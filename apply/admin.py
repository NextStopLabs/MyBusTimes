from django.contrib import admin
from .models import Position, Application


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "available_places", "created_at", "updated_at")
    search_fields = ("name",)
    ordering = ("name",)
    list_filter = ("created_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "position", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at", "updated_at", "position")
    search_fields = ("applicant__username", "position__name", "details")
    ordering = ("-created_at",)
    autocomplete_fields = ("applicant", "position", "chat")
    readonly_fields = ("created_at", "updated_at")
