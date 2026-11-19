"""Espace d'administration de la boutique (inspiré de l'espace « Administration » de MEDIATECH).
Réservé aux comptes « équipe » (is_staff). """
import mimetypes
from datetime import timedelta
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalogue.models import Categorie, Produit
from commandes.models import Commande, LigneCommande, ZoneLivraison

from .forms import CategorieForm, ProduitForm, SuiviCommandeForm, ZoneForm

SEUIL_STOCK_BAS = 5


def equipe_requise(vue):
    """Accès réservé à l'équipe : les autres sont renvoyés vers la page de connexion du site."""
    @wraps(vue)
    @user_passes_test(lambda u: u.is_active and u.is_staff, login_url='comptes:connexion')
    def enveloppe(request, *args, **kwargs):
        return vue(request, *args, **kwargs)
    return enveloppe


def lien_whatsapp_client(commande):
    numero = ''.join(c for c in commande.telephone if c.isdigit())
    if len(numero) == 9:  # numéro local camerounais : ajoute l'indicatif
        numero = '237' + numero
    message = f'Bonjour {commande.nom}, ici {settings.BOUTIQUE["NOM"]} au sujet de votre commande {commande.numero}.'
    return f'https://wa.me/{numero}?text={quote(message)}'


def appliquer_suivi(request, commande, statut, paiement):
    """Met à jour statut et paiement, avec les règles de la boutique. Renvoie True si la commande a changé."""
    if commande.statut == Commande.Statut.ANNULEE:
        messages.error(request, f'La commande {commande.numero} est annulée : elle ne peut plus être modifiée.')
        return False
    if statut == Commande.Statut.ANNULEE:
        commande.annuler()
        messages.success(request, f'Commande {commande.numero} annulée, les produits sont remis en stock.')
        return True
    commande.statut = statut
    commande.statut_paiement = paiement
    # Paiement à la livraison : une commande livrée est une commande payée.
    if statut == Commande.Statut.LIVREE and commande.mode_reglement == Commande.ModeReglement.LIVRAISON:
        commande.statut_paiement = Commande.StatutPaiement.PAYEE
    commande.save(update_fields=['statut', 'statut_paiement', 'modifie_le'])
    messages.success(request, f'Commande {commande.numero} : {commande.get_statut_display().lower()}, '
                              f'{commande.get_statut_paiement_display().lower()}.')
    return True


# ---------- Tableau de bord ----------
@equipe_requise
def tableau_de_bord(request):
    actives = Commande.objects.exclude(statut=Commande.Statut.ANNULEE)
    a_traiter = actives.filter(statut__in=[Commande.Statut.RECUE, Commande.Statut.CONFIRMEE]).count()
    a_verifier = preuves_a_verifier().count()
    stock_bas = Produit.objects.filter(actif=True, stock__lte=SEUIL_STOCK_BAS).count()
    return render(request, 'gestion/tableau_de_bord.html', {
        'kpis': [
            {'libelle': 'Commandes à traiter', 'valeur': a_traiter, 'icone': 'bi-inbox', 'alerte': a_traiter > 0},
            {'libelle': 'Preuves de paiement à vérifier', 'valeur': a_verifier, 'icone': 'bi-phone', 'alerte': a_verifier > 0,
             'lien': '?preuve=1'},
            {'libelle': 'Chiffre d’affaires encaissé', 'icone': 'bi-cash-stack', 'fcfa': True,
             'valeur': actives.filter(statut_paiement=Commande.StatutPaiement.PAYEE).aggregate(s=Sum('total'))['s'] or 0},
            {'libelle': 'Produits en stock bas', 'valeur': stock_bas, 'icone': 'bi-box-seam', 'alerte': stock_bas > 0},
        ],
        'commandes': Commande.objects.select_related('zone')[:8],
        'stock_bas': Produit.objects.filter(actif=True, stock__lte=SEUIL_STOCK_BAS).order_by('stock')[:6],
        'statuts': Commande.Statut.choices,
        'paiements': Commande.StatutPaiement.choices,
    })


# ---------- Commandes ----------
def preuves_a_verifier():
    """Commandes Mobile Money dont le client a envoyé une preuve, paiement pas encore confirmé."""
    return Commande.objects.filter(mode_reglement=Commande.ModeReglement.MOBILE_MONEY,
                                   statut_paiement=Commande.StatutPaiement.ATTENTE,
                                   preuve_envoyee_le__isnull=False).exclude(statut=Commande.Statut.ANNULEE)


@equipe_requise
def commandes(request):
    preuve = request.GET.get('preuve') == '1'
    qs = preuves_a_verifier() if preuve else Commande.objects.all()
    qs = qs.select_related('zone')
    q = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    paiement = request.GET.get('paiement', '')
    mode = request.GET.get('mode', '')
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(nom__icontains=q) | Q(telephone__icontains=q) | Q(reference_transfert__icontains=q))
    if statut:
        qs = qs.filter(statut=statut)
    if paiement:
        qs = qs.filter(statut_paiement=paiement)
    if mode:
        qs = qs.filter(mode_reglement=mode)
    return render(request, 'gestion/commandes.html', {
        'commandes': qs[:200], 'q': q, 'statut': statut, 'paiement': paiement, 'mode': mode, 'preuve': preuve,
        'statuts': Commande.Statut.choices, 'paiements': Commande.StatutPaiement.choices,
        'modes': Commande.ModeReglement.choices,
    })


@equipe_requise
@require_POST
def commande_suivi_rapide(request, pk):
    """Formulaire « Mettre à jour » dans les tableaux de commandes."""
    commande = get_object_or_404(Commande, pk=pk)
    statut = request.POST.get('statut')
    paiement = request.POST.get('statut_paiement')
    if statut in Commande.Statut.values and paiement in Commande.StatutPaiement.values:
        appliquer_suivi(request, commande, statut, paiement)
    else:
        messages.error(request, 'Statut invalide.')
    suivant = request.POST.get('suivant', '')
    return redirect(suivant if suivant.startswith('/gestion/') else 'gestion:commandes')


@equipe_requise
def commande_detail(request, pk):
    commande = get_object_or_404(Commande.objects.select_related('zone', 'client').prefetch_related('lignes'), pk=pk)
    # Le formulaire modifie l'objet pendant la validation : on garde l'état d'origine.
    statut_initial, paiement_initial = commande.statut, commande.statut_paiement
    form = SuiviCommandeForm(request.POST or None, instance=commande)
    if request.method == 'POST' and form.is_valid():
        if statut_initial == Commande.Statut.ANNULEE:
            messages.error(request, 'Cette commande est annulée : elle ne peut plus être modifiée.')
            return redirect('gestion:commande', pk=pk)
        nouveau_statut = form.cleaned_data['statut']
        nouveau_paiement = form.cleaned_data['statut_paiement']
        commande = form.save(commit=False)
        # Référence, frais et note sont enregistrés tels quels ; statut et paiement passent
        # par les règles communes (remise en stock si annulation, livrée = payée…).
        commande.statut, commande.statut_paiement = statut_initial, paiement_initial
        commande.recalculer()
        commande.save()
        appliquer_suivi(request, commande, nouveau_statut, nouveau_paiement)
        return redirect('gestion:commande', pk=pk)
    return render(request, 'gestion/commande.html', {
        'commande': commande, 'form': form, 'lien_wa': lien_whatsapp_client(commande),
    })


@equipe_requise
def preuve(request, pk):
    """Affiche la capture d'écran du paiement. Le fichier est dans un dossier privé :
    il n'a pas d'adresse publique et ne s'ouvre que par cette page, réservée à l'équipe."""
    commande = get_object_or_404(Commande, pk=pk)
    if not commande.capture_paiement:
        raise Http404
    try:
        fichier = commande.capture_paiement.open('rb')
    except FileNotFoundError:
        raise Http404
    type_mime = mimetypes.guess_type(commande.capture_paiement.name)[0] or 'application/octet-stream'
    reponse = FileResponse(fichier, content_type=type_mime)
    reponse['Cache-Control'] = 'private, no-store'
    return reponse


# ---------- Produits ----------
@equipe_requise
def produits(request):
    qs = Produit.objects.select_related('categorie')
    q = request.GET.get('q', '').strip()
    categorie = request.GET.get('categorie', '')
    if q:
        qs = qs.filter(nom__icontains=q)
    if categorie:
        qs = qs.filter(categorie__slug=categorie)
    return render(request, 'gestion/produits.html', {
        'produits': qs, 'q': q, 'categorie': categorie, 'categories': Categorie.objects.all(), 'seuil': SEUIL_STOCK_BAS,
    })


@equipe_requise
def produit_form(request, pk=None):
    produit = get_object_or_404(Produit, pk=pk) if pk else None
    form = ProduitForm(request.POST or None, request.FILES or None, instance=produit)
    if request.method == 'POST' and form.is_valid():
        produit = form.save()
        messages.success(request, f'« {produit.nom} » a été {"modifié" if pk else "ajouté"}.')
        return redirect('gestion:produits')
    return render(request, 'gestion/produit_form.html', {'form': form, 'produit': produit})


@equipe_requise
@require_POST
def produit_stock(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    try:
        produit.stock = max(0, int(request.POST.get('stock', produit.stock)))
    except ValueError:
        messages.error(request, 'Stock invalide.')
        return redirect('gestion:produits')
    produit.save(update_fields=['stock', 'modifie_le'])
    messages.success(request, f'Stock de « {produit.nom} » : {produit.stock}.')
    return redirect('gestion:produits')


@equipe_requise
@require_POST
def produit_supprimer(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if produit.lignes_commande.exists():
        # Comme sur MEDIATECH : un produit déjà commandé est masqué plutôt que supprimé.
        produit.actif = False
        produit.save(update_fields=['actif', 'modifie_le'])
        messages.info(request, f'« {produit.nom} » a déjà été commandé : il a été retiré de la boutique au lieu d’être supprimé.')
    else:
        produit.delete()
        messages.success(request, f'« {produit.nom} » a été supprimé.')
    return redirect('gestion:produits')


# ---------- Catégories ----------
@equipe_requise
def categories(request, pk=None):
    categorie = get_object_or_404(Categorie, pk=pk) if pk else None
    form = CategorieForm(request.POST or None, instance=categorie)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Catégorie enregistrée.')
        return redirect('gestion:categories')
    return render(request, 'gestion/categories.html', {
        'categories': Categorie.objects.annotate(nb=Count('produits')), 'form': form, 'edition': categorie,
    })


@equipe_requise
@require_POST
def categorie_supprimer(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    try:
        categorie.delete()
        messages.success(request, f'Catégorie « {categorie.nom} » supprimée.')
    except ProtectedError:
        messages.error(request, f'« {categorie.nom} » contient encore des produits : déplacez-les avant de la supprimer.')
    return redirect('gestion:categories')


# ---------- Zones de livraison ----------
@equipe_requise
def zones(request, pk=None):
    zone = get_object_or_404(ZoneLivraison, pk=pk) if pk else None
    form = ZoneForm(request.POST or None, instance=zone)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Zone de livraison enregistrée.')
        return redirect('gestion:zones')
    return render(request, 'gestion/zones.html', {
        'zones': ZoneLivraison.objects.annotate(nb=Count('commandes')), 'form': form, 'edition': zone,
    })


@equipe_requise
@require_POST
def zone_supprimer(request, pk):
    zone = get_object_or_404(ZoneLivraison, pk=pk)
    try:
        zone.delete()
        messages.success(request, f'Zone « {zone.nom} » supprimée.')
    except ProtectedError:
        zone.active = False
        zone.save(update_fields=['active'])
        messages.info(request, f'« {zone.nom} » est utilisée par des commandes : elle a été désactivée au lieu d’être supprimée.')
    return redirect('gestion:zones')


# ---------- Clients ----------
@equipe_requise
def clients(request):
    q = request.GET.get('q', '').strip()
    qs = User.objects.filter(is_staff=False).annotate(
        nb_commandes=Count('commandes', distinct=True),
        total_achats=Sum('commandes__total', filter=Q(commandes__statut_paiement=Commande.StatutPaiement.PAYEE)),
    ).order_by('-date_joined')
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    return render(request, 'gestion/clients.html', {'clients': qs, 'q': q})


@equipe_requise
@require_POST
def client_basculer(request, pk):
    client = get_object_or_404(User, pk=pk, is_staff=False)
    client.is_active = not client.is_active
    client.save(update_fields=['is_active'])
    messages.success(request, f'Compte de {client.get_full_name() or client.username} {"réactivé" if client.is_active else "suspendu"}.')
    return redirect('gestion:clients')


# ---------- Statistiques ----------
@equipe_requise
def statistiques(request):
    actives = Commande.objects.exclude(statut=Commande.Statut.ANNULEE)
    payees = actives.filter(statut_paiement=Commande.StatutPaiement.PAYEE)
    debut = (timezone.now() - timedelta(days=180)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    par_mois = list(payees.filter(cree_le__gte=debut).annotate(mois=TruncMonth('cree_le'))
                    .values('mois').annotate(total=Sum('total'), nb=Count('id')).order_by('mois'))
    maxi = max([m['total'] for m in par_mois], default=0) or 1
    for m in par_mois:
        m['pct'] = round(m['total'] * 100 / maxi)

    top = list(LigneCommande.objects.filter(commande__in=actives).values('nom_produit')
               .annotate(quantite=Sum('quantite')).order_by('-quantite')[:5])
    maxi_top = max([t['quantite'] for t in top], default=0) or 1
    for t in top:
        t['pct'] = round(t['quantite'] * 100 / maxi_top)

    nb = actives.count() or 1
    par_mode = [{'libelle': libelle, 'n': actives.filter(mode_reglement=cle).count()} for cle, libelle in Commande.ModeReglement.choices]
    for m in par_mode:
        m['pct'] = round(m['n'] * 100 / nb)

    return render(request, 'gestion/statistiques.html', {
        'ca_encaisse': payees.aggregate(s=Sum('total'))['s'] or 0,
        'ca_attente': actives.filter(statut_paiement=Commande.StatutPaiement.ATTENTE).aggregate(s=Sum('total'))['s'] or 0,
        'nb_commandes': actives.count(),
        'nb_annulees': Commande.objects.filter(statut=Commande.Statut.ANNULEE).count(),
        'par_statut': [(s.label, actives.filter(statut=s.value).count()) for s in Commande.Statut if s != Commande.Statut.ANNULEE],
        'par_mois': par_mois, 'top_produits': top, 'par_mode': par_mode,
    })
