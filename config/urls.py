from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path('', include('pages.urls')),
    path('boutique/', include('catalogue.urls')),
    path('panier/', include('panier.urls')),
    path('commande/', include('commandes.urls')),
    path('compte/', include('comptes.urls')),
    path('gestion/', include('gestion.urls')),  # espace administrateur de la boutique
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
