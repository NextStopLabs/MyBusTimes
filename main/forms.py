from django import forms
from .models import Report
from gameData.models import game

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['report_type', 'details', 'context', 'screenshot']

class GameForm(forms.ModelForm):
    class Meta:
        model = game
        fields = ['game_name']