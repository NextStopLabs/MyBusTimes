from django.contrib import admin
from .models import CustomModel
class CustomModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
admin.site.register(CustomModel, CustomModelAdmin)