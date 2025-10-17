# myapp/templatetags/url_filters.py
import urllib.parse
from django import template

register = template.Library()

@register.filter
def urlquote(value):
    return urllib.parse.quote(value, safe='')
