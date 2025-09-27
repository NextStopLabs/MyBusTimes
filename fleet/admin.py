from django.contrib import admin, messages
from django.utils import timezone
from .models import *
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME

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
    search_fields = ['operator_slug']
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

def mark_as_for_sale(modeladmin, request, queryset):
    # Only update vehicles that are in service
    in_service_qs = queryset.filter(in_service=True)
    updated_count = in_service_qs.update(for_sale=True)

    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as for sale.")

mark_as_for_sale.short_description = "Mark selected vehicles as For Sale"

def ukmark_as_for_sale(modeladmin, request, queryset):
    updated = queryset.update(for_sale=False)
    modeladmin.message_user(request, f"{updated} vehicle(s) marked as not for sale.")
ukmark_as_for_sale.short_description = "Mark selected vehicles as Not For Sale"

def sell_random_25(modeladmin, request, queryset):
    count = queryset.count()
    if count <= 25:
        updated = queryset.update(for_sale=True)
        modeladmin.message_user(request, f"All {updated} vehicle(s) marked as for sale.")
    else:
        random_25_ids = list(queryset.order_by('?').values_list('pk', flat=True)[:25])
        updated = queryset.filter(pk__in=random_25_ids).update(for_sale=True)
        modeladmin.message_user(request, f"{updated} vehicle(s) marked as for sale.")

def sell_random_100(modeladmin, request, queryset):
    count = queryset.count()
    if count <= 100:
        updated = queryset.update(for_sale=True)
        modeladmin.message_user(request, f"All {updated} vehicle(s) marked as for sale.")
    else:
        random_100_ids = list(queryset.order_by('?').values_list('pk', flat=True)[:100])
        updated = queryset.filter(pk__in=random_100_ids).update(for_sale=True)
        modeladmin.message_user(request, f"{updated} vehicle(s) marked as for sale.")

class TransferVehiclesForm(forms.Form):
    new_operator = forms.ModelChoiceField(
        label="New Operator",
        queryset=MBTOperator.objects.order_by("operator_name"),
    )

def transfer_vehicles(modeladmin, request, queryset):
    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    return redirect(f"transfer-vehicles/?ids={','.join(selected)}")

transfer_vehicles.short_description = "Transfer selected vehicles to another operator"


class fleetAdmin(admin.ModelAdmin):
    search_fields = ['fleet_number', 'reg']
    list_display = ('fleet_number', 'operator', 'reg', 'vehicleType', 'livery', 'in_service', 'for_sale')
    list_filter = ['operator', 'for_sale']
    actions = [
        deduplicate_fleet,
        mark_as_for_sale,
        ukmark_as_for_sale,
        sell_random_25,
        sell_random_100,
        transfer_vehicles,
    ]
    autocomplete_fields = ['operator', 'loan_operator', 'livery', 'vehicleType', 'last_modified_by']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("transfer-vehicles/", self.admin_site.admin_view(self.transfer_vehicles_view), name="transfer_vehicles"),
        ]
        return custom_urls + urls

    def transfer_vehicles_view(self, request):
        ids = request.GET.get("ids", "")
        queryset = self.model.objects.filter(pk__in=ids.split(","))

        if request.method == "POST":
            form = TransferVehiclesForm(request.POST)
            if form.is_valid():
                new_operator = form.cleaned_data["new_operator"]

                updated = queryset.update(operator=new_operator)
                self.message_user(
                    request,
                    f"{updated} vehicle(s) transferred to {new_operator.operator_name}.",
                    level=messages.SUCCESS,
                )
                return redirect("..")

        else:
            form = TransferVehiclesForm()

        return render(request, "admin/transfer_vehicles.html", {
            "form": form,
            "vehicles": queryset,
            "title": "Transfer Vehicles",
        })

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

@admin.action(description='reset for sale count')
def reset_for_sale_count(modeladmin, request, queryset):
    updated = queryset.update(vehicles_for_sale=0)
    modeladmin.message_user(request, f"{updated} operator(s) reset for sale count.")

class MBTOperatorAdmin(admin.ModelAdmin):
    search_fields = ['operator_name', 'operator_code', 'operator_slug']
    list_display = ('operator_name', 'operator_code', 'operator_slug', 'vehicles_for_sale')
    list_filter = ('private', 'public', 'owner')
    autocomplete_fields = ['owner', 'group', 'organisation']
    actions = [reset_for_sale_count]

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
            'all': ('/static/css/select2.min.css',),
        }
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/select2/4.0.13/js/select2.full.min.js',
            'https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js',  # Ensure jQuery is loaded
            'js/select2-init.js',       # This will initialize select2
        )
class HelperAdmin(admin.ModelAdmin):
    autocomplete_fields = ['operator', 'helper']
    list_display = ('operator', 'helper')
    actions = ['delete_selected']  # optional but safe

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