from .panier import Panier


def panier(request):
    """Nombre d'articles affiché sur l'icône du panier, sur toutes les pages."""
    return {'panier_nb': len(Panier(request))}
