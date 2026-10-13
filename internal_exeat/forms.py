from django import forms

from guardians.forms import ParentChildExeatFormMixin
from .models import InternalExeat


class InternalExeatForm(ParentChildExeatFormMixin, forms.ModelForm):
    class Meta:
        model = InternalExeat
        fields = ["student", "purpose", "destination", "departure_date", "departure_time", "return_date", "return_time"]
        widgets = {
            "purpose": forms.TextInput(attrs={"id": "purpose", "placeholder": "State your reason clearly", "maxlength": 200}),
            "destination": forms.TextInput(attrs={"id": "destination", "placeholder": "Enter the destination", "maxlength": 200}),
            "departure_date": forms.DateInput(attrs={"id": "departure-date", "type": "date"}),
            "departure_time": forms.TimeInput(attrs={"id": "departure-time", "type": "time"}),
            "return_date": forms.DateInput(attrs={"id": "return-date", "type": "date"}),
            "return_time": forms.TimeInput(attrs={"id": "return-time", "type": "time"}),
        }
