from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import TicketType, Ticket, TicketMessage, Notification, TicketSession
from django.utils.html import format_html
from django.urls import reverse

@admin.register(TicketType)
class TicketTypeAdmin(SimpleHistoryAdmin):
    list_display = ('type_name', 'team', 'active')
    list_filter = ('active', 'team')
    search_fields = ('type_name',)

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('sender', 'content', 'files', 'created_at', 'edited_at')
    autocomplete_fields = ('sender',)
    can_delete = False
    exclude = ('seen_by',)  # hides the field

@admin.register(Ticket)
class TicketAdmin(SimpleHistoryAdmin):
    list_display = (
        'id', 'view_ticket_link', 'ticket_type', 'user', 'assigned_team', 'assigned_agent', 
        'status', 'priority', 'created_at', 'updated_at'
    )
    list_filter = ('status', 'priority', 'assigned_team', 'assigned_agent', 'ticket_type')
    search_fields = ('id', 'user__username', 'assigned_agent__username')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('user', 'assigned_agent', 'assigned_team', 'ticket_type')
    inlines = [TicketMessageInline]

    def view_ticket_link(self, obj):
        url = reverse('ticket_detail', args=[obj.id])  # use your URL name here
        return format_html('<a class="button" href="{}" target="_blank">View</a>', url)

    view_ticket_link.short_description = 'View Ticket'
    view_ticket_link.allow_tags = True


@admin.register(TicketMessage)
class TicketMessageAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'ticket', 'sender', 'short_content', 'created_at', 'edited_at')
    list_filter = ('created_at', 'edited_at', 'sender')
    search_fields = ('ticket__id', 'sender__username', 'content')
    readonly_fields = ('created_at', 'edited_at')

    def short_content(self, obj):
        return (obj.content[:50] + '...') if obj.content and len(obj.content) > 50 else obj.content
    short_content.short_description = "Content"


@admin.register(Notification)
class NotificationAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'user', 'short_message', 'url', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)

    def short_message(self, obj):
        return (obj.message[:50] + '...') if len(obj.message) > 50 else obj.message
    short_message.short_description = "Message"


@admin.register(TicketSession)
class TicketSessionAdmin(SimpleHistoryAdmin):
    list_display = ('ticket', 'active_users_list')
    filter_horizontal = ('active_users',)

    def active_users_list(self, obj):
        return ", ".join([u.username for u in obj.active_users.all()])
    active_users_list.short_description = "Active Users"
