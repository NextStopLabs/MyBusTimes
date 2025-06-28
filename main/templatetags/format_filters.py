from django import template

register = template.Library()

@register.filter
def format_feature_name(value):
    return value.replace('_', ' ').title()
