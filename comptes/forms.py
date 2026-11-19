from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from pages.bootstrap import BootstrapFormMixin


class ConnexionForm(BootstrapFormMixin, AuthenticationForm):
    pass


class InscriptionForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(label='Prénom', max_length=150)
    last_name = forms.CharField(label='Nom', max_length=150)
    email = forms.EmailField(label='E-mail')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {'username': "Nom d'utilisateur"}

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Un compte existe déjà avec cette adresse e-mail.')
        return email
