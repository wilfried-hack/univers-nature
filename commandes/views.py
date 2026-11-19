from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalogue.models import Produit
from panier.panier import Panier

from .forms import CommandeForm, PreuvePaiementForm
from .models import Commande, LigneCommande, ZoneLivraison

CLE_DERNIERES = 'commandes_session'  # numéros des commandes passées dans cette session (visiteurs sans compte)


class StockInsuffisant(Exception):
    pass


def passer_commande(request):
    """Étapes 3 à 8 du processus de commande (section 4.4)."""
    panier = Panier(request)
    lignes = panier.lignes()
    if not lignes:
        messages.info(request, 'Votre panier est vide.')
        return redirect('catalogue:liste')

    initial = {}
    if request.user.is_authenticated:
        initial = {'nom': request.user.get_full_name(), 'email': request.user.email}

    form = CommandeForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            commande = enregistrer_commande(form, lignes, client=request.user if request.user.is_authenticated else None)
        except StockInsuffisant as e:
            messages.error(request, str(e))
            return redirect('panier:detail')
        panier.vider()
        request.session[CLE_DERNIERES] = request.session.get(CLE_DERNIERES, []) + [commande.numero]
        return redirect('commandes:confirmation', numero=commande.numero)

    zones = ZoneLivraison.objects.filter(active=True)
    return render(request, 'commandes/commande.html', {
        'form': form,
        'lignes': lignes,
        'sous_total': panier.sous_total(),
        'frais_zones': {str(z.pk): z.frais for z in zones},
    })


@transaction.atomic
def enregistrer_commande(form, lignes, client=None):
    """Enregistre la commande et retire les produits du stock.
    lignes = [{'produit': Produit, 'quantite': int, 'prix': int}, …]"""
    commande = form.save(commit=False)
    commande.client = client
    commande.frais_livraison = commande.zone.frais
    commande.save()

    for ligne in lignes:
        produit = ligne['produit']
        # Décrémente le stock seulement s'il en reste assez (protège contre deux commandes simultanées).
        modifies = Produit.objects.filter(pk=produit.pk, stock__gte=ligne['quantite']).update(stock=F('stock') - ligne['quantite'])
        if not modifies:
            raise StockInsuffisant(f'Il ne reste plus assez de « {produit.nom} » en stock. Merci d’ajuster la quantité.')
        LigneCommande.objects.create(
            commande=commande, produit=produit, nom_produit=produit.nom,
            prix_unitaire=ligne['prix'], quantite=ligne['quantite'],
        )

    commande.recalculer()
    commande.save(update_fields=['sous_total', 'total'])
    return commande


def _commande_visible(request, numero):
    """Le client connecté voit ses commandes ; un visiteur voit celles passées dans sa session."""
    commande = get_object_or_404(Commande.objects.select_related('zone').prefetch_related('lignes'), numero=numero)
    if request.user.is_staff:
        return commande
    if request.user.is_authenticated and commande.client_id == request.user.pk:
        return commande
    if numero in request.session.get(CLE_DERNIERES, []):
        return commande
    raise Http404


def confirmation(request, numero):
    commande = _commande_visible(request, numero)
    return render(request, 'commandes/confirmation.html', {
        'commande': commande, 'form_preuve': PreuvePaiementForm(),
        'message_wa': f'Bonjour, j’ai une question sur ma commande {commande.numero}.',
    })


def detail(request, numero):
    commande = _commande_visible(request, numero)
    return render(request, 'commandes/detail.html', {'commande': commande, 'form_preuve': PreuvePaiementForm()})


@require_POST
def envoyer_preuve(request, numero):
    """Le client envoie la référence et/ou la capture d'écran de son transfert Mobile Money."""
    commande = _commande_visible(request, numero)
    if not commande.attend_preuve:
        messages.error(request, 'Cette commande n’attend pas de preuve de paiement.')
        return redirect(commande.get_absolute_url())

    form = PreuvePaiementForm(request.POST, request.FILES)
    if not form.is_valid():
        gabarit = 'commandes/confirmation.html' if request.POST.get('depuis') == 'confirmation' else 'commandes/detail.html'
        return render(request, gabarit, {'commande': commande, 'form_preuve': form}, status=400)

    champs = ['preuve_envoyee_le', 'modifie_le']
    if form.cleaned_data['reference_transfert']:
        commande.reference_transfert = form.cleaned_data['reference_transfert']
        champs.append('reference_transfert')
    if form.cleaned_data['capture_paiement']:
        if commande.capture_paiement:
            commande.capture_paiement.delete(save=False)  # remplace l'ancienne capture
        commande.capture_paiement = form.cleaned_data['capture_paiement']
        champs.append('capture_paiement')
    commande.preuve_envoyee_le = timezone.now()
    commande.save(update_fields=champs)
    messages.success(request, 'Merci ! Votre preuve de paiement a bien été envoyée. '
                              'Nous vérifions la réception du transfert, puis nous préparons votre commande.')
    return redirect(commande.get_absolute_url())


@login_required
def mes_commandes(request):
    commandes = request.user.commandes.select_related('zone')
    return render(request, 'commandes/mes_commandes.html', {'commandes': commandes})
