from django.contrib import admin
from .models import Chat, ChatMember, Message, ReadReceipt, TypingStatus


class ChatMemberInline(admin.TabularInline):
    model = ChatMember
    extra = 1


class MessageInline(admin.TabularInline):
    model = Message
    extra = 1
    fields = ("sender", "text", "image", "file", "created_at", "is_deleted")
    readonly_fields = ("created_at",)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_type", "name", "created_by", "created_at")
    list_filter = ("chat_type", "created_at")
    search_fields = ("name", "description")
    inlines = [ChatMemberInline, MessageInline]


@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "user", "joined_at", "last_seen_at", "is_admin")
    list_filter = ("is_admin", "joined_at")
    search_fields = ("user__username", "chat__name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "sender", "short_text", "created_at", "edited_at", "is_deleted")
    list_filter = ("is_deleted", "created_at", "edited_at")
    search_fields = ("text", "sender__username", "chat__name")

    def short_text(self, obj):
        return (obj.text[:50] + "...") if obj.text and len(obj.text) > 50 else obj.text
    short_text.short_description = "Message Text"


@admin.register(ReadReceipt)
class ReadReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "user", "read_at")
    list_filter = ("read_at",)
    search_fields = ("message__text", "user__username")


@admin.register(TypingStatus)
class TypingStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "chat", "user", "is_typing", "updated_at")
    list_filter = ("is_typing", "updated_at")
    search_fields = ("chat__name", "user__username")
