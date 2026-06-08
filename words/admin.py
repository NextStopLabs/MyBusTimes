from django.contrib import admin
from django import forms
from .models import bannedWord, whitelistedWord
from simple_history.admin import SimpleHistoryAdmin
    
# Register your models here.

class BannedWordAdminForm(forms.ModelForm):
    ban_all = forms.BooleanField(
        label='Select all ban types',
        required=False,
        help_text='Tick to enable this word for search, operator names, group names, and usernames.',
    )

    class Meta:
        model = bannedWord
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        scope_fields = bannedWord.SCOPE_FIELD_MAP.values()
        self.fields['ban_all'].initial = all(
            self.initial.get(field, self.instance.pk is None) for field in scope_fields
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.cleaned_data.get('ban_all'):
            for field in bannedWord.SCOPE_FIELD_MAP.values():
                setattr(instance, field, True)
        if commit:
            instance.save()
            self.save_m2m()
        return instance

@admin.register(bannedWord)
class BannedWordAdmin(SimpleHistoryAdmin):
    form = BannedWordAdminForm
    list_display = (
        'word',
        'insta_ban',
        'ban_search',
        'ban_operator_name',
        'ban_group_name',
        'ban_username',
    )
    list_filter = (
        'insta_ban',
        'ban_search',
        'ban_operator_name',
        'ban_group_name',
        'ban_username',
    )
    fieldsets = (
        (None, {
            'fields': ('word', 'insta_ban'),
        }),
        ('Ban types', {
            'fields': (
                'ban_all',
                'ban_search',
                'ban_operator_name',
                'ban_group_name',
                'ban_username',
            ),
        }),
    )

    class Media:
        js = ('words/admin_bannedword.js',)

@admin.register(whitelistedWord)
class WhitelistedWordAdmin(SimpleHistoryAdmin):
    list_display = ('word',)
