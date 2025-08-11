from django.contrib import admin
from django.utils import timezone
from .models import *
from django import forms

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

@admin.action(description='Deduplicate Full Fleet')
def deduplicate_fleet(modeladmin, request, queryset):
    seen = {}
    duplicates = []

    for obj in queryset:
        key = (obj.reg.strip().upper(), obj.fleet_number.strip().upper())
        if key in seen:
            duplicates.append(obj)
        else:
            seen[key] = obj

    for dup in duplicates:
        # You can customize this merge logic, e.g., keep the most complete one
        dup.delete()

    modeladmin.message_user(request, f"{len(duplicates)} duplicates removed.")

class fleetAdmin(admin.ModelAdmin):
    search_fields = ['fleet_number', 'reg']
    list_display = ('fleet_number', 'operator', 'reg', 'vehicleType', 'livery', 'in_service', 'for_sale')
    list_filter = ['operator']
    actions = [deduplicate_fleet]

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset.filter(in_service=True), use_distinct

    def save_model(self, request, obj, form, change):
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)

class groupAdmin(admin.ModelAdmin):
    search_fields = ['group_name']

class organisationAdmin(admin.ModelAdmin):
    search_fields = ['organisation_name']

@admin.action(description='Deduplicate')
def deduplicate_tickets(modeladmin, request, queryset):
    seen = set()
    duplicates = []

    for ticket in queryset.order_by('ticket_name', 'ticket_price', 'id'):
        key = (ticket.ticket_name.strip().lower(), ticket.ticket_price)
        if key in seen:
            duplicates.append(ticket)
        else:
            seen.add(key)

    count = len(duplicates)
    for dup in duplicates:
        dup.delete()

    modeladmin.message_user(request, f"{count} duplicate ticket(s) removed.")

class TicketsAdmin(admin.ModelAdmin):
    search_fields = ['ticket_name', 'operator__operator_name']
    list_display = ('ticket_name', 'operator', 'created_at', 'updated_at')
    list_filter = ('operator',)
    actions = [deduplicate_tickets]

class MBTOperatorAdmin(admin.ModelAdmin):
    search_fields = ['operator_name', 'operator_code']
    list_display = ('operator_name', 'operator_code', 'private', 'public')
    list_filter = ('private', 'public', 'owner')

class HelperAdminForm(forms.ModelForm):
    class Meta:
        model = helper
        fields = '__all__'
        widgets = {
            'operator': forms.Select(attrs={'class': 'select2'}),
            'helper': forms.Select(attrs={'class': 'select2'}),
        }

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/css/select2.min.css',),
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.full.min.js',
            'https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js',  # Ensure jQuery is loaded
            'js/select2-init.js',       # This will initialize select2
        )
class HelperAdmin(admin.ModelAdmin):
    autocomplete_fields = ['operator', 'helper']
    list_display = ['operator', 'helper']
    filter_horizontal = ['perms']

admin.site.register(liverie, liverieAdmin)
admin.site.register(vehicleType, typeAdmin)
admin.site.register(fleet, fleetAdmin)
admin.site.register(fleetChange, FleetChangeAdmin)
admin.site.register(group, groupAdmin)
admin.site.register(organisation, organisationAdmin)
admin.site.register(MBTOperator, MBTOperatorAdmin)
admin.site.register(helper, HelperAdmin)
admin.site.register(helperPerm)
admin.site.register(companyUpdate)
admin.site.register(operatorType, operatorTypeAdmin)
admin.site.register(reservedOperatorName, reservedOperatorNameAdmin)
admin.site.register(ticket, TicketsAdmin)
admin.site.register(mapTileSet)