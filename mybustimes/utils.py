"""Shared lightweight parsing / request helpers used across apps."""

import logging

logger = logging.getLogger(__name__)


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