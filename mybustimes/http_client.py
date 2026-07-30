import atexit
import logging
import threading

import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def _apply_default_timeout(kwargs):
    if kwargs.get("timeout") is None:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    return kwargs


_local = threading.local()


def _get_session():
    session = getattr(_local, "session", None)
    if session is None:
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(total=2, backoff_factor=0.1),
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _local.session = session
    return session


def _close_session():
    session = getattr(_local, "session", None)
    if session is not None:
        try:
            session.close()
        except Exception:
            pass
        _local.session = None


atexit.register(_close_session)


def get(url, **kwargs):
    return _get_session().get(url, **_apply_default_timeout(kwargs))


def post(url, **kwargs):
    return _get_session().post(url, **_apply_default_timeout(kwargs))


def put(url, **kwargs):
    return _get_session().put(url, **_apply_default_timeout(kwargs))


def delete(url, **kwargs):
    return _get_session().delete(url, **_apply_default_timeout(kwargs))


def patch(url, **kwargs):
    return _get_session().patch(url, **_apply_default_timeout(kwargs))
