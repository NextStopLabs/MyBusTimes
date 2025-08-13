from django.contrib import admin
from .models import Thread, Post, Forum

# Inline posts inside threads for easy editing
class PostInline(admin.TabularInline):
    model = Post
    extra = 1
    readonly_fields = ('created_at',)
    fields = ('author', 'content', 'image', 'created_at')

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'forum', 'created_by', 'created_at', 'locked', 'admin_only', 'pinned', 'message_limit')
    list_filter = ('forum', 'locked', 'admin_only', 'pinned')
    search_fields = ('title', 'created_by', 'discord_channel_id')
    ordering = ('-created_at',)
    inlines = [PostInline]

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'thread', 'short_content', 'created_at')
    list_filter = ('thread__forum',)
    search_fields = ('author', 'content')
    ordering = ('-created_at',)

    def short_content(self, obj):
        return obj.content[:50]
    short_content.short_description = 'Content'

@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ('name', 'discord_forum_id', 'order')
    search_fields = ('name', 'discord_forum_id')
    ordering = ('order',)
