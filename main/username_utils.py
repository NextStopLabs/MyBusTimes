"""Helpers for displaying usernames safely.

Some historic accounts use an email address as their username
(e.g. ``22cbaylis@bewdley.worcs.sch.uk``). Displaying the full address
in public pages leaks the email domain, so the ``@`` and everything
after it is hidden (``22cbaylis``), and the canonical profile URL uses
the user id (``/u/id/<pk>/``) so the domain never appears in the
browser address bar either.
"""
import re

# Matches ``local@domain.tld`` where the domain has a dot and ends in a
# letter-only TLD of length >= 2. This covers .com, .org, .co.uk,
# .sch.uk, etc. Plain ``foo@bar`` (no dot/TLD) is left untouched.
_EMAIL_LIKE_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

MASK_SUFFIX = ""


def mask_email_username(username):
    """Return the public display form of a username.

    If ``username`` looks like an email address (contains ``@`` and the
    domain part has a TLD such as .com / .co.uk / .org), everything from
    the ``@`` onwards is hidden, e.g. ``user@example.com`` -> ``user``.
    All other usernames are returned unchanged.
    """
    if username is None:
        return username
    text = str(username)
    if "@" not in text:
        return text
    if not _EMAIL_LIKE_RE.match(text):
        return text
    local, _, _ = text.partition("@")
    return f"{local}{MASK_SUFFIX}"


def is_email_like_username(username):
    """Return True if ``username`` looks like an email address with a TLD.

    Such usernames get a redacted display form and an ID-based canonical
    profile URL so the email domain never appears in visible text or the
    browser address bar.
    """
    if username is None:
        return False
    text = str(username)
    return "@" in text and bool(_EMAIL_LIKE_RE.match(text))


def _username_and_id(user_or_username):
    """Split a user object (or plain username string) into (username, user_id)."""
    if isinstance(user_or_username, str):
        return user_or_username, None
    username = getattr(user_or_username, "username", user_or_username)
    user_id = getattr(user_or_username, "pk", None)
    if user_id is None:
        user_id = getattr(user_or_username, "id", None)
    return username, user_id


def profile_path_for(user_or_username):
    """Canonical public profile path without leaking email domains.

    Email-like usernames resolve to ``/u/id/<pk>/``; all other usernames
    keep the historic ``/u/<username>/`` form. Plain strings (no known id)
    fall back to the ``/u/<username>/`` form.
    """
    username, user_id = _username_and_id(user_or_username)
    if user_id and is_email_like_username(username):
        return f"/u/id/{user_id}/"
    return f"/u/{username}/"


def liveries_path_for(user_or_username):
    """Canonical liveries path matching :func:`profile_path_for`."""
    username, user_id = _username_and_id(user_or_username)
    if user_id and is_email_like_username(username):
        return f"/u/id/{user_id}/liveries/"
    return f"/u/{username}/liveries/"


def block_path_for(user_or_username):
    """Canonical block-action path matching :func:`profile_path_for`."""
    username, user_id = _username_and_id(user_or_username)
    if user_id and is_email_like_username(username):
        return f"/u/id/{user_id}/block/"
    return f"/u/{username}/block/"


def unblock_path_for(user_or_username):
    """Canonical unblock-action path matching :func:`profile_path_for`."""
    username, user_id = _username_and_id(user_or_username)
    if user_id and is_email_like_username(username):
        return f"/u/id/{user_id}/unblock/"
    return f"/u/{username}/unblock/"
