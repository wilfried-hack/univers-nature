from django.urls import path

from . import views

app_name = 'gestion'

urlpatterns = [
    path('', views.tableau_de_bord, name='tableau_de_bord'),
    path('commandes/', views.commandes, name='commandes'),
    path('commandes/<int:pk>/', views.commande_detail, name='commande'),
    path('commandes/<int:pk>/suivi/', views.commande_suivi_rapide, name='commande_suivi'),
    path('commandes/<int:pk>/preuve/', views.preuve, name='preuve'),
    path('produits/', views.produits, name='produits'),
    path('produits/ajouter/', views.produit_form, name='produit_ajouter'),
    path('produits/<int:pk>/', views.produit_form, name='produit_modifier'),
    path('produits/<int:pk>/stock/', views.produit_stock, name='produit_stock'),
    path('produits/<int:pk>/supprimer/', views.produit_supprimer, name='produit_supprimer'),
    path('categories/', views.categories, name='categories'),
    path('categories/<int:pk>/', views.categories, name='categorie_modifier'),
    path('categories/<int:pk>/supprimer/', views.categorie_supprimer, name='categorie_supprimer'),
    path('zones/', views.zones, name='zones'),
    path('zones/<int:pk>/', views.zones, name='zone_modifier'),
    path('zones/<int:pk>/supprimer/', views.zone_supprimer, name='zone_supprimer'),
    path('clients/', views.clients, name='clients'),
    path('clients/<int:pk>/basculer/', views.client_basculer, name='client_basculer'),
    path('statistiques/', views.statistiques, name='statistiques'),
]
