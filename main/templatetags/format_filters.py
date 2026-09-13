from django import template

register = template.Library()

try:
    from main.username_utils import mask_email_username as _mask_email_username
    from main.username_utils import (
        profile_path_for as _profile_path_for,
        liveries_path_for as _liveries_path_for,
        block_path_for as _block_path_for,
        unblock_path_for as _unblock_path_for,
    )
except Exception:  # pragma: no cover - fallback if app not ready
    import re as _re
    _EMAIL_LIKE_RE = _re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

    def _mask_email_username(value):
        if value is None:
            return value
        text = str(value)
        if "@" not in text or not _EMAIL_LIKE_RE.match(text):
            return text
        return text.partition("@")[0]

    def _profile_path_for(value):
        username = getattr(value, "username", value)
        return f"/u/{username}/"

    def _liveries_path_for(value):
        username = getattr(value, "username", value)
        return f"/u/{username}/liveries/"

    def _block_path_for(value):
        username = getattr(value, "username", value)
        return f"/u/{username}/block/"

    def _unblock_path_for(value):
        username = getattr(value, "username", value)
        return f"/u/{username}/unblock/"


@register.filter(name="mask_email_username")
def mask_email_username(value):
    """Blank out everything after @ for email-like usernames (display only)."""
    return _mask_email_username(value)


@register.filter(name="display_username")
def display_username(value):
    """Alias of mask_email_username; accepts a user object or string."""
    username = getattr(value, "username", value)
    display = getattr(value, "display_username", None)
    if isinstance(display, str):
        return display
    return _mask_email_username(username)


@register.filter(name="profile_url")
def profile_url(value):
    """Canonical profile path: ``/u/id/<pk>/`` for email-like usernames."""
    return _profile_path_for(value)


@register.filter(name="liveries_url")
def liveries_url(value):
    """Canonical liveries path matching :func:`profile_url`."""
    return _liveries_path_for(value)


@register.filter(name="block_url")
def block_url(value):
    """Canonical block-action path matching :func:`profile_url`."""
    return _block_path_for(value)


@register.filter(name="unblock_url")
def unblock_url(value):
    """Canonical unblock-action path matching :func:`profile_url`."""
    return _unblock_path_for(value)

@register.filter
def format_feature_name(value):
    formatted = value.replace('_', ' ').title()
    # Replace 'Mbt' with 'MBT' if present
    return formatted.replace('Mbt', 'MBT')
