# forms.py
from django.contrib.auth.forms import UserCreationForm
from main.models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']
