from django.contrib import admin
from .models import *

class CustomUserAdmin(admin.ModelAdmin):
    search_fields = ['username']
    list_filter = ['badges']

class themeAdmin(admin.ModelAdmin):
    search_fields = ['theme_name']

class liverieAdmin(admin.ModelAdmin):
    search_fields = ['liverie_name']

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
admin.site.register(featureToggle)