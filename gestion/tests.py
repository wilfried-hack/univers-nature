"""Tests de l'espace de gestion : python manage.py test gestion"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Categorie, Produit
from commandes.models import Commande, LigneCommande, ZoneLivraison


class GestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('charger_demo', stdout=StringIO())
        cls.admin = User.objects.create_user('equipe', password='mot-de-passe-solide-1', is_staff=True, first_name='Awa')
        cls.client_user = User.objects.create_user('cliente', password='mot-de-passe-solide-1')
        cls.baume = Produit.objects.get(slug='baume-a-levres')
        cls.zone = ZoneLivraison.objects.get(ordre=1)

    def setUp(self):
        self.client.force_login(self.admin)

    def _commande(self, mode=Commande.ModeReglement.LIVRAISON, quantite=2):
        c = Commande.objects.create(nom='Test', telephone='690000000', zone=self.zone, adresse='Akwa',
                                    mode_reglement=mode, frais_livraison=self.zone.frais, client=self.client_user)
        LigneCommande.objects.create(commande=c, produit=self.baume, nom_produit=self.baume.nom,
                                     prix_unitaire=self.baume.prix, quantite=quantite)
        Produit.objects.filter(pk=self.baume.pk).update(stock=self.baume.stock - quantite)
        c.recalculer()
        c.save()
        return c

    def test_acces_refuse_aux_clients_et_visiteurs(self):
        self.client.logout()
        r = self.client.get(reverse('gestion:tableau_de_bord'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('comptes:connexion'), r.url)
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse('gestion:commandes')).status_code, 302)

    def test_toutes_les_pages_s_affichent(self):
        c = self._commande()
        pages = ['tableau_de_bord', 'commandes', 'produits', 'produit_ajouter', 'categories', 'zones',
                 'clients', 'statistiques']
        for nom in pages:
            with self.subTest(page=nom):
                self.assertEqual(self.client.get(reverse(f'gestion:{nom}')).status_code, 200)
        self.assertContains(self.client.get(reverse('gestion:commande', args=[c.pk])), c.numero)
        self.assertEqual(self.client.get(reverse('gestion:produit_modifier', args=[self.baume.pk])).status_code, 200)

    def test_staff_redirige_vers_gestion_apres_connexion(self):
        self.assertRedirects(self.client.get(reverse('comptes:espace')), reverse('gestion:tableau_de_bord'))

    def test_suivi_rapide_livree_paiement_livraison_devient_payee(self):
        c = self._commande()
        self.client.post(reverse('gestion:commande_suivi', args=[c.pk]), {'statut': 'livree', 'statut_paiement': 'attente'})
        c.refresh_from_db()
        self.assertEqual(c.statut, 'livree')
        self.assertEqual(c.statut_paiement, 'payee')

    def test_annulation_depuis_la_fiche_remet_en_stock_et_bloque(self):
        c = self._commande(quantite=3)
        self.client.post(reverse('gestion:commande', args=[c.pk]), {
            'statut': 'annulee', 'statut_paiement': 'attente', 'reference_transfert': '', 'frais_livraison': 1000, 'note_interne': 'client injoignable',
        })
        c.refresh_from_db()
        self.baume.refresh_from_db()
        self.assertEqual(c.statut, 'annulee')
        self.assertEqual(c.note_interne, 'client injoignable')
        self.assertEqual(self.baume.stock, 40)
        # Une commande annulée ne peut plus être relancée
        self.client.post(reverse('gestion:commande_suivi', args=[c.pk]), {'statut': 'expediee', 'statut_paiement': 'payee'})
        c.refresh_from_db()
        self.assertEqual(c.statut, 'annulee')

    def test_fiche_commande_reference_et_frais_recalcules(self):
        c = self._commande(mode=Commande.ModeReglement.MOBILE_MONEY)
        self.client.post(reverse('gestion:commande', args=[c.pk]), {
            'statut': 'confirmee', 'statut_paiement': 'payee', 'reference_transfert': 'MP2611.1234', 'frais_livraison': 2500, 'note_interne': '',
        })
        c.refresh_from_db()
        self.assertEqual((c.statut, c.statut_paiement, c.reference_transfert), ('confirmee', 'payee', 'MP2611.1234'))
        self.assertEqual(c.total, c.sous_total + 2500)

    def test_ajouter_modifier_produit(self):
        cat = Categorie.objects.first()
        r = self.client.post(reverse('gestion:produit_ajouter'), {
            'nom': 'Savon noir', 'categorie': cat.pk, 'description_courte': 'Un savon', 'prix': 900,
            'contenance': '250 g', 'stock': 10, 'actif': 'on',
        })
        self.assertRedirects(r, reverse('gestion:produits'))
        p = Produit.objects.get(nom='Savon noir')
        self.assertEqual(p.slug, 'savon-noir')
        # Prix promo supérieur au prix : refusé
        r = self.client.post(reverse('gestion:produit_modifier', args=[p.pk]), {
            'nom': 'Savon noir', 'categorie': cat.pk, 'description_courte': 'Un savon', 'prix': 900, 'prix_promo': 1000,
            'contenance': '250 g', 'stock': 10, 'actif': 'on',
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'inférieur au prix normal')

    def test_supprimer_produit_deja_commande_le_masque(self):
        self._commande()
        self.client.post(reverse('gestion:produit_supprimer', args=[self.baume.pk]))
        self.baume.refresh_from_db()
        self.assertFalse(self.baume.actif)
        neuf = Produit.objects.get(slug='savon-en-morceaux')
        self.client.post(reverse('gestion:produit_supprimer', args=[neuf.pk]))
        self.assertFalse(Produit.objects.filter(pk=neuf.pk).exists())

    def test_stock_rapide(self):
        self.client.post(reverse('gestion:produit_stock', args=[self.baume.pk]), {'stock': '12'})
        self.baume.refresh_from_db()
        self.assertEqual(self.baume.stock, 12)

    def test_categorie_avec_produits_non_supprimable(self):
        cat = Categorie.objects.first()
        self.client.post(reverse('gestion:categorie_supprimer', args=[cat.pk]))
        self.assertTrue(Categorie.objects.filter(pk=cat.pk).exists())
        r = self.client.post(reverse('gestion:categories'), {'nom': 'Coffrets cadeaux', 'description': '', 'ordre': 3})
        self.assertRedirects(r, reverse('gestion:categories'))
        self.assertTrue(Categorie.objects.filter(slug='coffrets-cadeaux').exists())

    def test_zone_utilisee_desactivee_au_lieu_de_supprimee(self):
        self._commande()
        self.client.post(reverse('gestion:zone_supprimer', args=[self.zone.pk]))
        self.zone.refresh_from_db()
        self.assertFalse(self.zone.active)

    def test_suspendre_client(self):
        self.client.post(reverse('gestion:client_basculer', args=[self.client_user.pk]))
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_active)
        # Un membre de l'équipe ne peut pas être suspendu depuis cet écran
        r = self.client.post(reverse('gestion:client_basculer', args=[self.admin.pk]))
        self.assertEqual(r.status_code, 404)
