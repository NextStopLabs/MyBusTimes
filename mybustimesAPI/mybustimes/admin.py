from django.contrib import admin
from .models import CustomUser, theme  # Import your models

admin.site.register(CustomUser)
admin.site.register(theme)
