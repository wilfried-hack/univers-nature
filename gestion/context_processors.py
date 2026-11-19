from commandes.models import Commande


def compteurs(request):
    """Pastilles de la barre latérale (commandes à traiter), seulement dans /gestion/."""
    if not request.path.startswith('/gestion/') or not getattr(request.user, 'is_staff', False):
        return {}
    return {
        'nb_a_traiter': Commande.objects.filter(statut__in=[Commande.Statut.RECUE, Commande.Statut.CONFIRMEE]).count(),
    }
