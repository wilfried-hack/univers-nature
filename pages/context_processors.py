from django.conf import settings


def boutique(request):
    """Rend les coordonnées de la boutique (settings.BOUTIQUE) disponibles dans tous les gabarits : {{ boutique.TELEPHONE }}"""
    return {'boutique': settings.BOUTIQUE}
