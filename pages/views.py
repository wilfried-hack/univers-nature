from django.contrib.staticfiles import finders
from django.shortcuts import render

from catalogue.models import Categorie, Produit


def accueil(request):
    """Page d'accueil (section 4.1)."""
    visibles = Produit.objects.visibles()
    return render(request, 'pages/accueil.html', {
        'categories': Categorie.objects.all(),
        'populaires': visibles.filter(populaire=True)[:6],
        'nouveautes': visibles.filter(nouveaute=True)[:3],
        'promotions': [p for p in visibles.filter(prix_promo__isnull=False) if p.en_promo][:3],
        'photo_hero': bool(finders.find('img/hero.jpg')),
    })


def a_propos(request):
    return render(request, 'pages/a_propos.html')


def contact(request):
    return render(request, 'pages/contact.html')


def cgv(request):
    return render(request, 'pages/cgv.html')


def confidentialite(request):
    return render(request, 'pages/confidentialite.html')
