from django.contrib import admin
from .models import *
from django.utils.html import format_html

class routeAdmin(admin.ModelAdmin):
    search_fields = ['route_num']
    list_filter = ['route_num', 'route_name', 'inbound_destination', 'outbound_destination', 'route_operators'] 
    list_display = ['route_num', 'route_name', 'inbound_destination', 'outbound_destination']

class stopAdmin(admin.ModelAdmin):
    search_fields = ['stop_name']
    list_display = ['stop_name', 'latitude', 'longitude']

class dayTypeAdmin(admin.ModelAdmin):
    list_display = ['name']

class timetableEntryAdmin(admin.ModelAdmin):
    list_display = ['route', 'get_day_types', 'get_operator_schedule']
    list_filter = ['route']
    search_fields = ['route__route_num']
    filter_horizontal = ['day_type']

    def get_day_types(self, obj):
        return ", ".join([day.name for day in obj.day_type.all()])
    get_day_types.short_description = 'Day Types'

    def get_operator_schedule(self, obj):
        return ", ".join(obj.operator_schedule)
    get_operator_schedule.short_description = 'Operator Schedule'

class routeStopsAdmin(admin.ModelAdmin):
    list_display = ['route', 'inbound', 'circular', 'get_stops']
    list_filter = ['route', 'inbound', 'circular']
    search_fields = ['route__route_num']

    def get_stops(self, obj):
        # obj.stops is a list of dicts, so join their 'stop' values
        return ", ".join(stop['stop'] for stop in obj.stops)
    get_stops.short_description = 'Stops'

class serviceUpdateAdmin(admin.ModelAdmin):
    list_display = ['effected_routes_list', 'start_date', 'end_date']
    list_filter = ['start_date', 'end_date']
    search_fields = ['effected_route__route_num']
    date_hierarchy = 'start_date'

    def effected_routes_list(self, obj):
        return ", ".join([r.route_num for r in obj.effected_route.all()])
    effected_routes_list.short_description = 'Effected Routes'

class dutyAdmin(admin.ModelAdmin):
    list_display = ['duty_name', 'get_day_types', 'duty_operator']

    def get_day_types(self, obj):
        return ", ".join([duty_day.name for duty_day in obj.duty_day.all()])
    get_day_types.short_description = 'Day Types'

class dutyAdminTrip(admin.ModelAdmin):
    list_display = ['duty', 'route', 'start_time', 'start_at', 'end_time', 'end_at']

@admin.register(transitAuthoritiesColour)
class TransitAuthoritiesColourAdmin(admin.ModelAdmin):
    list_display = ('id', 'authority_code', 'colour_display')

    def colour_display(self, obj):
        return format_html(
            '<div style="background-color: {}; color: {}; padding: 5px;">Sample Text</div>',
            obj.primary_colour,
            obj.secondary_colour
        )
    colour_display.short_description = 'Colour Preview'


admin.site.register(route, routeAdmin)
admin.site.register(serviceUpdate, serviceUpdateAdmin)
admin.site.register(stop, stopAdmin)
admin.site.register(dayType, dayTypeAdmin)
admin.site.register(timetableEntry, timetableEntryAdmin)
admin.site.register(routeStop, routeStopsAdmin)
admin.site.register(duty, dutyAdmin)
admin.site.register(dutyTrip, dutyAdminTrip)

admin.site.site_header = "MyBusTimes Admin"