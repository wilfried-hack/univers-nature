from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator

from pages.bootstrap import BootstrapFormMixin

from .models import FORMATS_CAPTURE, Commande, ZoneLivraison


class CommandeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['nom', 'telephone', 'email', 'zone', 'adresse', 'mode_reglement', 'note']
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Quartier, rue, point de repère…'}),
            'note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Facultatif : horaire de livraison souhaité, précision…'}),
            'telephone': forms.TextInput(attrs={'placeholder': 'Ex. : 6 90 00 00 00', 'autocomplete': 'tel'}),
            'mode_reglement': forms.RadioSelect,
        }
        labels = {'email': 'E-mail (facultatif)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seulement les deux vrais modes de règlement (Django ajoute sinon une option vide « Choisir une option »)
        self.fields['mode_reglement'].choices = Commande.ModeReglement.choices
        self.fields['zone'].queryset = ZoneLivraison.objects.filter(active=True)
        self.fields['zone'].empty_label = 'Choisissez votre zone'
        self.fields['zone'].label_from_instance = (
            lambda z: f"{z.nom} — {z.frais:,} FCFA".replace(',', ' ')
            + ('' if z.paiement_livraison else ' (paiement Mobile Money avant expédition)')
        )

    def clean(self):
        donnees = super().clean()
        zone = donnees.get('zone')
        mode = donnees.get('mode_reglement')
        if zone and mode == Commande.ModeReglement.LIVRAISON and not zone.paiement_livraison:
            self.add_error(
                'mode_reglement',
                f'Le paiement à la livraison n’est pas disponible pour « {zone.nom} ». '
                'Choisissez le paiement par Mobile Money.',
            )
        return donnees


class PreuvePaiementForm(BootstrapFormMixin, forms.Form):
    """Preuve du transfert Mobile Money envoyée par le client sur le site : la référence, la capture d'écran, ou les deux."""

    reference_transfert = forms.CharField(
        label='Référence du transfert', max_length=80, required=False,
        help_text='Elle figure dans le SMS de confirmation Mobile Money (ex. : MP2611.1234.A56789).',
    )
    capture_paiement = forms.ImageField(
        label='Capture d’écran du message de confirmation', required=False,
        validators=[FileExtensionValidator(FORMATS_CAPTURE)],
        help_text='Image JPG, PNG ou WEBP, 5 Mo maximum.',
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
    )

    def clean_reference_transfert(self):
        return self.cleaned_data['reference_transfert'].strip()

    def clean_capture_paiement(self):
        capture = self.cleaned_data.get('capture_paiement')
        if capture and capture.size > settings.TAILLE_MAX_CAPTURE:
            raise forms.ValidationError('L’image est trop lourde (5 Mo maximum).')
        return capture

    def clean(self):
        donnees = super().clean()
        if not self.errors and not donnees.get('reference_transfert') and not donnees.get('capture_paiement'):
            raise forms.ValidationError('Indiquez la référence du transfert ou ajoutez une capture d’écran.')
        return donnees
