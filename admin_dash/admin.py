from django.contrib import admin
from .models import CustomModel
from simple_history.admin import SimpleHistoryAdmin

class CustomModelAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'description')
admin.site.register(CustomModel, CustomModelAdmin)