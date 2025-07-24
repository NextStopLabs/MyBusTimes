import json
import ast
from django import template

register = template.Library()

@register.filter
def json_to_text(value):
    # Handle already a list
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)

    # Try json.loads (valid JSON string)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return ', '.join(str(v) for v in parsed)
        except Exception:
            pass
        
        # Try ast.literal_eval (string representation of Python list)
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return ', '.join(str(v) for v in parsed)
        except Exception:
            pass

    # Default fallback
    return value


@register.filter
def index(List, i):
    try:
        return List[i]
    except:
        return ''

@register.filter
def dashify(value):
    return value.replace(' ', '-')

@register.filter
def get_css(change_data, key):
    if isinstance(change_data, dict):
        return change_data.get(key, '')
    return ''

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces and title-case it."""
    return value.replace("_", " ").title()

