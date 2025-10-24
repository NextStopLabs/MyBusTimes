from django.contrib import admin
from .models import bannedWord, whitelistedWord
from simple_history.admin import SimpleHistoryAdmin
    
# Register your models here.
@admin.register(bannedWord)
class BannedWordAdmin(SimpleHistoryAdmin):
    list_display = ('word',)

@admin.register(whitelistedWord)
class WhitelistedWordAdmin(SimpleHistoryAdmin):
    list_display = ('word',)