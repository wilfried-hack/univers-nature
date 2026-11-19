from django.db import models
from django.urls import reverse


class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    ordre = models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage (le plus petit en premier).")

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = 'catégorie'

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('catalogue:liste') + f'?categorie={self.slug}'


class ProduitQuerySet(models.QuerySet):
    def visibles(self):
        return self.filter(actif=True).select_related('categorie')


class Produit(models.Model):
    """Fiche produit (section 2 du cahier des charges)."""

    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name='produits')
    nom = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='produits/', blank=True)
    description_courte = models.CharField(max_length=220, help_text='Une phrase affichée sur les cartes du catalogue.')
    description = models.TextField(blank=True)

    prix = models.PositiveIntegerField(help_text='Prix de vente en FCFA.')
    prix_promo = models.PositiveIntegerField(null=True, blank=True, help_text='Prix réduit en FCFA (laisser vide si pas de promotion).')
    contenance = models.CharField('volume, poids ou quantité', max_length=60, help_text='Ex. : 250 ml, 100 g, lot de 3.')

    composition = models.TextField('composition / ingrédients déclarés', blank=True)
    caracteristiques = models.TextField('caractéristiques', blank=True)
    utilisation = models.TextField("instructions d'utilisation", blank=True)
    precautions = models.TextField("précautions d'emploi", blank=True)
    fabricant = models.CharField('fabricant / responsable de la mise sur le marché', max_length=200, blank=True)

    stock = models.PositiveIntegerField(default=0)
    fait_main = models.BooleanField('fait main', default=False)
    naturel = models.BooleanField(default=False)
    populaire = models.BooleanField('mis en avant sur l’accueil', default=False)
    nouveaute = models.BooleanField('nouveauté', default=False)
    actif = models.BooleanField('visible sur le site', default=True)

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    objects = ProduitQuerySet.as_manager()

    class Meta:
        ordering = ['categorie__ordre', 'nom']

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('catalogue:detail', args=[self.slug])

    @property
    def en_promo(self):
        return self.prix_promo is not None and self.prix_promo < self.prix

    @property
    def prix_actuel(self):
        return self.prix_promo if self.en_promo else self.prix

    @property
    def en_stock(self):
        return self.stock > 0
