from django import forms
from main.models import ad
from fleet.models import liverie, reservedOperatorName, vehicleType

def reserved_operator_name_message(reservation):
    return f"This operator name ({reservation.operator_name}) is reserved, if you think this is a mistake please open a ticket via discord or on the site"

class AdForm(forms.ModelForm):
    class Meta:
        model = ad
        fields = '__all__'  # or list specific fields like ['title', 'image', 'link']

class LiveryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = liverie
        fields = '__all__'
        widgets = {
            'left_css': forms.Textarea(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'right_css': forms.Textarea(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'text_colour': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'stroke_colour': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'colour': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        reservation = reservedOperatorName.blocking_reservation_for_user(name, self.request_user)
        if reservation:
            raise forms.ValidationError(reserved_operator_name_message(reservation))
        return name

class VehicleForm(forms.ModelForm):
    class Meta:
        model = vehicleType
        fields = ['type_name', 'double_decker', 'active', 'hidden', 'type', 'fuel', 'aproved_by']
    
