from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogue.models import Produit
from commandes.models import ZoneLivraison

from .panier import Panier


def _quantite(request, defaut=1):
    try:
        return int(request.POST.get('quantite', defaut))
    except ValueError:
        return defaut


def detail(request):
    panier = Panier(request)
    return render(request, 'panier/detail.html', {
        'lignes': panier.lignes(),
        'sous_total': panier.sous_total(),
        'zones': ZoneLivraison.objects.filter(active=True),
    })


@require_POST
def ajouter(request, produit_id):
    produit = get_object_or_404(Produit.objects.visibles(), pk=produit_id)
    if not produit.en_stock:
        messages.error(request, f'« {produit.nom} » est en rupture de stock.')
        return redirect(produit.get_absolute_url())
    Panier(request).ajouter(produit, max(1, _quantite(request)))
    messages.success(request, f'« {produit.nom} » a été ajouté au panier.')
    suivant = request.POST.get('suivant', '')
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        return redirect(suivant)
    return redirect('panier:detail')


@require_POST
def modifier(request, produit_id):
    produit = get_object_or_404(Produit, pk=produit_id)
    Panier(request).modifier(produit, _quantite(request))
    return redirect('panier:detail')


@require_POST
def retirer(request, produit_id):
    produit = get_object_or_404(Produit, pk=produit_id)
    Panier(request).retirer(produit)
    messages.info(request, f'« {produit.nom} » a été retiré du panier.')
    return redirect('panier:detail')
