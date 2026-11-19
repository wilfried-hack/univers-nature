from django import forms
from django.utils.text import slugify

from catalogue.models import Categorie, Produit
from commandes.models import Commande, ZoneLivraison
from pages.bootstrap import BootstrapFormMixin


class ProduitForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Produit
        fields = ['nom', 'categorie', 'image', 'description_courte', 'description',
                  'prix', 'prix_promo', 'contenance', 'stock',
                  'composition', 'caracteristiques', 'utilisation', 'precautions', 'fabricant',
                  'fait_main', 'naturel', 'populaire', 'nouveaute', 'actif']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'composition': forms.Textarea(attrs={'rows': 3}),
            'caracteristiques': forms.Textarea(attrs={'rows': 3}),
            'utilisation': forms.Textarea(attrs={'rows': 3}),
            'precautions': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        donnees = super().clean()
        prix, promo = donnees.get('prix'), donnees.get('prix_promo')
        if prix is not None and promo is not None and promo >= prix:
            self.add_error('prix_promo', 'Le prix promotionnel doit être inférieur au prix normal.')
        return donnees

    def save(self, commit=True):
        produit = super().save(commit=False)
        if not produit.slug:
            base = slugify(produit.nom) or 'produit'
            slug, n = base, 2
            while Produit.objects.filter(slug=slug).exclude(pk=produit.pk).exists():
                slug, n = f'{base}-{n}', n + 1
            produit.slug = slug
        if commit:
            produit.save()
        return produit


class CategorieForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description', 'ordre']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}

    def save(self, commit=True):
        categorie = super().save(commit=False)
        if not categorie.slug:
            base = slugify(categorie.nom) or 'categorie'
            slug, n = base, 2
            while Categorie.objects.filter(slug=slug).exclude(pk=categorie.pk).exists():
                slug, n = f'{base}-{n}', n + 1
            categorie.slug = slug
        if commit:
            categorie.save()
        return categorie


class ZoneForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ZoneLivraison
        fields = ['nom', 'frais', 'delai', 'paiement_livraison', 'active', 'ordre']


class SuiviCommandeForm(BootstrapFormMixin, forms.ModelForm):
    """Ce que l'administrateur modifie sur une commande."""

    class Meta:
        model = Commande
        fields = ['statut', 'statut_paiement', 'reference_transfert', 'frais_livraison', 'note_interne']
        widgets = {'note_interne': forms.Textarea(attrs={'rows': 3})}
