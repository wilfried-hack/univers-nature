from django.urls import path

from . import views

app_name = 'commandes'

urlpatterns = [
    path('', views.passer_commande, name='passer'),
    path('mes-commandes/', views.mes_commandes, name='mes_commandes'),
    path('<str:numero>/confirmation/', views.confirmation, name='confirmation'),
    path('<str:numero>/preuve-de-paiement/', views.envoyer_preuve, name='envoyer_preuve'),
    path('<str:numero>/', views.detail, name='detail'),
]
