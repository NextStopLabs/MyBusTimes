from django.contrib import admin
from .models import Link

# Register your models here.
@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'active', 'clicks')
    list_filter = ('active',)
    search_fields = ('name', 'url')
    ordering = ('name',)