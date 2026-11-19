"""Tests du parcours complet : python manage.py test"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Produit

from .models import Commande, ZoneLivraison


class ParcoursAchatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('charger_demo', stdout=StringIO())
        cls.baume = Produit.objects.get(slug='baume-a-levres')
        cls.javel = Produit.objects.get(slug='eau-de-javel')
        cls.zone_ville = ZoneLivraison.objects.get(paiement_livraison=True, ordre=1)
        cls.zone_loin = ZoneLivraison.objects.get(paiement_livraison=False)

    def _ajouter(self, produit, quantite=1):
        return self.client.post(reverse('panier:ajouter', args=[produit.pk]), {'quantite': quantite})

    def _commander(self, zone, mode):
        return self.client.post(reverse('commandes:passer'), {
            'nom': 'Awa Test', 'telephone': '690000000', 'email': '',
            'zone': zone.pk, 'adresse': 'Akwa, près du marché', 'mode_reglement': mode, 'note': '',
        })

    # ---------- Pages publiques ----------
    def test_pages_publiques(self):
        for nom in ['pages:accueil', 'pages:a_propos', 'pages:contact', 'pages:cgv', 'pages:confidentialite',
                    'catalogue:liste', 'panier:detail', 'comptes:connexion', 'comptes:inscription']:
            with self.subTest(page=nom):
                self.assertEqual(self.client.get(reverse(nom)).status_code, 200)
        self.assertContains(self.client.get(self.baume.get_absolute_url()), 'Baume à lèvres')

    def test_deux_modes_de_reglement_sans_option_vide(self):
        self._ajouter(self.baume)
        html = self.client.get(reverse('commandes:passer')).content.decode()
        self.assertEqual(html.count('name="mode_reglement"'), 2)
        self.assertNotIn('Choisir une option', html)

    def test_commande_uniquement_sur_le_site(self):
        """Aucun bouton ne propose de commander par WhatsApp : la commande se fait par le panier."""
        self._ajouter(self.baume)
        for url in [reverse('pages:accueil'), self.baume.get_absolute_url(), reverse('panier:detail')]:
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertNotIn('Commander via WhatsApp', html)
                self.assertNotIn('je souhaite commander', html)
                self.assertNotIn('Envoyer mon panier', html)
        self.assertContains(self.client.get(reverse('panier:detail')), 'Passer commande')

    def test_recherche_et_filtres(self):
        r = self.client.get(reverse('catalogue:liste'), {'q': 'javel'})
        self.assertContains(r, 'Eau de Javel')
        self.assertNotContains(r, 'Baume de massage')
        r = self.client.get(reverse('catalogue:liste'), {'categorie': 'soin-bien-etre'})
        self.assertEqual(len(r.context['produits']), 2)
        r = self.client.get(reverse('catalogue:liste'), {'prix_max': '900'})
        self.assertEqual({p.slug for p in r.context['produits']}, {'savon-en-morceaux', 'eau-de-javel'})

    # ---------- Panier ----------
    def test_panier_ajout_modification_quantite_limitee_au_stock(self):
        self._ajouter(self.javel, 10)  # stock = 4
        r = self.client.get(reverse('panier:detail'))
        self.assertEqual(r.context['lignes'][0]['quantite'], 4)
        self.client.post(reverse('panier:modifier', args=[self.javel.pk]), {'quantite': 2})
        self.assertEqual(self.client.get(reverse('panier:detail')).context['sous_total'], 1600)
        self.client.post(reverse('panier:retirer', args=[self.javel.pk]))
        self.assertEqual(self.client.get(reverse('panier:detail')).context['lignes'], [])

    def test_redirection_externe_refusee(self):
        r = self.client.post(reverse('panier:ajouter', args=[self.baume.pk]), {'suivant': 'https://site-pirate.com/'})
        self.assertRedirects(r, reverse('panier:detail'))

    # ---------- Commande : paiement à la livraison ----------
    def test_commande_paiement_livraison(self):
        self._ajouter(self.baume, 2)
        r = self._commander(self.zone_ville, 'livraison')
        commande = Commande.objects.get()
        self.assertRedirects(r, reverse('commandes:confirmation', args=[commande.numero]))
        self.assertEqual(commande.sous_total, 3000)
        self.assertEqual(commande.frais_livraison, 1000)
        self.assertEqual(commande.total, 4000)
        self.assertEqual(commande.statut_paiement, Commande.StatutPaiement.ATTENTE)
        self.assertTrue(commande.numero.startswith('UN'))
        self.baume.refresh_from_db()
        self.assertEqual(self.baume.stock, 38)
        self.assertEqual(len(self.client.session['panier']), 0)
        page = self.client.get(reverse('commandes:confirmation', args=[commande.numero]))
        self.assertContains(page, 'Paiement à la livraison')

    def test_paiement_livraison_refuse_pour_zone_eloignee(self):
        self._ajouter(self.baume)
        r = self._commander(self.zone_loin, 'livraison')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'n’est pas disponible')
        self.assertFalse(Commande.objects.exists())

    # ---------- Commande : Mobile Money via WhatsApp ----------
    def test_commande_mobile_money(self):
        self._ajouter(self.baume)
        self._commander(self.zone_loin, 'mobile_money')
        commande = Commande.objects.get()
        page = self.client.get(reverse('commandes:confirmation', args=[commande.numero]))
        self.assertContains(page, 'Payer par Mobile Money')
        self.assertContains(page, 'https://wa.me/')

    def test_promo_appliquee(self):
        massage = Produit.objects.get(slug='baume-de-massage')
        self._ajouter(massage)
        self._commander(self.zone_ville, 'livraison')
        self.assertEqual(Commande.objects.get().sous_total, 3000)

    def test_stock_epuise_entre_temps(self):
        self._ajouter(self.javel, 4)
        Produit.objects.filter(pk=self.javel.pk).update(stock=1)
        r = self._commander(self.zone_ville, 'livraison')
        self.assertRedirects(r, reverse('panier:detail'))
        self.assertFalse(Commande.objects.exists())

    def test_annulation_remet_en_stock(self):
        self._ajouter(self.baume, 3)
        self._commander(self.zone_ville, 'livraison')
        commande = Commande.objects.get()
        commande.annuler()
        commande.annuler()  # deuxième appel sans effet
        self.baume.refresh_from_db()
        self.assertEqual(self.baume.stock, 40)

    # ---------- Confidentialité des commandes ----------
    def test_autre_visiteur_ne_voit_pas_la_commande(self):
        self._ajouter(self.baume)
        self._commander(self.zone_ville, 'livraison')
        numero = Commande.objects.get().numero
        self.client.logout()
        self.client.cookies.clear()
        self.assertEqual(self.client.get(reverse('commandes:detail', args=[numero])).status_code, 404)

    # ---------- Comptes ----------
    def test_inscription_et_espace_client(self):
        r = self.client.post(reverse('comptes:inscription'), {
            'username': 'awa', 'first_name': 'Awa', 'last_name': 'Test', 'email': 'awa@exemple.com',
            'password1': 'Karite-2026-baume', 'password2': 'Karite-2026-baume',
        })
        self.assertRedirects(r, reverse('comptes:espace'))
        self.assertContains(self.client.get(reverse('comptes:espace')), 'Bonjour Awa')

    def test_admin_django_supprime(self):
        self.assertEqual(self.client.get('/admin/').status_code, 404)
