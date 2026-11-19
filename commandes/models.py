import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse

FORMATS_CAPTURE = ['jpg', 'jpeg', 'png', 'webp']


class StockagePreuves(FileSystemStorage):
    """Captures de paiement rangées HORS du dossier public media/ : elles n'ont aucune adresse publique,
    seule l'équipe peut les ouvrir (vue gestion:preuve). Le dossier est lu dans settings.PREUVES_ROOT
    à chaque utilisation."""

    @property
    def base_location(self):
        return settings.PREUVES_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None  # pas d'adresse publique


def stockage_preuves():
    return StockagePreuves()


def chemin_preuve(commande, nom_fichier):
    extension = Path(nom_fichier).suffix.lower().lstrip('.') or 'jpg'
    return f'{commande.numero}-{uuid.uuid4().hex[:12]}.{extension}'


class ZoneLivraison(models.Model):
    """Zones desservies et frais de livraison (section 4.6)."""

    nom = models.CharField(max_length=120, help_text='Ex. : Douala – Akwa, Bonabéri, Yaoundé…')
    frais = models.PositiveIntegerField('frais de livraison (FCFA)', default=0)
    delai = models.CharField('délai indicatif', max_length=60, blank=True, help_text='Ex. : 24 h, 2 à 3 jours.')
    paiement_livraison = models.BooleanField(
        'paiement à la livraison accepté', default=True,
        help_text='Décocher pour les zones éloignées : le client devra payer par Mobile Money avant expédition.',
    )
    active = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = 'zone de livraison'
        verbose_name_plural = 'zones de livraison'

    def __str__(self):
        return self.nom


class Commande(models.Model):
    class ModeReglement(models.TextChoices):
        LIVRAISON = 'livraison', 'Paiement à la livraison'
        MOBILE_MONEY = 'mobile_money', 'Mobile Money (avant expédition)'

    class StatutPaiement(models.TextChoices):
        ATTENTE = 'attente', 'En attente de paiement'
        PAYEE = 'payee', 'Payée'
        ANNULEE = 'annulee', 'Annulée'

    class Statut(models.TextChoices):
        RECUE = 'recue', 'Reçue'
        CONFIRMEE = 'confirmee', 'Confirmée'
        PREPARATION = 'preparation', 'En préparation'
        EXPEDIEE = 'expediee', 'Expédiée'
        LIVREE = 'livree', 'Livrée'
        ANNULEE = 'annulee', 'Annulée'

    numero = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='commandes')

    # Coordonnées et livraison
    nom = models.CharField('nom complet', max_length=150)
    telephone = models.CharField('téléphone', max_length=30)
    email = models.EmailField(blank=True)
    zone = models.ForeignKey(ZoneLivraison, on_delete=models.PROTECT, related_name='commandes')
    adresse = models.TextField('adresse / repères de livraison')
    note = models.TextField('remarque du client', blank=True)

    # Règlement
    mode_reglement = models.CharField('mode de règlement', max_length=20, choices=ModeReglement.choices)
    statut_paiement = models.CharField('paiement', max_length=10, choices=StatutPaiement.choices, default=StatutPaiement.ATTENTE)
    reference_transfert = models.CharField(
        'référence du transfert Mobile Money', max_length=80, blank=True,
        help_text='Référence envoyée par le client sur le site, à vérifier sur le compte avant expédition.',
    )
    capture_paiement = models.ImageField(
        'capture d’écran du paiement', upload_to=chemin_preuve, storage=stockage_preuves, blank=True,
        validators=[FileExtensionValidator(FORMATS_CAPTURE)],
    )
    preuve_envoyee_le = models.DateTimeField('preuve de paiement envoyée le', null=True, blank=True)

    statut = models.CharField('statut de la commande', max_length=12, choices=Statut.choices, default=Statut.RECUE)

    # Montants figés au moment de la commande
    sous_total = models.PositiveIntegerField(default=0)
    frais_livraison = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    note_interne = models.TextField('note interne (non visible par le client)', blank=True)
    cree_le = models.DateTimeField('passée le', auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-cree_le']

    def __str__(self):
        return f'Commande {self.numero}'

    def save(self, *args, **kwargs):
        nouvelle = self.pk is None
        super().save(*args, **kwargs)
        if nouvelle and not self.numero:
            self.numero = f'UN{self.cree_le:%y%m}-{self.pk:04d}'
            super().save(update_fields=['numero'])

    def get_absolute_url(self):
        return reverse('commandes:detail', args=[self.numero])

    @property
    def attend_preuve(self):
        """Commande Mobile Money encore à payer : le client peut envoyer sa preuve de paiement."""
        return (self.mode_reglement == self.ModeReglement.MOBILE_MONEY
                and self.statut_paiement == self.StatutPaiement.ATTENTE
                and self.statut != self.Statut.ANNULEE)

    @property
    def preuve_a_verifier(self):
        return self.attend_preuve and self.preuve_envoyee_le is not None

    def recalculer(self):
        self.sous_total = sum(l.total for l in self.lignes.all())
        self.total = self.sous_total + self.frais_livraison

    @transaction.atomic
    def annuler(self):
        """Annule la commande et remet les produits en stock (une seule fois)."""
        if self.statut == self.Statut.ANNULEE:
            return
        for ligne in self.lignes.select_related('produit'):
            if ligne.produit_id:
                type(ligne.produit).objects.filter(pk=ligne.produit_id).update(stock=F('stock') + ligne.quantite)
        self.statut = self.Statut.ANNULEE
        self.statut_paiement = self.StatutPaiement.ANNULEE
        self.save(update_fields=['statut', 'statut_paiement', 'modifie_le'])


class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey('catalogue.Produit', null=True, on_delete=models.SET_NULL, related_name='lignes_commande')
    nom_produit = models.CharField(max_length=150)  # copie, au cas où le produit serait modifié ou supprimé
    prix_unitaire = models.PositiveIntegerField()
    quantite = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'ligne de commande'

    def __str__(self):
        return f'{self.quantite} × {self.nom_produit}'

    @property
    def total(self):
        return self.prix_unitaire * self.quantite
