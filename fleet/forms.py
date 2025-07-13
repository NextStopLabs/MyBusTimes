from django import forms
from datetime import datetime, date
from tracking.models import Trip
from routes.models import timetableEntry, route, serviceUpdate
from fleet.models import fleet, helper, helperPerm, ticket # or whatever your Vehicle model is
from django.forms.widgets import SelectDateWidget
from django_select2.forms import ModelSelect2Widget
from django.contrib.auth.models import User

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

class OperatorHelperForm(forms.ModelForm):
    class Meta:
        model = helper
        fields = ['helper', 'perms']
        widgets = {
            'helper': ModelSelect2Widget(
                model=User,
                search_fields=['username__icontains', 'first_name__icontains', 'last_name__icontains']
            ),
            'perms': forms.CheckboxSelectMultiple,
        }
        labels = {
            'helper': 'User',
            'perms': 'Permissions',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['perms'].queryset = helperPerm.objects.all().order_by('perms_level')
        self.fields['helper'].required = True
        self.fields['helper'].widget.attrs.update({'class': 'select2'})

class TicketForm(forms.ModelForm):
    class Meta:
        model = ticket
        fields = [
            'ticket_name',
            'ticket_price',
            'ticket_details',
            'zone',
            'valid_for_days',
            'single_use',
            'name_on_ticketer',
            'colour_on_ticketer',
            'ticket_category',
            'hidden_on_ticketer'
        ]
        widgets = {
            'ticket_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Day Saver'}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ticket_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'zone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Zone 1'}),
            'valid_for_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'single_use': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'name_on_ticketer': forms.TextInput(attrs={'class': 'form-control'}),
            'colour_on_ticketer': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'ticket_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Adult'}),
            'hidden_on_ticketer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ServiceUpdateForm(forms.ModelForm):
    effected_route = forms.ModelMultipleChoiceField(
        queryset=route.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'})
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    update_title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    update_description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        operator = kwargs.pop('operator', None)
        super().__init__(*args, **kwargs)
        if operator:
            self.fields['effected_route'].queryset = route.objects.filter(route_operators=operator)

    class Meta:
        model = serviceUpdate
        fields = ['effected_route', 'start_date', 'end_date', 'update_title', 'update_description']
