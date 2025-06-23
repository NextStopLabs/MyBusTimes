from django.contrib import admin
from .models import *
from django.utils.html import format_html
from django.contrib import messages

class GameTrackingAdmin(admin.ModelAdmin):
    list_display = ('tracking_id', 'tracking_vehicle', 'tracking_route', 'trip_ended', 'tracking_start_at', 'tracking_end_at')
    search_fields = ('tracking_id', 'tracking_vehicle', 'tracking_route')
    list_filter = ('tracking_vehicle', 'tracking_route')
    actions = ['end_trip', 'unend_trip']

    @admin.action(description='End selected trips')
    def end_trip(self, request, queryset):
        updated = queryset.update(trip_ended=True)
        self.message_user(request, f"{updated} trip(s) marked as ended.", messages.SUCCESS)

    @admin.action(description='Un-end selected trips')
    def unend_trip(self, request, queryset):
        updated = queryset.update(trip_ended=False)
        self.message_user(request, f"{updated} trip(s) marked as not ended.", messages.SUCCESS)

admin.site.register(GameTracking, GameTrackingAdmin)

