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
from django.utils.crypto import get_random_string
from django.db.models import Count
from django.db import connection, transaction

VEHICLE_TYPE_DEDUPE_USER_IDS = {51, 416}

def normalise_vehicle_type_name(type_name):
    return " ".join((type_name or "").split()).casefold()


def get_vehicle_type_duplicate_groups(queryset):
    selected_keys = {
        normalise_vehicle_type_name(type_name)
        for type_name in queryset.values_list("type_name", flat=True)
    }
    selected_keys.discard("")

    grouped_types = {}
    for vehicle_type in vehicleType.objects.all().order_by("id"):
        key = normalise_vehicle_type_name(vehicle_type.type_name)
        if key in selected_keys:
            grouped_types.setdefault(key, []).append(vehicle_type)

    duplicate_groups = []
    for duplicate_group in grouped_types.values():
        if len(duplicate_group) <= 1:
            continue

        duplicate_group.sort(key=lambda item: item.id)
        keeper = duplicate_group[0]
        duplicates = duplicate_group[1:]
        duplicate_ids = [item.id for item in duplicates]

        duplicate_groups.append({
            "keeper": keeper,
            "duplicates": duplicates,
            "vehicle_count": fleet.objects.filter(vehicleType_id__in=duplicate_ids).count(),
            "favourite_count": favouriteVehicleType.objects.filter(vehicle_type_id__in=duplicate_ids).count(),
            "replacement_count": VehicleTypeChangeRequest.objects.filter(
                replacement_type_id__in=duplicate_ids
            ).count(),
        })

    return duplicate_groups


@admin.action(description="Deduplicate selected vehicle types")
def deduplicate_vehicle_types(modeladmin, request, queryset):
    groups_to_merge = get_vehicle_type_duplicate_groups(queryset)

    if not queryset.exists():
        modeladmin.message_user(request, "No vehicle type names selected to deduplicate.", messages.WARNING)
        return

    if not groups_to_merge:
        modeladmin.message_user(request, "No duplicate vehicle types found for the selected names.", messages.INFO)
        return

    if "post" not in request.POST:
        return render(
            request,
            "admin/deduplicate_vehicle_types.html",
            {
                "title": "Confirm Vehicle Type Deduplication",
                "groups_to_merge": groups_to_merge,
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
                "queryset": queryset,
                "opts": modeladmin.model._meta,
            },
        )

    vehicle_updates = 0
    favourite_updates = 0
    favourite_deletes = 0
    replacement_updates = 0
    activated_types = 0
    unhidden_types = 0
    deleted_types = 0

    with transaction.atomic():
        for duplicate_group in groups_to_merge:
            keeper = duplicate_group["keeper"]
            duplicates = duplicate_group["duplicates"]
            duplicate_ids = [item.id for item in duplicates]

            if not keeper.active:
                activated_types += 1
            if keeper.hidden:
                unhidden_types += 1
            keeper.active = True
            keeper.hidden = False
            keeper.save(update_fields=["active", "hidden"])

            vehicle_updates += fleet.objects.filter(vehicleType_id__in=duplicate_ids).update(vehicleType=keeper)

            for duplicate in duplicates:
                duplicate_favourites = favouriteVehicleType.objects.filter(vehicle_type=duplicate)
                duplicate_user_ids = list(duplicate_favourites.values_list("user_id", flat=True))
                existing_keeper_user_ids = set(
                    favouriteVehicleType.objects.filter(
                        vehicle_type=keeper,
                        user_id__in=duplicate_user_ids,
                    ).values_list("user_id", flat=True)
                )

                if existing_keeper_user_ids:
                    favourite_deletes += duplicate_favourites.filter(user_id__in=existing_keeper_user_ids).delete()[0]

                favourite_updates += duplicate_favourites.exclude(
                    user_id__in=existing_keeper_user_ids
                ).update(vehicle_type=keeper)

            replacement_updates += VehicleTypeChangeRequest.objects.filter(
                replacement_type_id__in=duplicate_ids
            ).update(replacement_type=keeper)

            deleted_types += len(duplicate_ids)
            vehicleType.objects.filter(id__in=duplicate_ids).delete()

    modeladmin.message_user(
        request,
        (
            f"Deduplicated {len(groups_to_merge)} vehicle type name(s): "
            f"{vehicle_updates} fleet vehicle(s) moved, "
            f"{favourite_updates} favourite(s) moved, "
            f"{favourite_deletes} duplicate favourite(s) removed, "
            f"{replacement_updates} change request replacement(s) updated, "
            f"{deleted_types} duplicate row(s) deleted. "
            f"{activated_types} kept type(s) set active and {unhidden_types} kept type(s) unhidden."
        ),
        messages.SUCCESS,
    )

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
    autocomplete_fields = ('vehicle', 'operator', 'user', 'approved_by', 'voters')
    search_fields = (
        'vehicle__fleet_number',
        'vehicle__reg',
        'operator__operator_name',
        'user__username',
        'user__first_name',
        'user__last_name',
        'approved_by__username',
        'approved_by__first_name',
        'approved_by__last_name'
    )

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
    search_fields = ['operator_name', 'owner__username', 'approved_by__username', 'allowed_users__username']
    list_filter = ['approved']
    list_display = ('operator_name', 'owner', 'approved', 'approved_by', 'created_at', 'updated_at')
    autocomplete_fields = ('owner', 'approved_by', 'allowed_users')

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
        return qs.order_by("owner__username")

class OperatorGroupFilter(AutocompleteFilter):
    title = "Group"
    field_name = "group"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("group__group_name")


def delete_legacy_depots_for_operators(operator_ids):
    """Remove stale depot rows that still point at operators in older databases."""
    operator_ids = [operator_id for operator_id in operator_ids if operator_id]
    if not operator_ids:
        return 0

    table_name = "fleet_depot"
    if table_name not in connection.introspection.table_names():
        return 0

    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }
        if "operator_id" not in columns:
            return 0

        quoted_table = connection.ops.quote_name(table_name)
        placeholders = ", ".join(["%s"] * len(operator_ids))
        cursor.execute(
            f"DELETE FROM {quoted_table} WHERE operator_id IN ({placeholders})",
            operator_ids,
        )
        return cursor.rowcount
    
class OperatorOrganisationFilter(AutocompleteFilter):
    title = "Organisation"
    field_name = "organisation"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("organisation__organisation_name")

class AssignOperatorsOrganisationForm(forms.Form):
    organisation = forms.ModelChoiceField(
        label="Organisation",
        queryset=organisation.objects.all().order_by("organisation_name"),
        required=True,
        widget=AutocompleteSelect(
            field=MBTOperator._meta.get_field("organisation"),
            admin_site=admin.site,
        ),
    )

@admin.action(description="Add selected operators to an organisation")
def assign_operators_to_organisation(modeladmin, request, queryset):
    key = get_random_string(12)
    request.session[f"assign_operator_organisation_ids_{key}"] = list(queryset.values_list("id", flat=True))
    return redirect(f"/api-admin/fleet/mbtoperator/assign-organisation/?key={key}")

@admin.register(MBTOperator)
class MBTOperatorAdmin(SimpleHistoryAdmin):
    search_fields = ['operator_name', 'operator_code']
    list_display = ('operator_name', 'operator_slug', 'operator_code', 'owner', 'vehicles_for_sale')
    list_editable = ('owner',)
    autocomplete_fields = ('owner',)
    ordering = ['operator_name']
    list_filter = (OperatorOwnerFilter, OperatorGroupFilter, OperatorOrganisationFilter)
    actions = [assign_operators_to_organisation]

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset.order_by('operator_name'), use_distinct

    def delete_model(self, request, obj):
        delete_legacy_depots_for_operators([obj.pk])
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        operator_ids = list(queryset.values_list("pk", flat=True))
        delete_legacy_depots_for_operators(operator_ids)
        super().delete_queryset(request, queryset)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "assign-organisation/",
                self.admin_site.admin_view(self.assign_organisation_view),
                name="assign_operator_organisation",
            ),
        ]
        return custom_urls + urls

    def assign_organisation_view(self, request):
        key = request.GET.get("key")
        ids = request.session.get(f"assign_operator_organisation_ids_{key}", [])
        queryset = self.model.objects.filter(pk__in=ids).order_by("operator_name")

        if not ids:
            self.message_user(request, "No operators were selected.", messages.ERROR)
            return redirect("..")

        if request.method == "POST":
            form = AssignOperatorsOrganisationForm(request.POST)
            if form.is_valid():
                selected_organisation = form.cleaned_data["organisation"]
                updated = queryset.update(organisation=selected_organisation)
                request.session.pop(f"assign_operator_organisation_ids_{key}", None)
                self.message_user(
                    request,
                    f"{updated} operator(s) added to {selected_organisation.organisation_name}.",
                    level=messages.SUCCESS,
                )
                return redirect("..")

            self.message_user(request, "Organisation assignment failed. Please check the form.", messages.ERROR)
        else:
            form = AssignOperatorsOrganisationForm()

        return render(
            request,
            "admin/assign_operators_organisation.html",
            {
                "form": form,
                "operators": queryset,
                "title": "Add Operators To Organisation",
            },
        )

@admin.register(vehicleType)
class VehicleTypeAdmin(SimpleHistoryAdmin):
    search_fields = ['type_name',]
    ordering = ['type_name']
    list_display = ['id', 'type_name', 'vehicle_count', 'active', 'hidden', 'added_by', 'type', 'fuel']
    list_filter = ['type', 'added_by', 'fuel']
    autocomplete_fields = ['added_by', 'aproved_by']
    actions = [deduplicate_vehicle_types]

    def vehicle_count(self, obj):
        return obj.fleet_set.count()

    vehicle_count.short_description = "Vehicles Using"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.user.id not in VEHICLE_TYPE_DEDUPE_USER_IDS:
            actions.pop("deduplicate_vehicle_types", None)
        return actions

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset.order_by('type_name'), use_distinct

@admin.register(VehicleTypeChangeRequest)
class VehicleTypeChangeRequestAdmin(SimpleHistoryAdmin):
    list_display = ('vehicle_type', 'request_type', 'status', 'requested_by', 'created_at', 'reviewed_by')
    list_filter = ('request_type', 'status')
    search_fields = (
        'vehicle_type__type_name',
        'requested_by__username',
        'requested_by__first_name',
        'requested_by__last_name',
    )
    ordering = ('-created_at',)

class LiveryUserFilter(AutocompleteFilter):
    title = "User"
    field_name = "added_by"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("added_by__username")

@admin.register(liverie)
class LiveryAdmin(SimpleHistoryAdmin):
    search_fields = ['name']
    ordering = ['name']
    list_display = ['id', 'name', 'vehicle_count', 'left', 'right', 'BLOB', 'published', 'declined', 'aproved_by', 'added_by']
    list_filter = ['published', 'declined', LiveryUserFilter]
    list_editable = ['added_by']
    autocomplete_fields = ['added_by', 'aproved_by']

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
    
    def vehicle_count(self, obj):
        return obj.fleet_set.count()
    
    left.short_description = "Left Preview"
    right.short_description = "Right Preview"
    BLOB.short_description = "Colour"
    vehicle_count.short_description = "Vehicles Using"

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


class FleetOperatorGroupFilter(AutocompleteFilter):
    title = "Operator Group"
    field_name = "group"
    rel_model = MBTOperator
    parameter_name = "operator_group"

    def lookups(self, request, model_admin):
        return ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("group__group_name")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(operator__group_id=self.value())
        return queryset


class FleetOperatorOwnerFilter(AutocompleteFilter):
    title = "Owner"
    field_name = "owner"
    rel_model = MBTOperator
    parameter_name = "operator_owner"

    def lookups(self, request, model_admin):
        return ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by("owner__username")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(operator__owner_id=self.value())
        return queryset


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


@admin.action(description="Mark selected vehicles as In Service")
def mark_as_in_service(modeladmin, request, queryset):
    updated_count = queryset.update(in_service=True)
    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as in service.", messages.SUCCESS)


@admin.action(description="Mark selected vehicles as Not In Service")
def mark_as_not_in_service(modeladmin, request, queryset):
    updated_count = queryset.update(in_service=False)
    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as not in service.", messages.SUCCESS)


@admin.action(description="Mark selected vehicles as For Sale")
def mark_as_for_sale(modeladmin, request, queryset):
    in_service_qs = queryset.filter(in_service=True)
    updated_count = in_service_qs.update(for_sale=True)
    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as for sale.", messages.SUCCESS)


@admin.action(description="Mark selected vehicles as Not For Sale")
def ukmark_as_for_sale(modeladmin, request, queryset):
    updated = queryset.update(for_sale=False)
    modeladmin.message_user(request, f"{updated} vehicle(s) marked as not for sale.", messages.SUCCESS)

@admin.action(description="Mark selected vehicles as In Service")
def mark_as_in_service(modeladmin, request, queryset):
    in_service_qs = queryset.filter(in_service=True)
    updated_count = queryset.update(in_service=True)
    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as In Service.", messages.SUCCESS)

@admin.action(description="Mark selected vehicles as Not In Service")
def mark_as_not_in_service(modeladmin, request, queryset):    
    in_service_qs = queryset.filter(in_service=False)
    updated_count = queryset.update(in_service=False)
    modeladmin.message_user(request, f"{updated_count} vehicle(s) marked as Not In Service.", messages.SUCCESS)


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
    # Create a unique key for this transfer session
    key = get_random_string(12)
    # Store the selected IDs in the session
    request.session[f"transfer_ids_{key}"] = list(queryset.values_list("id", flat=True))
    # Redirect to the transfer page with just the key
    return redirect(f"/api-admin/fleet/fleet/transfer-vehicles/?key={key}")
    
# ---------------------------
# Fleet Admin
# ---------------------------

@admin.register(fleet)
class FleetAdmin(SimpleHistoryAdmin):
    search_fields = ["fleet_number", "reg", "operator__operator_name"]
    list_display = (
        "id",
        "fleet_number",
        "operator",
        "reg",
        "vehicleType",
        "livery",
        "in_service",
        "for_sale",
        "fleet_number_sort",
    )
    list_filter = (
        "for_sale",
        FleetOperatorOwnerFilter,
        FleetOperatorGroupFilter,
        FleetVehicleTypeFilter,
        FleetOperatorFilter,
        FleetLiveryFilter,
    )
    autocomplete_fields = ["operator", "loan_operator", "livery", "vehicleType", "last_modified_by", "current_trip", "vehicle_category"]
    actions = [
        deduplicate_fleet,
        mark_as_for_sale,
        ukmark_as_for_sale,
        sell_random_25,
        sell_random_100,
        transfer_vehicles,
        mark_as_in_service,
        mark_as_not_in_service,
    ]
    ordering = ("fleet_number_sort",)
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
        key = request.GET.get("key")
        ids = request.session.get(f"transfer_ids_{key}", [])

        # ✅ FIX: ids is already a list, no need to split
        queryset = self.model.objects.filter(pk__in=ids)

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

from django.contrib import admin
from django.db.models import Count
from simple_history.admin import SimpleHistoryAdmin
from .models import group, MBTOperator

# Filter for groups with zero operators
class ZeroOperatorFilter(admin.SimpleListFilter):
    title = 'Operators'
    parameter_name = 'zero_operators'

    def lookups(self, request, model_admin):
        return (
            ('0', 'No Operators'),
        )

    def queryset(self, request, queryset):
        if self.value() == '0':
            # Use the correct related_name
            return queryset.annotate(op_count=Count('mbtoperator')).filter(op_count=0)
        return queryset

@admin.action(description='Set selected groups to private')
def set_private(modeladmin, request, queryset):
    queryset.update(private=True)
    modeladmin.message_user(request, f"{queryset.count()} group(s) set to private.")

class groupAdmin(SimpleHistoryAdmin):
    list_display = ('group_name', 'group_owner', 'private', 'operator_count')
    search_fields = ['group_name', 'group_owner__username']
    list_filter = ('private', ZeroOperatorFilter)
    actions = [set_private]
    autocomplete_fields = ('group_owner',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate number of operators for sorting
        return qs.annotate(_operator_count=Count('mbtoperator'))

    def operator_count(self, obj):
        return obj._operator_count
    operator_count.admin_order_field = '_operator_count'  # makes it sortable
    operator_count.short_description = 'Number of Operators'

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

@admin.register(mapTileSet)
class MapTileSetAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'tile_url', 'attribution', 'tracking_trail_colour', 'is_default', 'pro_access', 'is_locked')
    list_filter = ('is_default', 'pro_access')
    search_fields = ('name', 'tile_url', 'attribution')
    autocomplete_fields = ('allowed_users',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not mapTileSet.pro_access_column_exists():
            queryset = queryset.defer('pro_access')
        return queryset

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        if not mapTileSet.pro_access_column_exists():
            list_display.remove('pro_access')
        return tuple(list_display)

    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        if not mapTileSet.pro_access_column_exists():
            list_filter.remove('pro_access')
        return tuple(list_filter)

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not mapTileSet.pro_access_column_exists():
            exclude.append('pro_access')
        if not mapTileSet.allowed_users_table_exists():
            exclude.append('allowed_users')
        return tuple(exclude)

    def is_locked(self, obj):
        if not mapTileSet.allowed_users_table_exists():
            return False
        return obj.allowed_users.exists()
    is_locked.boolean = True
    is_locked.short_description = 'Locked'

    def move_operators_to_fallback(self, request, deleted_tile_sets):
        deleted_ids = list(deleted_tile_sets.values_list('id', flat=True))
        if not deleted_ids:
            return

        fallback_tile_set = mapTileSet.objects.filter(is_default=True).exclude(id__in=deleted_ids).first()
        if fallback_tile_set is None:
            self.message_user(
                request,
                "Operators using deleted map tile sets were not moved because no remaining default map tile set exists.",
                level=messages.WARNING,
            )
            return

        updated = MBTOperator.objects.filter(mapTile_id__in=deleted_ids).update(mapTile=fallback_tile_set)
        if updated:
            self.message_user(
                request,
                f"{updated} operator(s) using deleted map tile sets were moved to the default map tile set.",
                level=messages.SUCCESS,
            )

    def delete_model(self, request, obj):
        with transaction.atomic():
            self.move_operators_to_fallback(request, mapTileSet.objects.filter(pk=obj.pk))
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            self.move_operators_to_fallback(request, queryset)
            super().delete_queryset(request, queryset)

admin.site.register(fleetChange, FleetChangeAdmin)
admin.site.register(group, groupAdmin)
admin.site.register(organisation, organisationAdmin)
admin.site.register(helper, HelperAdmin)
admin.site.register(helperPerm)
admin.site.register(companyUpdate)
admin.site.register(operatorType, operatorTypeAdmin)
admin.site.register(reservedOperatorName, reservedOperatorNameAdmin)
admin.site.register(ticket, TicketsAdmin)
