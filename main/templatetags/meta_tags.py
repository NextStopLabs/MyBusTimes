import logging

from django import template
from django.template import Context, Template
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)
register = template.Library()


def render_with_context(context, text):
    """Render a text string with template context support."""
    return Template(text).render(Context(context))


def set_or_get(context, key, value=None, default=None):
    """
    Store or retrieve a value from the shared template context.
    Works across block inheritance.
    """
    # Try to find the shared storage dict if it already exists
    for d in context.dicts:
        if "meta_tags" in d:
            storage = d["meta_tags"]
            break
    else:
        # Not found — create it in the base layer
        storage = context.dicts[0].setdefault("meta_tags", {})

    if value is not None:
        storage[key] = value

    if default is None:
        if key == "meta_title":
            default = "MyBusTimes"
        elif key == "meta_url":
            default = "https://www.mybustimes.cc/"
        elif key == "meta_description":
            default = '''MyBusTimes is a fictional bus tracking and management platform where users 
            can create companies, manage fleets, and more.'''
        elif key == "meta_keywords":
            default = "bus, buses, coach, coaches, vehicle, vehicles, mybustimes, MBT, MyBusTimes, My Bus Times, fleet, fleet list"
        else:
            default = "MyBusTimes"

    return storage.get(key, default)


@register.simple_tag(takes_context=True)
def meta_description(context, text=None):
    default = '''MyBusTimes is a fictional bus tracking and management platform where users 
        can create companies, manage fleets, and more.'''

    if text:
        rendered = render_with_context(context, text)
        set_or_get(context, "meta_description", rendered)
        return rendered
    
    return set_or_get(context, "meta_description", default)


@register.simple_tag(takes_context=True)
def meta_keywords(context, text=None):
    base = "bus, buses, coach, coaches, vehicle, vehicles, mybustimes, MBT, MyBusTimes, My Bus Times, fleet, fleet list"
    if text:
        rendered = render_with_context(context, text)
        set_or_get(context, "meta_keywords", rendered)
        return rendered
    return set_or_get(context, "meta_keywords", base)


@register.simple_tag(takes_context=True)
def meta_title(context, text=None):
    default = "MyBusTimes"
    if text:
        rendered = render_with_context(context, text)
        set_or_get(context, "meta_title", rendered)
        return rendered
    return set_or_get(context, "meta_title", default)


@register.simple_tag(takes_context=True)
def meta_url(context, text=None):
    default = "https://www.mybustimes.cc/"
    if text:
        rendered = render_with_context(context, text)
        set_or_get(context, "meta_url", rendered)
        return rendered
    return set_or_get(context, "meta_url", default)


@register.simple_tag(takes_context=True)
def render_meta_tags(context):
    """Render full meta tag block."""
    try:
        storage = context.dicts[0].get("meta_tags", {})
    except Exception:
        storage = {}

    description = set_or_get(context, "meta_description")
    keywords = set_or_get(context, "meta_keywords")
    title = set_or_get(context, "meta_title")
    url = set_or_get(context, "meta_url")

    html = f"""
    <meta name="description" content="{description}">
    <meta name="twitter:description" content="{description}">
    <meta property="og:description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <meta property="og:title" content="{title}">
    <meta name="twitter:title" content="{title}">
    <meta property="og:url" content="{url}">
    <meta property="twitter:url" content="{url}">
    <meta property="og:type" content="website">
    <meta property="twitter:domain" content="mybustimes.cc">
    <meta property="og:image" content="https://www.mybustimes.cc/static/src/icons/mbt.png">
    <meta name="twitter:image" content="https://www.mybustimes.cc/static/src/icons/mbt.png">
    <meta name="twitter:card" content="mbt logo">
    """
    return mark_safe(html)

