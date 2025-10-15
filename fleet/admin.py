from django.contrib import admin, messages
from django.utils import timezone
from .models import *
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.filters import RelatedFieldListFilter
from django.contrib.admin.widgets import AutocompleteSelect
from admin_auto_filters.filters import AutocompleteFilter
from django.contrib.admin.sites import site
from simple_history.admin import SimpleHistoryAdmin
from django.utils.safestring import mark_safe

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

class FleetChangeAdmin(SimpleHistoryAdmin):
    list_display = ('vehicle', 'operator', 'user', 'approved_by', 'status', 'create_at', 'approved_at')
    list_filter = ('pending', 'approved', 'disapproved')
    actions = [approve_changes, decline_changes]
    list_select_related = ('vehicle', 'operator', 'user', 'approved_by')  # KEY FIX

    def status(self, obj):
        if obj.approved:
            return "Approved"
        elif obj.disapproved:
            return "Declined"
        elif obj.pending:
            return "Pending"
        return "Unknown"
    status.short_description = 'Status'

class reservedOperatorNameAdmin(SimpleHistoryAdmin):
    search_fields = ['operator_slug']
    list_filter = ['approved']
    list_display = ('operator_name', 'owner', 'approved', 'created_at', 'updated_at')

class operatorTypeAdmin(SimpleHistoryAdmin):
    search_fields = ['operator_type_name']

# ---------------------------
# Custom Filters
# ---------------------------

class OperatorOwnerFilter(AutocompleteFilter):
    title = "Owner"
    field_name = "owner"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("owner__name")

class OperatorGroupFilter(AutocompleteFilter):
    title = "Group"
    field_name = "group"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("group__group_name")
    
class OperatorOrganisationFilter(AutocompleteFilter):
    title = "Organisation"
    field_name = "organisation"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("organisation__organisation_name")

@admin.register(MBTOperator)
class MBTOperatorAdmin(SimpleHistoryAdmin):
    search_fields = ['operator_name', 'operator_code']
    list_display = ('operator_name', 'operator_slug', 'operator_code', 'owner', 'vehicles_for_sale')
    list_editable = ('owner',)
    autocomplete_fields = ('owner',)
    ordering = ['operator_name']
    list_filter = (OperatorOwnerFilter, OperatorGroupFilter, OperatorOrganisationFilter)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset.order_by('operator_name'), use_distinct

@admin.register(vehicleType)
class VehicleTypeAdmin(SimpleHistoryAdmin):
    search_fields = ['type_name']
    ordering = ['type_name']

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset.order_by('type_name'), use_distinct

class LiveryUserFilter(AutocompleteFilter):
    title = "User"
    field_name = "added_by"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("added_by__name")

@admin.register(liverie)
class LiveryAdmin(SimpleHistoryAdmin):
    search_fields = ['name']
    ordering = ['name']
    list_display = ['id', 'name', 'left', 'right', 'BLOB', 'published']
    list_filter = ['published', LiveryUserFilter]

    def left(self, obj):
        return mark_safe(f"""
            <svg height="24" width="36" style="line-height:24px;font-size:24px;background:{obj.left_css}">
                <text x="50%" y="85%" fill="{obj.text_colour}" text-anchor="middle" style="stroke:{obj.stroke_colour};stroke-width:3px;paint-order:stroke">42</text>
            </svg>
        """)
    
    def right(self, obj):
        return mark_safe(f"""
            <svg height="24" width="36" style="line-height:24px;font-size:24px;background:{obj.right_css}">
                <text x="50%" y="85%" fill="{obj.text_colour}" text-anchor="middle" style="stroke:{obj.stroke_colour};stroke-width:3px;paint-order:stroke">42</text>
            </svg>
        """)
    
    def BLOB(self, obj):
        return mark_safe(f"""
            <div style="background:{obj.colour}; width: 20px; height: 20px; border-radius: 50%;"></div>
        """)
    
    left.short_description = "Left Preview"
    right.short_description = "Right Preview"
    BLOB.short_description = "Colour"

# ---------------------------
# Custom Filters
# ---------------------------

class FleetOperatorFilter(AutocompleteFilter):
    title = "Operator"
    field_name = "operator"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("operator__operator_name")

class FleetVehicleTypeFilter(AutocompleteFilter):
    title = "Vehicle Type"
    field_name = "vehicleType"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("vehicleType__type_name")

class FleetLiveryFilter(AutocompleteFilter):
    title = "Livery"
    field_name = "livery"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("livery__name")


# ---------------------------
# Custom Form for Transfers
# ---------------------------

class TransferVehiclesForm(forms.Form):
    new_operator = forms.ModelChoiceField(
        label="New Operator",
        queryset=MBTOperator.objects.all(),
        widget=AutocompleteSelect(
            field=fleet._meta.get_field("operator"),
            admin_site=admin.site,
        ),
    )

# ---------------------------
# Admin Actions
# ---------------------------

@admin.action(description="Deduplicate Full Fleet")
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
        dup.delete()

    modeladmin.message_user(request, f"{len(duplicates)} duplicates removed.", messages.SUCCESS)


@admin.action(description="Mark selected vehicles as For Sale")
def mark_as_for_sale(modeladmin, request, queryset):
    in_service_qs = queryset.filter(in_service=True)
    updated_count = in_service_qs.update(for_sale=True)
    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as for sale.", messages.SUCCESS)


@admin.action(description="Mark selected vehicles as Not For Sale")
def ukmark_as_for_sale(modeladmin, request, queryset):
    updated = queryset.update(for_sale=False)
    modeladmin.message_user(request, f"{updated} vehicle(s) marked as not for sale.", messages.SUCCESS)


@admin.action(description="Sell 25 random vehicles")
def sell_random_25(modeladmin, request, queryset):
    count = queryset.count()
    if count <= 25:
        updated = queryset.update(for_sale=True)
        modeladmin.message_user(request, f"All {updated} vehicle(s) marked as for sale.", messages.SUCCESS)
    else:
        random_ids = list(queryset.order_by("?").values_list("pk", flat=True)[:25])
        updated = queryset.filter(pk__in=random_ids).update(for_sale=True)
        modeladmin.message_user(request, f"{updated} vehicle(s) marked as for sale.", messages.SUCCESS)


@admin.action(description="Sell 100 random vehicles")
def sell_random_100(modeladmin, request, queryset):
    count = queryset.count()
    if count <= 100:
        updated = queryset.update(for_sale=True)
        modeladmin.message_user(request, f"All {updated} vehicle(s) marked as for sale.", messages.SUCCESS)
    else:
        random_ids = list(queryset.order_by("?").values_list("pk", flat=True)[:100])
        updated = queryset.filter(pk__in=random_ids).update(for_sale=True)
        modeladmin.message_user(request, f"{updated} vehicle(s) marked as for sale.", messages.SUCCESS)


@admin.action(description="Transfer selected vehicles to another operator")
def transfer_vehicles(modeladmin, request, queryset):
    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    return redirect(f"transfer-vehicles/?ids={','.join(selected)}")


# ---------------------------
# Fleet Admin
# ---------------------------

@admin.register(fleet)
class FleetAdmin(SimpleHistoryAdmin):
    search_fields = ["fleet_number", "reg", "operator__operator_name"]
    list_display = (
        "fleet_number",
        "operator",
        "reg",
        "vehicleType",
        "livery",
        "in_service",
        "for_sale",
    )
    list_filter = (
        "for_sale",
        FleetVehicleTypeFilter,
        FleetOperatorFilter,
        FleetLiveryFilter,
    )
    autocomplete_fields = ["operator", "loan_operator", "livery", "vehicleType", "last_modified_by"]
    actions = [
        deduplicate_fleet,
        mark_as_for_sale,
        ukmark_as_for_sale,
        sell_random_25,
        sell_random_100,
        transfer_vehicles,
    ]
    ordering = ("operator__operator_name", "fleet_number")
    list_per_page = 100
    date_hierarchy = None  # fleets usually don’t have datetime, but kept here for consistency

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "transfer-vehicles/",
                self.admin_site.admin_view(self.transfer_vehicles_view),
                name="transfer_vehicles",
            ),
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
                self.message_user(request, "Transfer failed. Please check the form.", messages.ERROR)
        else:
            form = TransferVehiclesForm()

        return render(
            request,
            "admin/transfer_vehicles.html",
            {"form": form, "vehicles": queryset, "title": "Transfer Vehicles"},
        )

class groupAdmin(SimpleHistoryAdmin):
    search_fields = ['group_name']

class organisationAdmin(SimpleHistoryAdmin):
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

class TicketsAdmin(SimpleHistoryAdmin):
    search_fields = ['ticket_name', 'operator__operator_name']
    list_display = ('ticket_name', 'operator', 'created_at', 'updated_at')
    list_filter = ('operator',)
    actions = [deduplicate_tickets]

@admin.action(description='reset for sale count')
def reset_for_sale_count(modeladmin, request, queryset):
    updated = queryset.update(vehicles_for_sale=0)
    modeladmin.message_user(request, f"{updated} operator(s) reset for sale count.")

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
class HelperAdmin(SimpleHistoryAdmin):
    autocomplete_fields = ['operator', 'helper']
    list_display = ('operator', 'helper')
    actions = ['delete_selected']  # optional but safe

admin.site.register(fleetChange, FleetChangeAdmin)
admin.site.register(group, groupAdmin)
admin.site.register(organisation, organisationAdmin)
admin.site.register(helper, HelperAdmin)
admin.site.register(helperPerm)
admin.site.register(companyUpdate)
admin.site.register(operatorType, operatorTypeAdmin)
admin.site.register(reservedOperatorName, reservedOperatorNameAdmin)
admin.site.register(ticket, TicketsAdmin)
admin.site.register(mapTileSet)