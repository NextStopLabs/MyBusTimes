from django.contrib import admin
from .models import *

@admin.register(region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('region_name', 'region_code', 'region_country', 'in_the')
    search_fields = ('region_name', 'region_code', 'region_country')
    list_filter = ('region_country', 'in_the')

@admin.register(badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('badge_name', 'badge_backgroud', 'badge_text_color', 'self_asign')
    search_fields = ('badge_name',)

@admin.register(MBTAdminPermission)
class MBTAdminPermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('theme_name', 'dark_theme', 'main_colour', 'weight')
    search_fields = ('theme_name',)
    list_filter = ('dark_theme',)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'join_date', 'banned', 'ad_free_until')
    list_filter = ('banned', 'theme')
    search_fields = ('username', 'email', 'ticketer_code')
    filter_horizontal = ('mbt_admin_perms', 'badges')

@admin.register(ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('ad_name', 'ad_img', 'ad_link', 'ad_live')
    search_fields = ('ad_name', 'ad_link')
    list_filter = ('ad_live',)

@admin.register(google_ad)
class GoogleAdAdmin(admin.ModelAdmin):
    list_display = ('ad_type', 'ad_id', 'ad_place_id')
    search_fields = ('ad_id', 'ad_place_id')
    list_filter = ('ad_type',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'report_type', 'created_at')
    search_fields = ('details', 'context')

@admin.register(featureToggle)
class FeatureToggleAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'maintenance', 'coming_soon', 'coming_soon_percent')
    list_editable = ('enabled', 'maintenance', 'coming_soon', 'coming_soon_percent')
    search_fields = ('name',)
    list_filter = ('enabled', 'maintenance', 'coming_soon')
    ordering = ('name',)