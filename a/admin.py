from django.contrib import admin
from django.utils.html import format_html
from .models import Link, AffiliateLink


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'active', 'clicks')
    list_filter = ('active',)
    search_fields = ('name', 'url')
    ordering = ('name',)

    readonly_fields = ('affiliate_link',)

    def affiliate_link(self, obj):
        if obj.pk:  # only show if the object is saved
            return format_html(
                '<a href="https://www.mybustimes.cc/a/{0}" target="_blank">'
                'https://www.mybustimes.cc/a/{0}</a>', obj.name
            )
        return "-"
    affiliate_link.short_description = "Affiliate Link"

@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ('tag', 'user', 'clicks', 'signups_from_clicks')
    search_fields = ('tag', 'user__username')
    ordering = ('-clicks',)