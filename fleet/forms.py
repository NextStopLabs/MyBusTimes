from django import forms
from datetime import datetime, date
from tracking.models import Trip
from routes.models import timetableEntry, route
from fleet.models import fleet  # or whatever your Vehicle model is

class TripFromTimetableForm(forms.ModelForm):
    trip_route = forms.ModelChoiceField(
        queryset=route.objects.none(), required=True, label="Trip Route"
    )
    trip_vehicle = forms.ModelChoiceField(
        queryset=fleet.objects.none(), required=True, label="Vehicle"
    )
    timetable = forms.ModelChoiceField(
        queryset=timetableEntry.objects.none(), required=True, label="Timetable Entry"
    )
    start_time_choice = forms.ChoiceField(
        required=True, label="Select Trip Time"
    )

    class Meta:
        model = Trip
        fields = ['trip_vehicle', 'trip_route', 'timetable', 'start_time_choice']

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)

        if self.operator:
            self.fields['trip_route'].queryset = route.objects.filter(route_operators=self.operator)
            self.fields['trip_vehicle'].queryset = fleet.objects.filter(operator=self.operator)

        if self.vehicle:
            self.initial['trip_vehicle'] = self.vehicle

        route_id = self.data.get('trip_route') or (self.instance.trip_route.id if self.instance.pk else None)
        if route_id:
            self.fields['timetable'].queryset = timetableEntry.objects.filter(route_id=route_id)

        timetable_id = self.data.get('timetable') or (self.instance.timetable.id if self.instance.pk else None)
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
            except timetableEntry.DoesNotExist:
                self.fields['start_time_choice'].choices = []

    def save(self, commit=True):
        instance = super().save(commit=False)
        cleaned_data = self.cleaned_data

        instance.trip_start_location = cleaned_data.get('trip_start_location')
        instance.trip_end_location = cleaned_data.get('trip_end_location')
        instance.trip_start_at = cleaned_data.get('trip_start_at')
        instance.trip_end_at = cleaned_data.get('trip_end_at')

        if commit:
            instance.save()
        return instance


    def clean(self):
        cleaned_data = super().clean()
        timetable = cleaned_data.get('timetable')
        start_time = cleaned_data.get('start_time_choice')

        if timetable and start_time:
            stop_order = list(timetable.stop_times.keys())
            start_stop = stop_order[0]
            end_stop = stop_order[-1]
            try:
                index = timetable.stop_times[start_stop]["times"].index(start_time)
                end_time = timetable.stop_times[end_stop]["times"][index]
            except (KeyError, ValueError, IndexError):
                raise forms.ValidationError("Invalid time selected.")

            today = date.today()
            cleaned_data['trip_start_location'] = start_stop
            cleaned_data['trip_end_location'] = end_stop
            cleaned_data['trip_start_at'] = datetime.strptime(f"{today} {start_time}", "%Y-%m-%d %H:%M")
            cleaned_data['trip_end_at'] = datetime.strptime(f"{today} {end_time}", "%Y-%m-%d %H:%M")

        return cleaned_data

class ManualTripForm(forms.ModelForm):
    trip_vehicle = forms.ModelChoiceField(
        queryset=fleet.objects.none(), required=True, label="Vehicle"
    )

    class Meta:
        model = Trip
        fields = [
            'trip_vehicle', 'trip_route_num',
            'trip_start_location', 'trip_end_location',
            'trip_start_at', 'trip_end_at'
        ]
        widgets = {
            'trip_start_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
            'trip_end_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        self.vehicle = kwargs.pop('vehicle', None)

        super().__init__(*args, **kwargs)
        if self.operator:
            self.fields['trip_vehicle'].queryset = fleet.objects.filter(operator=self.operator)

        if self.vehicle:
            self.initial['trip_vehicle'] = self.vehicle

    def __init__(self, *args, **kwargs):
        self.operator = kwargs.pop('operator', None)
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)

        if self.operator:
            self.fields['trip_vehicle'].queryset = fleet.objects.filter(operator=self.operator)

        if self.vehicle:
            self.initial['trip_vehicle'] = self.vehicle

