from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import InscriptionForm


def inscription(request):
    if request.user.is_authenticated:
        return redirect('comptes:espace')
    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Bienvenue {user.first_name} ! Votre compte est créé.')
        return redirect('comptes:espace')
    return render(request, 'comptes/inscription.html', {'form': form})


@login_required
def espace(request):
    if request.user.is_staff:  # l'équipe arrive directement sur l'espace de gestion
        return redirect('gestion:tableau_de_bord')
    commandes = request.user.commandes.all()[:5]
    return render(request, 'comptes/espace.html', {'commandes': commandes})
