from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import ConnexionForm

app_name = 'comptes'

urlpatterns = [
    path('inscription/', views.inscription, name='inscription'),
    path('connexion/', auth_views.LoginView.as_view(redirect_authenticated_user=True, authentication_form=ConnexionForm),
         name='connexion'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),  # accepte seulement POST
    path('', views.espace, name='espace'),
]
