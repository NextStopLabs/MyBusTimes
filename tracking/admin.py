from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from requests import request
from .models import *
from django.utils.html import format_html
from django.contrib import messages
from django import forms
from datetime import datetime, date
from routes.models import timetableEntry
from django.utils import timezone
from datetime import timedelta
from admin_auto_filters.filters import AutocompleteFilter

class TripForm(forms.ModelForm):
    timetable = forms.ModelChoiceField(
        queryset=timetableEntry.objects.none(),  # Lazy load only in __init__
        required=False,
        label="Timetable Entry"
    )
    start_time_choice = forms.ChoiceField(required=False, label="Select Trip Time")

    class Meta:
        model = Trip
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the timetable queryset based on selected trip_route
        if 'trip_route' in self.data:
            try:
                route_id = int(self.data.get('trip_route'))
                self.fields['timetable'].queryset = timetableEntry.objects.filter(route_id=route_id)[:500]  # limit size
            except (ValueError, TypeError):
                self.fields['timetable'].queryset = timetableEntry.objects.none()
        elif self.instance.pk and self.instance.trip_route:
            self.fields['timetable'].queryset = timetableEntry.objects.filter(route=self.instance.trip_route)[:500]

        # Determine timetable to build time choices
        timetable_id = None
        if 'timetable' in self.data:
            try:
                timetable_id = int(self.data.get('timetable'))
            except (ValueError, TypeError):
                pass
        elif hasattr(self.instance, 'timetable') and self.instance.timetable:
            timetable_id = self.instance.timetable.id

        # Build start time choices
        if timetable_id:
            try:
                tt = timetableEntry.objects.get(id=timetable_id)
                stop_order = list(tt.stop_times.keys())
                start_stop = stop_order[0]
                end_stop = stop_order[-1]
                trip_times = tt.stop_times[start_stop]["times"]

                self.fields['start_time_choice'].choices = [
                    (t, f"{t} — {start_stop} ➝ {end_stop}") for t in trip_times
                ]

                # Optional: auto-select value when editing existing trip
                if self.instance and self.instance.trip_start_at:
                    self.initial['start_time_choice'] = self.instance.trip_start_at.strftime('%H:%M')

            except timetableEntry.DoesNotExist:
                self.fields['start_time_choice'].choices = []


    def clean(self):
        cleaned_data = super().clean()
        timetable = cleaned_data.get('timetable')
        start_time = cleaned_data.get('start_time_choice')

        if timetable and start_time:
            stop_order = list(timetable.stop_times.keys())
            start_stop = stop_order[0]
            end_stop = stop_order[-1]

            try:
                end_time = timetable.stop_times[end_stop]["times"][timetable.stop_times[start_stop]["times"].index(start_time)]
            except (KeyError, ValueError, IndexError):
                raise forms.ValidationError("Invalid time selected.")

            # Use Django's timezone-aware local date to build datetimes
            today = timezone.localdate()
            cleaned_data['trip_start_location'] = start_stop
            cleaned_data['trip_end_location'] = end_stop
            dt_start = datetime.strptime(f"{today} {start_time}", "%Y-%m-%d %H:%M")
            dt_end = datetime.strptime(f"{today} {end_time}", "%Y-%m-%d %H:%M")
            # If the trip crosses midnight, ensure end is after start
            if dt_end <= dt_start:
                dt_end = dt_end + timedelta(days=1)
            # Convert to timezone-aware datetimes with DST resilience
            def _make_aware_dst(dt):
                try:
                    return timezone.make_aware(dt, timezone.get_current_timezone())
                except timezone.AmbiguousTimeError:
                    # Ambiguous (fold) — prefer the later fold
                    dt = dt.replace(fold=1)
                    return timezone.make_aware(dt, timezone.get_current_timezone())
                except timezone.NonExistentTimeError:
                    # Non-existent time (clock jumps forward) — nudge forward by 1 hour
                    dt = dt + timedelta(hours=1)
                    return timezone.make_aware(dt, timezone.get_current_timezone())

            dt_start = _make_aware_dst(dt_start)
            dt_end = _make_aware_dst(dt_end)
            cleaned_data['trip_start_at'] = dt_start
            cleaned_data['trip_end_at'] = dt_end

        return cleaned_data


class TripVehicleFilter(AutocompleteFilter):
    title = 'Vehicle'
    field_name = 'trip_vehicle'

class TripRouteFilter(AutocompleteFilter):
    title = 'Route'
    field_name = 'trip_route'

@admin.register(Trip)
class TripAdmin(SimpleHistoryAdmin):
    form = TripForm
    list_display = (
        'trip_id', 'trip_inbound', 'trip_start_at', 'trip_end_at', 'trip_ended', 'trip_route', 'trip_vehicle'
    )
    search_fields = (
        'trip_id',
        'trip_vehicle__fleet_number',
        'trip_route__route_name',
    )
    list_filter = (
        'trip_ended',
        TripVehicleFilter,
        TripRouteFilter,
    )
    autocomplete_fields = ['trip_vehicle', 'trip_route']
    date_hierarchy = 'trip_start_at'
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer()

    class Media:
        js = ('admin/js/jquery.init.js',  # Django's jQuery
              'js/trip_form.js',)         # Your custom JS


class TrackingVehicleFilter(AutocompleteFilter):
    title = 'Vehicle'
    field_name = 'tracking_vehicle'


class TrackingRouteFilter(AutocompleteFilter):
    title = 'Route'
    field_name = 'tracking_route'


@admin.register(Tracking)
class TrackingAdmin(SimpleHistoryAdmin):
    list_display = (
        'tracking_id',
        'tracking_start_at',
        'tracking_end_at',
        'trip_ended',
        'tracking_route',
        'tracking_vehicle',
    )
    search_fields = (
        'tracking_id',
        'tracking_vehicle__fleet_number',
        'tracking_route__route_name',  # make sure this matches your model field
    )
    list_filter = (
        'trip_ended',
        TrackingVehicleFilter,
        TrackingRouteFilter,
    )
    autocomplete_fields = ['tracking_vehicle', 'tracking_route', 'tracking_trip']
    date_hierarchy = 'tracking_start_at'
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.defer('tracking_data', 'tracking_history_data')

    @admin.action(description='End selected trips')
    def end_trip(self, request, queryset):
        updated = queryset.update(trip_ended=True)
        self.message_user(request, f"{updated} trip(s) marked as ended.", messages.SUCCESS)

    @admin.action(description='Un-end selected trips')
    def unend_trip(self, request, queryset):
        updated = queryset.update(trip_ended=False)
        self.message_user(request, f"{updated} trip(s) marked as not ended.", messages.SUCCESS)


@admin.register(TripArchive)
class TripArchiveAdmin(admin.ModelAdmin):
    list_display = (
        'original_trip_id', 'trip_vehicle', 'trip_route', 'trip_route_num',
        'trip_start_at', 'trip_end_at', 'trip_ended', 'trip_missed', 'archived_at',
    )
    search_fields = (
        'original_trip_id',
        'trip_vehicle__fleet_number',
        'trip_route__route_name',
        'trip_route_num',
    )
    list_filter = ('trip_ended', 'trip_missed', 'trip_inbound')
    date_hierarchy = 'trip_end_at'
    list_per_page = 50
    readonly_fields = [
        'original_trip_id', 'trip_display_id', 'trip_vehicle', 'trip_route',
        'trip_route_num', 'trip_driver', 'trip_start_location', 'trip_end_location',
        'trip_start_at', 'trip_end_at', 'trip_updated_at', 'trip_ended',
        'trip_missed', 'trip_inbound', 'trip_board', 'archived_at',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('trip_vehicle', 'trip_route', 'trip_driver', 'trip_board')