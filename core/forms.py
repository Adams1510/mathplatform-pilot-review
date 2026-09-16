from django import forms

from .models import SyntheticResponse


class ReadinessProofForm(forms.Form):
    acknowledgement = forms.BooleanField(
        label="Confirm this is a synthetic technical readiness check",
        required=True,
    )


class SyntheticStateForm(forms.Form):
    value = forms.ChoiceField(
        label="Synthetic state token",
        choices=SyntheticResponse.Value.choices,
        widget=forms.RadioSelect,
    )
    operation_id = forms.UUIDField(widget=forms.HiddenInput)
    base_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    content_version = forms.CharField(max_length=64, widget=forms.HiddenInput)
