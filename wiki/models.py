from django.db import models
from django.conf import settings
from django.utils.text import slugify
from markdownx.models import MarkdownxField

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name

class WikiPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    content = MarkdownxField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_draft = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(WikiPage, self).save(*args, **kwargs)

    def has_pending_version(self):
        return self.versions.filter(page=self, created_at__gt=self.updated_at).exists()

    def latest_version(self):
        return self.versions.order_by('-created_at').first()

    def __str__(self):
        return self.title

class WikiPageVersion(models.Model):
    page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name='versions')
    content = models.TextField()
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    edit_summary = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Version of '{self.page.title}' on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
