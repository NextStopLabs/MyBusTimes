from django import template
import markdown
import bleach
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({'h1', 'h2', 'h3', 'p', 'br', 'hr', 'code', 'small'})
ALLOWED_ATTRIBUTES = {'a': ['href', 'title'], 'img': ['src', 'alt']}

@register.filter
def markdownify(text):
    html = markdown.markdown(text, extensions=['extra'])
    clean_html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    return mark_safe(clean_html)
