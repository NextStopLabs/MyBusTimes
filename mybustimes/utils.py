"""Shared lightweight parsing / request helpers used across apps."""

import logging
import re

logger = logging.getLogger(__name__)


_EVIDENCE_URL_RE = re.compile(
    r'(?:www\.)'
    r'|\.(?:com|co\.uk|org\.uk|gov\.uk|ac\.uk|org|net|gov|edu|io|info|biz|'
    r'me|tv|co|uk|de|fr|es|it|nl|be|ch|at|se|no|dk|fi|ie|us|ca|au|nz|eu|'
    r'in|jp|cn|ru|br|za)\b',
    re.IGNORECASE,
)


def is_valid_evidence_url(value):
    """Return True if ``value`` looks like a real web URL.

    Accepts URLs containing ``www`` or a recognised domain ending such as
    ``.com``, ``.co.uk``, ``.uk``, etc. Used to stop plain text or raw image
    links being submitted as evidence.
    """
    if not value:
        return False
    value = value.strip()
    if not value:
        return False
    return bool(_EVIDENCE_URL_RE.search(value))


def safe_int(value, default=0):
    """Convert ``value`` to ``int`` returning ``default`` on bad input.

    Handles ``None``, empty strings, and non-numeric values without raising.
    """
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_json_body(request):
    """Parse ``request.body`` as JSON and return ``(data, error_response)``.

    On success returns ``(parsed, None)``. On failure returns ``(None, True)``
    so the caller can respond with a 400. ``error_response`` is truthy when the
    body was not valid JSON; the caller decides how to translate that to a response.
    """
    import json
    try:
        return json.loads(request.body), None
    except (ValueError, TypeError):
        return None, True