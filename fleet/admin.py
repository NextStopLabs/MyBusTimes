from django.contrib import admin
from django.utils import timezone
from .models import *

@admin.action(description='Approve selected changes')
def approve_changes(modeladmin, request, queryset):
    queryset.update(
        approved=True,
        pending=False,
        disapproved=False,
        approved_at=timezone.now()
    )

@admin.action(description='Decline selected changes')
def decline_changes(modeladmin, request, queryset):
    queryset.update(
        approved=False,
        pending=False,
        disapproved=True,
        approved_at=None 
    )

class FleetChangeAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'operator', 'user', 'approved_by', 'status', 'create_at', 'approved_at')
    list_filter = ('pending', 'approved', 'disapproved')
    actions = [approve_changes, decline_changes]

    def status(self, obj):
        if obj.approved:
            return "Approved"
        elif obj.disapproved:
            return "Declined"
        elif obj.pending:
            return "Pending"
        return "Unknown"
    status.short_description = 'Status'

class reservedOperatorNameAdmin(admin.ModelAdmin):
    search_fields = ['operator_name']
    list_filter = ['approved']
    list_display = ('operator_name', 'owner', 'approved', 'created_at', 'updated_at')

class operatorTypeAdmin(admin.ModelAdmin):
    search_fields = ['operator_type_name']

class liverieAdmin(admin.ModelAdmin):
    search_fields = ['name']

class typeAdmin(admin.ModelAdmin):
    list_display = ('type_name', 'active', 'double_decker', 'added_by', 'aproved_by')
    search_fields = ['type_name']

class fleetAdmin(admin.ModelAdmin):
    search_fields = ['id']
    list_display = ('fleet_number', 'operator', 'reg', 'vehicleType', 'livery', 'in_service', 'for_sale')
    list_filter = ['fleet_number', 'reg'] 

    def save_model(self, request, obj, form, change):
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)

class groupAdmin(admin.ModelAdmin):
    search_fields = ['group_name']

class organisationAdmin(admin.ModelAdmin):
    search_fields = ['organisation_name']

class TicketsAdmin(admin.ModelAdmin):
    search_fields = ['ticket_name', 'operator__operator_name']
    list_display = ('ticket_name', 'operator', 'created_at', 'updated_at')

admin.site.register(liverie, liverieAdmin)
admin.site.register(vehicleType, typeAdmin)
admin.site.register(fleet, fleetAdmin)
admin.site.register(fleetChange, FleetChangeAdmin)
admin.site.register(group, groupAdmin)
admin.site.register(organisation, organisationAdmin)
admin.site.register(MBTOperator)
admin.site.register(helper)
admin.site.register(helperPerm)
admin.site.register(companyUpdate)
admin.site.register(operatorType, operatorTypeAdmin)
admin.site.register(reservedOperatorName, reservedOperatorNameAdmin)
admin.site.register(ticket, TicketsAdmin)
admin.site.register(mapTileSet)