"""Tests de l'envoi de la preuve de paiement Mobile Money sur le site : python manage.py test commandes"""
import shutil
import tempfile
from io import BytesIO, StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalogue.models import Produit

from .models import Commande, ZoneLivraison

DOSSIER_TEST = Path(tempfile.mkdtemp(prefix='preuves-test-'))


def image_png(nom='capture.png', taille=(40, 40)):
    tampon = BytesIO()
    Image.new('RGB', taille, (47, 107, 63)).save(tampon, format='PNG')
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type='image/png')


@override_settings(PREUVES_ROOT=DOSSIER_TEST)
class PreuvePaiementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('charger_demo', stdout=StringIO())
        cls.baume = Produit.objects.get(slug='baume-a-levres')
        cls.zone = ZoneLivraison.objects.get(ordre=1)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(DOSSIER_TEST, ignore_errors=True)

    def _commander(self, mode='mobile_money'):
        self.client.post(reverse('panier:ajouter', args=[self.baume.pk]), {'quantite': 1})
        self.client.post(reverse('commandes:passer'), {
            'nom': 'Awa', 'telephone': '690000000', 'zone': self.zone.pk, 'adresse': 'Akwa', 'mode_reglement': mode,
        })
        return Commande.objects.latest('cree_le')

    def _url(self, commande):
        return reverse('commandes:envoyer_preuve', args=[commande.numero])

    def test_formulaire_affiche_sur_confirmation_et_suivi(self):
        c = self._commander()
        for url in [reverse('commandes:confirmation', args=[c.numero]), c.get_absolute_url()]:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertContains(r, 'Envoyer ma preuve de paiement')
                self.assertContains(r, 'enctype="multipart/form-data"')
                self.assertNotContains(r, 'Envoyer la preuve de paiement</a>')  # plus de bouton WhatsApp

    def test_envoi_reference_seule(self):
        c = self._commander()
        r = self.client.post(self._url(c), {'reference_transfert': '  MP2611.1234.A56789 '})
        self.assertRedirects(r, c.get_absolute_url())
        c.refresh_from_db()
        self.assertEqual(c.reference_transfert, 'MP2611.1234.A56789')
        self.assertIsNotNone(c.preuve_envoyee_le)
        self.assertFalse(c.capture_paiement)
        self.assertTrue(c.preuve_a_verifier)
        self.assertEqual(c.statut_paiement, 'attente')  # le paiement reste à vérifier par l'équipe

    def test_envoi_capture_rangee_dans_le_dossier_prive(self):
        c = self._commander()
        self.client.post(self._url(c), {'capture_paiement': image_png()})
        c.refresh_from_db()
        self.assertTrue(c.capture_paiement.name.startswith(c.numero))
        chemin = Path(c.capture_paiement.path)
        self.assertTrue(chemin.exists())
        self.assertEqual(chemin.parent, DOSSIER_TEST)  # hors de media/, donc sans adresse publique

    def test_nouvelle_capture_remplace_l_ancienne_et_garde_la_reference(self):
        c = self._commander()
        self.client.post(self._url(c), {'reference_transfert': 'REF-1', 'capture_paiement': image_png('a.png')})
        c.refresh_from_db()
        ancienne = Path(c.capture_paiement.path)
        self.client.post(self._url(c), {'capture_paiement': image_png('b.png')})
        c.refresh_from_db()
        self.assertFalse(ancienne.exists())
        self.assertEqual(c.reference_transfert, 'REF-1')

    def test_rien_envoye_refuse(self):
        c = self._commander()
        r = self.client.post(self._url(c), {'reference_transfert': '   '})
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, 'Indiquez la référence du transfert', status_code=400)
        c.refresh_from_db()
        self.assertIsNone(c.preuve_envoyee_le)

    def test_fichier_qui_n_est_pas_une_image_refuse(self):
        c = self._commander()
        faux = SimpleUploadedFile('capture.png', b'pas une image', content_type='image/png')
        r = self.client.post(self._url(c), {'capture_paiement': faux})
        self.assertEqual(r.status_code, 400)
        pdf = SimpleUploadedFile('releve.pdf', b'%PDF-1.4', content_type='application/pdf')
        r = self.client.post(self._url(c), {'capture_paiement': pdf})
        self.assertEqual(r.status_code, 400)
        c.refresh_from_db()
        self.assertFalse(c.capture_paiement)

    @override_settings(TAILLE_MAX_CAPTURE=100)
    def test_image_trop_lourde_refusee(self):
        c = self._commander()
        r = self.client.post(self._url(c), {'capture_paiement': image_png(taille=(300, 300))})
        self.assertContains(r, 'trop lourde', status_code=400)

    def test_refuse_pour_paiement_a_la_livraison_ou_deja_paye(self):
        c = self._commander(mode='livraison')
        self.assertNotContains(self.client.get(c.get_absolute_url()), 'Envoyer ma preuve de paiement')
        self.client.post(self._url(c), {'reference_transfert': 'X'})
        c.refresh_from_db()
        self.assertEqual(c.reference_transfert, '')
        c2 = self._commander()
        Commande.objects.filter(pk=c2.pk).update(statut_paiement='payee')
        self.client.post(self._url(c2), {'reference_transfert': 'X'})
        c2.refresh_from_db()
        self.assertEqual(c2.reference_transfert, '')

    def test_un_autre_visiteur_ne_peut_pas_envoyer(self):
        c = self._commander()
        self.client.logout()
        self.client.cookies.clear()
        r = self.client.post(self._url(c), {'reference_transfert': 'PIRATE'})
        self.assertEqual(r.status_code, 404)

    def test_capture_visible_seulement_par_l_equipe(self):
        c = self._commander()
        self.client.post(self._url(c), {'capture_paiement': image_png()})
        url = reverse('gestion:preuve', args=[c.pk])
        self.assertEqual(self.client.get(url).status_code, 302)  # le client lui-même : non
        equipe = User.objects.create_user('equipe', password='mot-de-passe-solide-1', is_staff=True)
        self.client.force_login(equipe)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/png')
        self.assertIn('no-store', r['Cache-Control'])
        r.close()
        fiche = self.client.get(reverse('gestion:commande', args=[c.pk]))
        self.assertContains(fiche, 'Preuve de paiement Mobile Money')
        liste = self.client.get(reverse('gestion:commandes'), {'preuve': '1'})
        self.assertContains(liste, c.numero)
        self.assertContains(liste, 'Preuve à vérifier')
