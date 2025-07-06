from django import template

register = template.Library()

@register.filter
def get_css_color(changes, direction):
    for change in changes:
        if change.get('field') == 'livery_css':
            return change.get(direction)
    return ''

@register.filter
def replace(value, args):
    old, new = args.split(',')
    return value.replace(old, new)