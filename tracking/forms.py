import json
from routes.models import timetableEntry, route
from fleet.models import fleet
from .models import Tracking
from django import forms
from datetime import datetime, date

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
            self.fields['tracking_vehicle'].queryset = fleet.objects.filter(operator=operator)
            self.fields['tracking_route'].queryset = route.objects.filter(route_operators=operator)

        route_id = self.data.get('tracking_route') or (self.initial.get('tracking_route') and self.initial['tracking_route'].id)
        if route_id:
            self.fields['timetable'].queryset = timetableEntry.objects.filter(route_id=route_id)

        timetable_id = self.data.get('timetable') or (self.initial.get('timetable') and self.initial['timetable'].id)
        if timetable_id:
            try:
                tt = timetableEntry.objects.get(id=timetable_id)
                stop_times = json.loads(tt.stop_times) 
                stop_order = list(stop_times.keys())
                start_stop = stop_order[0]
                end_stop = stop_order[-1]
                trip_times = stop_times[start_stop]["times"]
                self.fields['start_time_choice'].choices = [
                    (t, f"{t} — {start_stop} ➝ {end_stop}") for t in trip_times
                ]
            except timetableEntry.DoesNotExist:
                self.fields['start_time_choice'].choices = []

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