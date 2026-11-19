"""Ajoute automatiquement les classes Bootstrap aux champs des formulaires Django."""
from django import forms


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            widget = champ.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect, forms.CheckboxSelectMultiple)):
                classe = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                classe = 'form-select'
            else:
                classe = 'form-control'
            widget.attrs['class'] = (widget.attrs.get('class', '') + ' ' + classe).strip()

    def full_clean(self):
        super().full_clean()
        # Bordure rouge Bootstrap sur les champs en erreur
        for nom in self.errors:
            if nom in self.fields:
                attrs = self.fields[nom].widget.attrs
                if 'is-invalid' not in attrs.get('class', ''):
                    attrs['class'] = attrs.get('class', '') + ' is-invalid'
