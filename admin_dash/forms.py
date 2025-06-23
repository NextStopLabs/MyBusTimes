from django import forms
from main.models import ad
from fleet.models import liverie

class AdForm(forms.ModelForm):
    class Meta:
        model = ad
        fields = '__all__'  # or list specific fields like ['title', 'image', 'link']

class LiveryForm(forms.ModelForm):
    class Meta:
        model = liverie
        fields = '__all__'
        widgets = {
            'left_css': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'right_css': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'text_colour': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'stroke_colour': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
            'colour': forms.TextInput(attrs={'class': 'color-input', 'oninput': 'updatePreview(this)'}),
        }
