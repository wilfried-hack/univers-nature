from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Categorie, Produit

TRIS = {
    'nom': ('Nom (A → Z)', 'nom'),
    'prix': ('Prix croissant', 'prix'),
    '-prix': ('Prix décroissant', '-prix'),
    'nouveautes': ('Nouveautés', '-cree_le'),
}


def liste(request):
    """Catalogue : recherche par mot-clé, filtres (catégorie, prix, disponibilité) et tri (section 4.2)."""
    produits = Produit.objects.visibles()
    categories = Categorie.objects.all()

    q = request.GET.get('q', '').strip()
    categorie_slug = request.GET.get('categorie', '')
    dispo = request.GET.get('dispo') == '1'
    prix_max = request.GET.get('prix_max', '')
    tri = request.GET.get('tri', 'nom')

    if q:
        produits = produits.filter(
            Q(nom__icontains=q) | Q(description_courte__icontains=q)
            | Q(description__icontains=q) | Q(composition__icontains=q)
        )
    categorie = None
    if categorie_slug:
        categorie = categories.filter(slug=categorie_slug).first()
        if categorie:
            produits = produits.filter(categorie=categorie)
    if dispo:
        produits = produits.filter(stock__gt=0)
    if prix_max.isdigit():
        produits = produits.filter(prix__lte=int(prix_max))
    produits = produits.order_by(TRIS.get(tri, TRIS['nom'])[1])

    return render(request, 'catalogue/liste.html', {
        'produits': produits,
        'categories': categories,
        'categorie': categorie,
        'q': q,
        'dispo': dispo,
        'prix_max': prix_max,
        'tri': tri,
        'tris': {cle: libelle for cle, (libelle, _) in TRIS.items()},
    })


def detail(request, slug):
    produit = get_object_or_404(Produit.objects.visibles(), slug=slug)
    similaires = Produit.objects.visibles().filter(categorie=produit.categorie).exclude(pk=produit.pk)[:3]
    return render(request, 'catalogue/detail.html', {'produit': produit, 'similaires': similaires})
