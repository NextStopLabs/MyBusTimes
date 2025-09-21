from django.contrib import admin
from .models import Link, AffiliateLink

# Register your models here.
@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'active', 'clicks')
    list_filter = ('active',)
    search_fields = ('name', 'url')
    ordering = ('name',)

@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ('tag', 'user', 'clicks', 'signups_from_clicks')
    search_fields = ('tag', 'user__username')
    ordering = ('-clicks',)