from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
import json

register = template.Library()

# All icons: 24x24 viewBox, stroke-based, currentColor, stroke-width 1.5
# Designed to be visually consistent (feather/lucide-style line icon set).

FEATURE_ICONS = {
    "USB-C": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="7" y="9" width="10" height="6" rx="3"/>
<line x1="9.5" y1="12" x2="9.5" y2="12"/>
<line x1="14.5" y1="12" x2="14.5" y2="12"/>
<line x1="12" y1="4" x2="12" y2="9"/>
<line x1="12" y1="15" x2="12" y2="20"/>
</svg>""",

    "USB-A": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="8" y="4" width="8" height="5" rx="1"/>
<line x1="10" y1="6" x2="10" y2="6"/>
<line x1="14" y1="6" x2="14" y2="6"/>
<line x1="12" y1="9" x2="12" y2="14"/>
<path d="M8 14h8v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-4Z"/>
</svg>""",

    "USB A": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="8" y="4" width="8" height="5" rx="1"/>
<line x1="10" y1="6" x2="10" y2="6"/>
<line x1="14" y1="6" x2="14" y2="6"/>
<line x1="12" y1="9" x2="12" y2="14"/>
<path d="M8 14h8v4a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-4Z"/>
</svg>""",

    "Power Sockets": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="9"/>
<line x1="9" y1="9" x2="9" y2="12.5"/>
<line x1="15" y1="9" x2="15" y2="12.5"/>
<path d="M9 15.5a3 3 0 0 0 6 0"/>
</svg>""",

    "Wireless Charging": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="3" y="15" width="18" height="4" rx="1.5"/>
<path d="M8 12a4 4 0 0 1 8 0"/>
<path d="M10 9a2 2 0 0 1 4 0"/>
<path d="M12 15v-2.2"/>
</svg>""",

    "Wi-Fi": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<path d="M2 8.5a15 15 0 0 1 20 0"/>
<path d="M5.5 12.5a10 10 0 0 1 13 0"/>
<path d="M9 16.5a5 5 0 0 1 6 0"/>
<circle cx="12" cy="19.5" r="1" fill="currentColor" stroke="none"/>
</svg>""",

    "WiFi": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<path d="M2 8.5a15 15 0 0 1 20 0"/>
<path d="M5.5 12.5a10 10 0 0 1 13 0"/>
<path d="M9 16.5a5 5 0 0 1 6 0"/>
<circle cx="12" cy="19.5" r="1" fill="currentColor" stroke="none"/>
</svg>""",

    "Announcements": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<path d="M4 10v4a1 1 0 0 0 1 1h2l4.5 3.5a1 1 0 0 0 1.5-.8V6.3a1 1 0 0 0-1.5-.8L7 9H5a1 1 0 0 0-1 1Z"/>
<path d="M17 9a4 4 0 0 1 0 6"/>
<path d="M19.5 6.5a8 8 0 0 1 0 11"/>
</svg>""",

    "Tables": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<path d="M3 8h13a2 2 0 0 1 2 2v1"/>
<line x1="3" y1="8" x2="3" y2="19"/>
<line x1="16" y1="8" x2="16" y2="19"/>
<line x1="3" y1="13" x2="18" y2="13"/>
<line x1="20" y1="13" x2="21" y2="13"/>
<line x1="18" y1="11" x2="18" y2="19"/>
</svg>""",

    "Seat Belts": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<path d="M5 3c3 4 3 6 0 10"/>
<path d="M19 3c-3 4-3 6 0 10"/>
<rect x="9.5" y="12" width="5" height="4" rx="1"/>
<path d="M9.5 14H7a2 2 0 0 1-2-2"/>
<path d="M14.5 14H17a2 2 0 0 0 2-2"/>
<line x1="12" y1="16" x2="12" y2="21"/>
</svg>""",

    "Bicycle Spaces": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<circle cx="5.5" cy="17.5" r="3.5"/>
<circle cx="18.5" cy="17.5" r="3.5"/>
<path d="M5.5 17.5 9 10h5l4 7.5"/>
<path d="M9 10 11 6h3"/>
<line x1="9" y1="10" x2="14" y2="17.5"/>
<line x1="18.5" y1="17.5" x2="14" y2="17.5"/>
</svg>""",

    "Luggage Racks": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<rect x="5" y="9" width="14" height="11" rx="2"/>
<path d="M9 9V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v3"/>
<line x1="5" y1="14" x2="19" y2="14"/>
<line x1="9" y1="14" x2="9" y2="20"/>
<line x1="15" y1="14" x2="15" y2="20"/>
</svg>""",

    "Air Conditioning": """<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
<path d="M12 3v18"/>
<path d="M4.5 6.5 19.5 17.5"/>
<path d="M19.5 6.5 4.5 17.5"/>
<path d="M9 5.5 12 3l3 2.5"/>
<path d="M9 18.5 12 21l3-2.5"/>
</svg>""",
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