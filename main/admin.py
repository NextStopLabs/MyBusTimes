from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.models import LogEntry
from .models import *


@admin.register(DeviceBan)
class DeviceBanAdmin(SimpleHistoryAdmin):
    list_display = ('fingerprint', 'banned_at', 'reason', 'related_user')
    search_fields = ('fingerprint', 'reason')
    list_filter = ('banned_at',)
    raw_id_fields = ('related_user',)

@admin.register(Device)
class DeviceAdmin(SimpleHistoryAdmin):
    list_display = ('fingerprint', 'last_seen', 'last_user', 'last_ip')
    search_fields = ('fingerprint', 'last_ip', 'last_user__username')
    list_filter = ('last_seen',)
    raw_id_fields = ('last_user',)

@admin.register(DeviceUsage)
class DeviceUsageAdmin(SimpleHistoryAdmin):
    list_display = ('device', 'user', 'last_seen', 'usage_count')
    search_fields = ('device__fingerprint', 'user__username')
    list_filter = ('last_seen',)
    raw_id_fields = ('device', 'user')

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message']
    list_filter = ['action_flag', 'content_type', 'user']
    search_fields = ['object_repr', 'change_message']

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
    list_display = ('theme_name', 'public', 'light_main_colour', 'dark_main_colour', 'weight')
    search_fields = ('theme_name',)
    list_filter = ('public',)

@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(SimpleHistoryAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)
    autocomplete_fields = ('user',)    

@admin.register(ActiveSubscription)
class ActiveSubscriptionAdmin(SimpleHistoryAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_trial', 'stripe_subscription_id')
    search_fields = ('user__username', 'stripe_subscription_id', 'plan')
    list_filter = ('plan', 'is_trial', 'start_date', 'end_date')
    autocomplete_fields = ('user',)
    ordering = ('-start_date',)

@admin.register(BanType)
class BanTypeAdmin(SimpleHistoryAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(CustomUser)
class CustomUserAdmin(SimpleHistoryAdmin, UserAdmin):
    list_display = ('username', 'email', 'discord_username', 'join_date', 'banned', 'sub_plan', 'ad_free_until', 'last_active')
    list_filter = ('banned', 'is_staff', 'is_superuser', 'ad_free_until', 'theme', 'last_active')
    search_fields = ('username', 'email', 'last_ip', 'last_login_ip', 'discord_username')
    filter_horizontal = ('badges', 'groups', 'user_permissions', 'banned_from')
    list_editable = ('sub_plan',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'email', 'discord_username', 'pfp', 'had_pro_trial', 'first_name', 'last_name'
            )
        }),
        ('Ban Info', {
            'fields': (
                'banned',
                'banned_from',
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

@admin.register(SuspiciousSignupAlert)
class SuspiciousSignupAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'created_at', 'webhook_sent_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'webhook_sent_at')
    raw_id_fields = ('user',)

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