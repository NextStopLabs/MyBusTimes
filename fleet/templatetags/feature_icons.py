from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
import json

register = template.Library()

# All icons: 24x24 viewBox, stroke-based, currentColor, stroke-width 1.5
# Designed to be visually consistent (feather/lucide-style line icon set).

FEATURE_ICONS = {
    "USB-C": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><g fill="currentColor"><path d="M8 11a1 1 0 1 0 0 2h8a1 1 0 1 0 0-2z"></path><path fill-rule="evenodd" d="M3 12a5 5 0 0 1 5-5h8a5 5 0 0 1 0 10H8a5 5 0 0 1-5-5m5-3h8a3 3 0 1 1 0 6H8a3 3 0 1 1 0-6" clip-rule="evenodd"></path></g></svg>""",

    "USB-A": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 16 16"><g fill="currentColor"><path d="M2.25 7a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h11.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25z"></path><path d="M0 5.5A.5.5 0 0 1 .5 5h15a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-.5.5H.5a.5.5 0 0 1-.5-.5zM1 10h14V6H1z"></path></g></svg>""",

    "USB A": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 16 16"><g fill="currentColor"><path d="M2.25 7a.25.25 0 0 0-.25.25v1c0 .138.112.25.25.25h11.5a.25.25 0 0 0 .25-.25v-1a.25.25 0 0 0-.25-.25z"></path><path d="M0 5.5A.5.5 0 0 1 .5 5h15a.5.5 0 0 1 .5.5v5a.5.5 0 0 1-.5.5H.5a.5.5 0 0 1-.5-.5zM1 10h14V6H1z"></path></g></svg>""",

    "Power Sockets": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="18" height="18" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect width="20" height="20" x="2" y="2" rx="2"></rect><path d="M12 8v2m-2 5H8m6 0h2"></path></g></svg>""",

    "Power sockets": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="18" height="18" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect width="20" height="20" x="2" y="2" rx="2"></rect><path d="M12 8v2m-2 5H8m6 0h2"></path></g></svg>""",

    "Wireless Charging": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="m3.929 4.929l1.414 1.414A7.98 7.98 0 0 0 3 12c0 2.21.895 4.21 2.343 5.657L3.93 19.07A9.97 9.97 0 0 1 1 12a9.97 9.97 0 0 1 2.929-7.071m16.142 0A9.97 9.97 0 0 1 23 12a9.97 9.97 0 0 1-2.929 7.071l-1.414-1.414A7.98 7.98 0 0 0 21 12a7.98 7.98 0 0 0-2.342-5.656zM13 5v6h3l-5 8v-6H8zM6.757 7.757l1.415 1.415A4 4 0 0 0 7 12c0 1.104.448 2.105 1.172 2.828l-1.415 1.415A5.98 5.98 0 0 1 5 12c0-1.657.672-3.157 1.757-4.243m10.487.001A5.98 5.98 0 0 1 19 12a5.98 5.98 0 0 1-1.757 4.243l-1.415-1.415A4 4 0 0 0 17 12a4 4 0 0 0-1.17-2.827z"></path></svg>""",

    "Wi-Fi": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"><path d="M13.308 17.886a1.308 1.308 0 1 1-2.616 0a1.308 1.308 0 0 1 2.616 0m-5.011-3.702a5.234 5.234 0 0 1 7.406 0M5.524 11.41a9.16 9.16 0 0 1 12.952 0"></path><path d="M2.75 8.636a13.083 13.083 0 0 1 18.5 0"></path></g></svg>""",

    "WiFi": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"><path d="M13.308 17.886a1.308 1.308 0 1 1-2.616 0a1.308 1.308 0 0 1 2.616 0m-5.011-3.702a5.234 5.234 0 0 1 7.406 0M5.524 11.41a9.16 9.16 0 0 1 12.952 0"></path><path d="M2.75 8.636a13.083 13.083 0 0 1 18.5 0"></path></g></svg>""",

    "Announcements": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 16 16"><path d="M8.694 2.04A.5.5 0 0 1 9 2.5v11a.5.5 0 0 1-.85.357l-2.927-2.875H3.5a1.5 1.5 0 0 1-1.5-1.5v-2.99a1.5 1.5 0 0 1 1.5-1.5h1.724l2.927-2.85a.5.5 0 0 1 .543-.103zm3.043 1.02l.087.058l.098.085c.063.056.15.138.252.245c.206.213.476.527.746.938a6.542 6.542 0 0 1 1.083 3.618a6.522 6.522 0 0 1-1.083 3.614c-.27.41-.541.724-.746.936l-.142.141l-.187.17l-.033.026a.5.5 0 0 1-.688-.72l.13-.117a5.49 5.49 0 0 0 .83-.985c.46-.7.919-1.73.919-3.065a5.542 5.542 0 0 0-.919-3.069a5.588 5.588 0 0 0-.54-.698l-.17-.176l-.184-.17a.5.5 0 0 1 .547-.832zM8 3.684L5.776 5.851a.5.5 0 0 1-.349.142H3.5a.5.5 0 0 0-.5.5v2.989a.5.5 0 0 0 .5.5h1.927a.5.5 0 0 1 .35.143L8 12.308V3.685zm2.738 1.374l.1.07l.133.126l.054.056c.114.123.26.302.405.54c.292.48.574 1.193.574 2.148c0 .954-.282 1.668-.573 2.148a3.388 3.388 0 0 1-.405.541l-.102.105l-.07.065l-.04.033l-.063.03c-.133.052-.442.139-.64-.108a.5.5 0 0 1 .012-.638l.134-.129l.034-.036c.075-.08.179-.208.284-.382c.21-.345.429-.882.429-1.63c0-.747-.219-1.283-.428-1.627a2.467 2.467 0 0 0-.223-.311l-.095-.105l-.069-.065a.5.5 0 0 1 .55-.83z" fill="currentColor" fill-rule="nonzero"></path></svg>""",

    "Tables": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M23 13H1v2h2v4h2v-4h14v4h2v-4h2z"></path></svg>""",

    "Seat Belts": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a2 2 0 0 1 2 2c0 1.11-.89 2-2 2a2 2 0 0 1-2-2a2 2 0 0 1 2-2m.39 12.79a34 34 0 0 1 4.25.25c.06-2.72-.18-5.12-.64-6.04c-.13-.27-.31-.5-.5-.7l-8.07 6.92c1.36-.22 3.07-.43 4.96-.43M7.46 17c.13 1.74.39 3.5.81 5h2.07c-.29-.88-.5-1.91-.66-3c0 0 2.32-.44 4.64 0c-.16 1.09-.37 2.12-.66 3h2.07c.44-1.55.7-3.39.83-5.21a35 35 0 0 0-4.17-.25c-1.93 0-3.61.21-4.93.46M12 7S9 7 8 9c-.34.68-.56 2.15-.63 3.96l6.55-5.62C12.93 7 12 7 12 7m6.57-1.33l-1.14-1.33l-3.51 3.01c.55.19 1.13.49 1.58.95zm2.1 10.16c-.09-.03-1.53-.5-4.03-.79c-.01.57-.04 1.16-.08 1.75c2.25.28 3.54.71 3.56.71zm-13.3-2.87l-3.94 3.38l.89 1.48c.02-.01 1.18-.46 3.14-.82c-.11-1.41-.14-2.8-.09-4.04"></path></svg>""",

    "Bicycle Spaces": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M19 10c-.56 0-1.09.11-1.59.28L14.46 4.5H11V6h2.54l.88 1.72L12 13.13l-1.77-4.18c.27-.1.51-.37.51-.7c0-.41-.33-.75-.74-.75H8c-.42 0-.76.34-.76.75S7.58 9 8 9h.61l2.25 5.25h-.94C9.56 11.85 7.5 10 5 10c-2.76 0-5 2.24-5 5s2.24 5 5 5c2.5 0 4.56-1.85 4.92-4.25h2.58l2.79-6.32l.79 1.53A4.98 4.98 0 0 0 14 15c0 2.76 2.24 5 5 5s5-2.24 5-5s-2.24-5-5-5M5 18.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5c1.67 0 3.07 1.18 3.41 2.75H4v1.5h4.41A3.495 3.495 0 0 1 5 18.5m14 0c-1.93 0-3.5-1.57-3.5-3.5c0-1.08.5-2.03 1.27-2.67l1.8 3.52l1.32-.72l-1.79-3.5c.29-.07.59-.13.9-.13c1.93 0 3.5 1.57 3.5 3.5s-1.57 3.5-3.5 3.5"></path></svg>""",

    "Luggage Racks": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M7 21q-.825 0-1.412-.587T5 19V8q0-.825.588-1.412T7 6h2V4q0-.825.588-1.412T11 2h2q.825 0 1.413.588T15 4v2h2q.825 0 1.413.588T19 8v11q0 .825-.587 1.413T17 21q0 .425-.288.713T16 22t-.712-.288T15 21H9q0 .425-.288.713T8 22t-.712-.288T7 21m0-2h10V8H7zm2-1h2V9H9zm4 0h2V9h-2zM11 6h2V4h-2zm1 7.5"></path></svg>""",

    "Air Conditioning": """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" style="color: rgb(74, 85, 101); opacity: 1; transform: rotate(0deg);" width="20" height="20" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M8 16a3 3 0 0 1-3 3m11-3a3 3 0 0 0 3 3m-7-3v4M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><path d="M7 13v-3a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v3"></path></g></svg>""",
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
def feature_icons(features, show_icons=True):
    if not features:
        return ""
    use_icons = show_icons is not False and str(show_icons).lower() not in ('false', '0', '')
    items = []
    for f in features:
        svg = FEATURE_ICONS.get(f, "")
        if svg and use_icons:
            items.append(f'<span class="feature-icon" title="{f}">{svg}</span>')
        else:
            items.append(f)
    separator = ", " if not use_icons else ""
    return mark_safe(separator.join(items))


@register.simple_tag
def feature_icons_json():
    return mark_safe(json.dumps(FEATURE_ICONS))