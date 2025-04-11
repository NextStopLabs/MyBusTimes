from django.contrib import admin
from .models import *

def toggle_maintenance(modeladmin, request, queryset):
    for obj in queryset:
        obj.maintenance = not obj.maintenance
        obj.save()

    modeladmin.message_user(request, f"Toggled maintenance status for {queryset.count()} items.")

toggle_maintenance.short_description = "Toggle maintenance status"

def toggle_coming_soon(modeladmin, request, queryset):
    for obj in queryset:
        obj.coming_soon = not obj.coming_soon
        obj.save()

    modeladmin.message_user(request, f"Toggled coming soon status for {queryset.count()} items.")

toggle_coming_soon.short_description = "Toggle coming soon status"

def toggle_enabled(modeladmin, request, queryset):
    for obj in queryset:
        obj.enabled = not obj.enabled
        obj.save()

    modeladmin.message_user(request, f"Toggled enabled status for {queryset.count()} items.")

toggle_enabled.short_description = "Toggle enabled status"

class CustomUserAdmin(admin.ModelAdmin):
    search_fields = ['username']
    list_filter = ['badges']

class themeAdmin(admin.ModelAdmin):
    search_fields = ['theme_name']

class liverieAdmin(admin.ModelAdmin):
    search_fields = ['name']

class typeAdmin(admin.ModelAdmin):
    search_fields = ['type_name']

class fleetAdmin(admin.ModelAdmin):
    search_fields = ['id']
    list_filter = ['fleet_number', 'reg'] 

class groupAdmin(admin.ModelAdmin):
    search_fields = ['group_name']

class organisationAdmin(admin.ModelAdmin):
    search_fields = ['organisation_name']

class regionAdmin(admin.ModelAdmin):
    search_fields = ['region_name']

class badgeAdmin(admin.ModelAdmin):
    search_fields = ['badge_name']

class routeAdmin(admin.ModelAdmin):
    search_fields = ['route_num']
    list_filter = ['route_num', 'route_name', 'inboud_destination', 'outboud_destination', 'route_operator'] 

class featureAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['enabled', 'maintenance', 'coming_soon'] 
    list_display = ['name', 'enabled', 'maintenance', 'coming_soon']
    actions = [toggle_enabled, toggle_maintenance, toggle_coming_soon]

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(theme, themeAdmin)
admin.site.register(liverie, liverieAdmin)
admin.site.register(type, typeAdmin)
admin.site.register(fleet, fleetAdmin)
admin.site.register(FleetChangeLog)
admin.site.register(group, groupAdmin)
admin.site.register(organisation, organisationAdmin)
admin.site.register(operator)
admin.site.register(region, regionAdmin)
admin.site.register(route, routeAdmin)
admin.site.register(badge, badgeAdmin)
admin.site.register(ad)
admin.site.register(update)
admin.site.register(featureToggle, featureAdmin)