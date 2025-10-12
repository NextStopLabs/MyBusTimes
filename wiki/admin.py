from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Category, Tag, WikiPage, WikiPageVersion

@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(SimpleHistoryAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(WikiPage)
class WikiPageAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'author', 'category', 'is_draft', 'is_approved', 'created_at', 'updated_at')
    list_filter = ('is_draft', 'is_approved', 'category', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(WikiPageVersion)
class WikiPageVersionAdmin(SimpleHistoryAdmin):
    list_display = ('page', 'edited_by', 'created_at', 'edit_summary')
    list_filter = ('created_at', 'edited_by')
    search_fields = ('page__title', 'edit_summary', 'content')
    readonly_fields = ('created_at',)
