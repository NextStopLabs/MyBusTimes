from django import forms
import json
from datetime import datetime, date
from tracking.models import Trip
from routes.models import timetableEntry, route, serviceUpdate
from fleet.models import fleet, helper, helperPerm, ticket # or whatever your Vehicle model is
from django.forms.widgets import SelectDateWidget
from django_select2.forms import ModelSelect2Widget
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import MBTOperator
from django.contrib import admin
import requests
from django.conf import settings

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
        self.debug_info = {"init": {}, "clean": {}}
        print("🧩 [INIT] TripFromTimetableForm initializing...")
        self.operator = kwargs.pop('operator', None)
        self.vehicle = kwargs.pop('vehicle', None)
        super().__init__(*args, **kwargs)

        self.debug_info["init"]["operator"] = str(self.operator)
        self.debug_info["init"]["vehicle"] = str(self.vehicle)
        self.debug_info["init"]["data"] = dict(self.data)
        self.debug_info["init"]["instance"] = str(self.instance)

        if self.operator:
            self.fields['trip_route'].queryset = route.objects.filter(route_operators=self.operator)
            self.fields['trip_vehicle'].queryset = fleet.objects.filter(operator=self.operator)
            self.debug_info["init"]["route_count"] = self.fields['trip_route'].queryset.count()
            self.debug_info["init"]["vehicle_count"] = self.fields['trip_vehicle'].queryset.count()

        if self.vehicle:
            self.initial['trip_vehicle'] = self.vehicle

        route_id = self.data.get('trip_route') or (self.instance.trip_route.id if self.instance.pk else None)
        self.debug_info["init"]["route_id"] = route_id
        if route_id:
            self.fields['timetable'].queryset = timetableEntry.objects.filter(route_id=route_id)
            self.debug_info["init"]["timetable_count"] = self.fields['timetable'].queryset.count()

        timetable_id = self.data.get('timetable') or (self.instance.timetable.id if self.instance.pk else None)
        self.debug_info["init"]["timetable_id"] = timetable_id
        
        if timetable_id:
            try:
                # --- Determine API URL dynamically ---
                if self.request:
                    api_url = self.request.build_absolute_uri(f"/api/get_trip_times/?timetable_id={timetable_id}")
                else:
                    base_url = getattr(settings, "BASE_URL", "")
                    if not base_url:
                        raise ValueError("BASE_URL not defined and no request available.")
                    api_url = f"{base_url.rstrip('/')}/api/get_trip_times/?timetable_id={timetable_id}"

                # --- Fetch data from API ---
                response = requests.get(api_url, timeout=5)
                response.raise_for_status()
                data = response.json()

                # --- Parse API data ---
                times_data = data.get("times", {})
                start_stop = data.get("start_stop", "Unknown Start")
                end_stop = data.get("end_stop", "Unknown End")

                choices = [
                    (t, info.get("label", f"{t} — {start_stop} ➝ {end_stop}"))
                    for t, info in times_data.items()
                ]
                self.fields["start_time_choice"].choices = choices

                # --- Debug info ---
                self.debug_info["init"].update({
                    "source": "API",
                    "api_url": api_url,
                    "trip_times": list(times_data.keys()),
                    "start_stop": start_stop,
                    "end_stop": end_stop,
                    "choice_count": len(choices)
                })

            except Exception as e:
                err = f"Error loading timetable details from API: {type(e).__name__} - {e}"
                print("❌", err)
                self.debug_info["init"]["error"] = err
                self.fields["start_time_choice"].choices = []
                self.add_error("timetable", err)

    def clean(self):
        cleaned_data = super().clean()
        timetable = cleaned_data.get('timetable')
        start_time = cleaned_data.get('start_time_choice')

        self.debug_info["clean"]["timetable"] = str(timetable)
        self.debug_info["clean"]["start_time"] = str(start_time)

        if timetable and start_time:
            try:
                stop_times = timetable.stop_times
                if isinstance(stop_times, str):
                    stop_times = json.loads(stop_times)
                    self.debug_info["clean"]["stop_times_json"] = True
                else:
                    self.debug_info["clean"]["stop_times_json"] = False

                self.debug_info["clean"]["stop_times_keys"] = list(stop_times.keys())
                stopname_map = {v['stopname']: k for k, v in stop_times.items()}
                stop_order = list(stopname_map.keys())
                start_stop = stop_order[0]
                end_stop = stop_order[-1]
                index = stop_times[stopname_map[start_stop]]["times"].index(start_time)

                self.debug_info["clean"]["start_stop"] = start_stop
                self.debug_info["clean"]["end_stop"] = end_stop
                self.debug_info["clean"]["start_index"] = index

                end_times = stop_times[stopname_map[end_stop]].get("times", [])
                end_time = end_times[index] if index < len(end_times) else None
                self.debug_info["clean"]["end_time"] = end_time

                today = date.today()
                cleaned_data['trip_start_location'] = start_stop
                cleaned_data['trip_end_location'] = end_stop
                cleaned_data['trip_start_at'] = timezone.make_aware(
                    datetime.strptime(f"{today} {start_time}", "%Y-%m-%d %H:%M")
                )

                if end_time:
                    try:
                        cleaned_data['trip_end_at'] = timezone.make_aware(
                            datetime.strptime(f"{today} {end_time}", "%Y-%m-%d %H:%M")
                        )
                    except ValueError:
                        msg = f"End time '{end_time}' could not be parsed — skipped."
                        self.add_error('timetable', msg)
                        self.debug_info["clean"]["end_time_error"] = msg

            except Exception as e:
                err_msg = f"Error processing timetable data: {type(e).__name__} - {e}"
                self.debug_info["clean"]["error"] = err_msg
                raise forms.ValidationError({
                    'timetable': err_msg,
                    '__all__': f"Debug info: {json.dumps(self.debug_info, indent=2)}"
                })

        # If we get a validation error like “Select a valid choice”, show debug info
        if self.errors:
            self.errors['__all__'] = self.errors.get('__all__', []) + [
                f"⚙️ Debug info:\n{json.dumps(self.debug_info, indent=2)}"
            ]

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        cleaned_data = self.cleaned_data

        instance.trip_start_at = cleaned_data.get('trip_start_at')
        instance.trip_end_at = cleaned_data.get('trip_end_at')
        instance.trip_start_location = cleaned_data.get('trip_start_location')
        instance.trip_end_location = cleaned_data.get('trip_end_location')

        if commit:
            instance.save()
        return instance



class ManualTripForm(forms.ModelForm):
    trip_vehicle = forms.ModelChoiceField(
        queryset=fleet.objects.none(), required=True, label="Vehicle"
    )

    trip_route = forms.ModelChoiceField(
        queryset=route.objects.none(), required=False, label="Trip Route"
    )

    class Meta:
        model = Trip
        fields = [
            'trip_vehicle', 'trip_route', 'trip_route_num',
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
        self.route = kwargs.pop('route', None)

        super().__init__(*args, **kwargs)
        if self.operator:
            self.fields['trip_vehicle'].queryset = fleet.objects.filter(operator=self.operator)
            self.fields['trip_route'].queryset = route.objects.filter(route_operators=self.operator)

        if self.vehicle:
            self.initial['trip_vehicle'] = self.vehicle

class LevelCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        # Unwrap ModelChoiceIteratorValue if needed
        real_value = value.value if hasattr(value, 'value') else value

        try:
            perm_obj = helperPerm.objects.get(pk=real_value)
            option['attrs']['data-level'] = perm_obj.perms_level
        except helperPerm.DoesNotExist:
            option['attrs']['data-level'] = 0

        return option
    
class OperatorHelperForm(forms.ModelForm):
    class Meta:
        model = helper
        fields = ['helper', 'perms']
        widgets = {
            'helper': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Search for user...',
            }),
            'perms': LevelCheckboxSelectMultiple,  # use our custom widget
        }
        labels = {
            'helper': 'User',
            'perms': 'Permissions',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['perms'].queryset = helperPerm.objects.all().order_by('perms_level')
        self.fields['helper'].required = True

        if self.instance and self.instance.pk:
            user = self.instance.helper
            self.fields['helper'].choices = [(user.id, user.username)]
        else:
            self.fields['helper'].choices = []

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