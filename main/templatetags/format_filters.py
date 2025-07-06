from django import template

register = template.Library()

@register.filter
def format_feature_name(value):
    formatted = value.replace('_', ' ').title()
    # Replace 'Mbt' with 'MBT' if present
    return formatted.replace('Mbt', 'MBT')
