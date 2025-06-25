from django import forms
from .models import Trip

class trackingForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['tracking_vehicle', 'tracking_route', 'tracking_start_at', 'tracking_end_at', 'tracking_data', 'tracking_start_location', 'tracking_end_location']

        widgets = {
            'tracking_start_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
            'tracking_end_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
            'tracking_data': forms.HiddenInput(),
        }

class updateTrackingForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['tracking_data', 'tracking_history_data']