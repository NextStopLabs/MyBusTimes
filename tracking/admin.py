from django.contrib import admin
from .models import *
from django.utils.html import format_html
from django.contrib import messages
from django import forms
from datetime import datetime, date
from routes.models import timetableEntry

class TrackingAdmin(admin.ModelAdmin):
    list_display = ('tracking_id', 'tracking_vehicle', 'tracking_route', 'trip_ended', 'tracking_start_at', 'tracking_end_at')
    search_fields = ('tracking_id', 'tracking_vehicle', 'tracking_route')
    list_filter = ('tracking_vehicle', 'tracking_route')
    actions = ['end_trip', 'unend_trip']
    list_per_page = 25

    @admin.action(description='End selected trips')
    def end_trip(self, request, queryset):
        updated = queryset.update(trip_ended=True)
        self.message_user(request, f"{updated} trip(s) marked as ended.", messages.SUCCESS)

    @admin.action(description='Un-end selected trips')
    def unend_trip(self, request, queryset):
        updated = queryset.update(trip_ended=False)
        self.message_user(request, f"{updated} trip(s) marked as not ended.", messages.SUCCESS)

class TripForm(forms.ModelForm):
    timetable = forms.ModelChoiceField(queryset=timetableEntry.objects.all(), required=False, label="Timetable Entry")
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
                self.fields['timetable'].queryset = timetableEntry.objects.filter(route_id=route_id)
            except (ValueError, TypeError):
                self.fields['timetable'].queryset = timetableEntry.objects.none()
        elif self.instance.pk and self.instance.trip_route:
            self.fields['timetable'].queryset = timetableEntry.objects.filter(route=self.instance.trip_route)

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

            today = date.today()
            cleaned_data['trip_start_location'] = start_stop
            cleaned_data['trip_end_location'] = end_stop
            cleaned_data['trip_start_at'] = datetime.strptime(f"{today} {start_time}", "%Y-%m-%d %H:%M")
            cleaned_data['trip_end_at'] = datetime.strptime(f"{today} {end_time}", "%Y-%m-%d %H:%M")

        return cleaned_data


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    form = TripForm
    list_display = ('trip_id', 'trip_vehicle', 'trip_route', 'trip_start_at', 'trip_end_at', 'trip_ended')
    search_fields = ('trip_id', 'trip_vehicle__fleet_number', 'trip_route__route_name')
    list_filter = ('trip_vehicle', 'trip_route')

    class Media:
        js = ('admin/js/jquery.init.js',  # Django's jQuery
              'js/trip_form.js',)         # Your custom JS

admin.site.register(Tracking, TrackingAdmin)