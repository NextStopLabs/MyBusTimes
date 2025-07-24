from django import template
from django.utils.timezone import localtime, now

register = template.Library()

@register.filter
def smart_datetime(value):
    if not value:
        return ""
    value = localtime(value)  # convert to local time if timezone aware
    today = localtime(now()).date()
    if value.date() == today:
        # just time if today
        return value.strftime("%H:%M")
    else:
        # date + time otherwise
        return value.strftime("%Y-%m-%d %H:%M")
