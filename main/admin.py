from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin
from .models import *

@admin.register(region)
class RegionAdmin(SimpleHistoryAdmin):
    list_display = ('region_name', 'region_code', 'region_country', 'in_the')
    search_fields = ('region_name', 'region_code', 'region_country')
    list_filter = ('region_country', 'in_the')

@admin.register(badge)
class BadgeAdmin(SimpleHistoryAdmin):
    list_display = ('badge_name', 'badge_backgroud', 'badge_text_color', 'self_asign')
    search_fields = ('badge_name',)

@admin.register(MBTTeam)
class MBTTeamAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'get_permissions')
    search_fields = ('name',)

    def get_permissions(self, obj):
        return ", ".join(p.name for p in obj.permissions.all())
    get_permissions.short_description = "Permissions"

@admin.register(MBTAdminPermission)
class MBTAdminPermissionAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(theme)
class ThemeAdmin(SimpleHistoryAdmin):
    list_display = ('theme_name', 'dark_theme', 'main_colour', 'weight')
    search_fields = ('theme_name',)
    list_filter = ('dark_theme',)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'discord_username', 'join_date', 'banned', 'ad_free_until', 'last_active')
    list_filter = ('banned', 'is_staff', 'is_superuser', 'ad_free_until', 'theme', 'last_active')
    search_fields = ('username', 'email')
    filter_horizontal = ('badges', 'groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'email', 'discord_username', 'pfp', 'ad_free_until', 'first_name', 'last_name'
            )
        }),
        ('Ban Info', {
            'fields': (
                'banned',
                'forum_banned',
                'wiki_edit_banned', 
                'messaging_banned', 
                'ticket_banned', 
                'banned_reason', 
                'banned_date',
                'last_login_ip',
                'last_ip'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions', 'mbt_team'
            )
        }),
        ('Important dates', {'fields': ('last_login', 'last_active')}),
        ('Custom Fields', {
            'fields': (
                'theme', 'ticketer_code', 'static_ticketer_code',
                'reg_background', 'badges'
            )
        }),
        ('Admin Notes', {'fields': ('admin_notes',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

@admin.register(ad)
class AdAdmin(SimpleHistoryAdmin):
    list_display = ('ad_name', 'ad_img', 'ad_link', 'ad_live')
    search_fields = ('ad_name', 'ad_link')
    list_filter = ('ad_live',)

@admin.register(google_ad)
class GoogleAdAdmin(SimpleHistoryAdmin):
    list_display = ('ad_type', 'ad_id', 'ad_place_id')
    search_fields = ('ad_id', 'ad_place_id')
    list_filter = ('ad_type',)

@admin.register(Report)
class ReportAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'reporter', 'report_type', 'created_at')
    search_fields = ('details', 'context')

@admin.register(featureToggle)
class FeatureToggleAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'enabled', 'maintenance', 'coming_soon', 'coming_soon_percent')
    list_editable = ('enabled', 'maintenance', 'coming_soon', 'coming_soon_percent')
    search_fields = ('name',)
    list_filter = ('enabled', 'maintenance', 'coming_soon')
    ordering = ('name',)

@admin.register(siteUpdate)
class ServiceUpdateAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'title', 'live', 'created_at', 'updated_at')
    list_editable = ('live',)
    search_fields = ('title', 'description')
    list_filter = ('live',)
    ordering = ('-created_at',)

@admin.register(patchNote)
class PatchNoteAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'title', 'live', 'created_at', 'updated_at')
    list_editable = ('live',)
    search_fields = ('title', 'description')
    list_filter = ('live',)
    ordering = ('-created_at',)

@admin.register(BannedIps)
class BannedIpsAdmin(SimpleHistoryAdmin):
    list_display = ('ip_address', 'reason', 'banned_at', 'related_user')
    search_fields = ('ip_address', 'reason')
    list_filter = ('banned_at',)
    raw_id_fields = ('related_user',)

@admin.register(ImportJob)
class ImportJobAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'user', 'message', 'progress', 'status', 'created_at', 'updated_at')
    search_fields = ('status',)
    list_filter = ('status',)
    ordering = ('-created_at',)
    raw_id_fields = ('user',)

@admin.register(UserKeys)
class UserKeysAdmin(SimpleHistoryAdmin):
    list_display = ('user', 'session_key', 'created_at')
    search_fields = ('user__username', 'session_key')
    list_filter = ('created_at',)

@admin.register(CommunityImages)
class CommunityImagesAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'uploaded_by', 'created_at')
    search_fields = ('uploaded_by__username',)
    list_filter = ('created_at',)
    autocomplete_fields = ('uploaded_by',)