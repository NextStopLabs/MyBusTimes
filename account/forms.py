# forms.py
from django.contrib.auth.forms import UserCreationForm
from main.models import CustomUser
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from django import forms

User = get_user_model()

username_validator = RegexValidator(
    regex=r'^[\w.@+-]+$',
    message='Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.'
)

class AccountSettingsForm(forms.ModelForm):
    username = forms.CharField(validators=[username_validator])
    class Meta:
        model = User
        fields = ['username', 'email', 'discord_username', 'pfp', 'banner', 'reg_background']

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']
