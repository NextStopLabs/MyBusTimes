import json
import re
from routes.models import timetableEntry, route
from fleet.models import fleet
from .models import Tracking
from django import forms
from datetime import datetime, date

def alphanum_key(fleet_number):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', fleet_number or '')]

class trackingForm(forms.ModelForm):
    tracking_route = forms.ModelChoiceField(queryset=route.objects.all(), required=False, label="Route")
    timetable = forms.ModelChoiceField(queryset=timetableEntry.objects.none(), required=False, label="Timetable Entry")
    start_time_choice = forms.ChoiceField(required=False, label="Select Trip Time")

    class Meta:
        model = Tracking
        fields = ['tracking_vehicle', 'tracking_route', 'timetable', 'start_time_choice',
                  'tracking_start_location', 'tracking_end_location',
                  'tracking_start_at', 'tracking_end_at', 'tracking_data']
        widgets = {
            'tracking_start_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'tracking_end_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'tracking_data': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)

        if operator:
            # Fetch and sort fleet by alphanumeric fleet_number
            fleet_list = list(fleet.objects.filter(operator=operator))
            fleet_list.sort(key=lambda f: alphanum_key(f.fleet_number))  # assuming 'fleet_number' is the field

            # Get the sorted list of IDs
            ordered_ids = [f.id for f in fleet_list]

            # Reassign queryset with preserved order using a Case/When expression
            from django.db.models import Case, When
            preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_ids)])

            self.fields['tracking_vehicle'].queryset = (
                fleet.objects.filter(pk__in=ordered_ids).order_by(preserved_order)
            )

            # Routes
            self.fields['tracking_route'].queryset = route.objects.filter(route_operators=operator).order_by('route_num')

    def clean(self):
        cleaned_data = super().clean()
        timetable = cleaned_data.get('timetable')
        start_time = cleaned_data.get('start_time_choice')

        if timetable and start_time:
            stop_times = json.loads(timetable.stop_times)  # 👈 Fix here
            stop_order = list(stop_times.keys())
            start_stop = stop_order[0]
            end_stop = stop_order[-1]
            try:
                index = stop_times[start_stop]["times"].index(start_time)
                end_time = stop_times[end_stop]["times"][index]
            except (KeyError, ValueError, IndexError):
                raise forms.ValidationError("Invalid time selected.")

            today = date.today()
            cleaned_data['tracking_start_location'] = start_stop
            cleaned_data['tracking_end_location'] = end_stop
            cleaned_data['tracking_start_at'] = datetime.strptime(f"{today} {start_time}", "%Y-%m-%d %H:%M")
            cleaned_data['tracking_end_at'] = datetime.strptime(f"{today} {end_time}", "%Y-%m-%d %H:%M")

        return cleaned_data


class updateTrackingForm(forms.ModelForm):
    class Meta:
        model = Tracking
        fields = ['tracking_data', 'tracking_history_data']