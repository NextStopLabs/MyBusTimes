from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
import json

register = template.Library()

FEATURE_ICONS = {
    "USB-C": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v6l3 3"/><rect x="8" y="11" width="8" height="7" rx="1.5"/><circle cx="12" cy="14.5" r="0.5"/></svg>""",
    "USB-A": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v6l3 3"/><rect x="7" y="11" width="10" height="9" rx="2"/><line x1="9" y1="14" x2="15" y2="14"/><line x1="9" y1="17" x2="15" y2="17"/></svg>""",
    "USB A": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v6l3 3"/><rect x="7" y="11" width="10" height="9" rx="2"/><line x1="9" y1="14" x2="15" y2="14"/><line x1="9" y1="17" x2="15" y2="17"/></svg>""",
    "Power Sockets": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 7l-4.5 10"/><path d="M8 7l4.5 10"/><path d="M7 2v4"/><path d="M17 2v4"/><rect x="3" y="6" width="18" height="11" rx="2"/></svg>""",
    "Wireless Charging": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="11" rx="2"/><path d="M11 9l-2 4h6l-2 4"/><line x1="9" y1="4" x2="9" y2="7"/><line x1="15" y1="4" x2="15" y2="7"/></svg>""",
    "Wi-Fi": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M6.5 10.5a9 9 0 0 1 10.93 0"/><path d="M3 7a13 13 0 0 1 17.93 0"/><path d="M10 14a6 6 0 0 1 5.93 0"/><circle cx="13.5" cy="17.5" r="1.5"/></svg>""",
    "WiFi": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1"/></svg>""",
    "Announcements": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="11" height="14" rx="2"/><path d="M4 9H2a2 2 0 0 0 0 4h2"/><circle cx="15" cy="10" r="2"/><circle cx="15" cy="10" r="5"/><path d="M15 15l4 4"/></svg>""",
    "Tables": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="1"/><line x1="3" y1="12" x2="21" y2="12"/></svg>""",
    "Seat Belts": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2l14 20"/><path d="M12 7l-7 10h14L12 7Z"/><path d="M12 7v10"/></svg>""",
    "Bicycle Spaces": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="14.5" r="3.5"/><circle cx="18.5" cy="14.5" r="3.5"/><path d="M17 14.5l-4-7H9"/><path d="M9 11l6.5 3.5"/><path d="M13 7.5V4"/></svg>""",
    "Luggage Racks": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="9" width="14" height="12" rx="2"/><path d="M9 9V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4"/><line x1="9" y1="14" x2="15" y2="14"/></svg>""",
    "Air Conditioning": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>""",
}


@register.filter
def feature_icon(feature_name):
    svg = FEATURE_ICONS.get(feature_name, "")
    if not svg:
        return feature_name
    return mark_safe(
        f'<span class="feature-icon" title="{feature_name}">{svg}</span>'
    )


@register.filter
def feature_icons(features):
    if not features:
        return ""
    items = []
    for f in features:
        svg = FEATURE_ICONS.get(f, "")
        if svg:
            items.append(f'<span class="feature-icon" title="{f}">{svg}</span>')
        else:
            items.append(f)
    return mark_safe("".join(items))


@register.simple_tag
def feature_icons_json():
    return mark_safe(json.dumps(FEATURE_ICONS))
