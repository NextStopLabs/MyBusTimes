from django import template
register = template.Library()

@register.filter
def index(List, i):
    try:
        return List[i]
    except:
        return ''

@register.filter
def dashify(value):
    return value.replace(' ', '-')