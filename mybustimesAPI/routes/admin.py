from django.contrib import admin
from .models import *

class routeAdmin(admin.ModelAdmin):
    search_fields = ['route_num']
    list_filter = ['route_num', 'route_name', 'inboud_destination', 'outboud_destination', 'route_operators'] 
    list_display = ['route_num', 'route_name', 'inboud_destination', 'outboud_destination']

class stopAdmin(admin.ModelAdmin):
    search_fields = ['stop_name']
    list_display = ['stop_name', 'latitude', 'longitude']

class dayTypeAdmin(admin.ModelAdmin):
    list_display = ['name']

class timetableEntryAdmin(admin.ModelAdmin):
    list_display = ['route', 'stop', 'get_day_types', 'get_times']
    list_filter = ['route', 'stop']
    search_fields = ['route__route_num', 'stop__stop_name']
    filter_horizontal = ['day_type']

    def get_day_types(self, obj):
        return ", ".join([day.name for day in obj.day_type.all()])
    get_day_types.short_description = 'Day Types'  # Make sure this is labeled in the admin view
    
    def get_times(self, obj):
        return ", ".join(obj.times)  # Access the list of times stored in the JSONField
    get_times.short_description = 'Times'  # Label for the times field

class serviceUpdateAdmin(admin.ModelAdmin):
    list_display = ['effected_routes_list', 'start_date', 'end_date']
    list_filter = ['start_date', 'end_date']
    search_fields = ['effected_route__route_num']
    date_hierarchy = 'start_date'

    def effected_routes_list(self, obj):
        return ", ".join([r.route_num for r in obj.effected_route.all()])
    effected_routes_list.short_description = 'Effected Routes'


admin.site.register(route, routeAdmin)
admin.site.register(serviceUpdate, serviceUpdateAdmin)
admin.site.register(stop, stopAdmin)
admin.site.register(dayType, dayTypeAdmin)
admin.site.register(timetableEntry, timetableEntryAdmin)
