# -*- coding: utf-8 -*-
"""
utils/network.py
=================
Network hardening helpers: a pre-configured `requests.Session` with
retry/backoff for transient failures (used by ThingSpeak and Telegram
helpers), plus a generic retry decorator for arbitrary callables such
as sensor reads that talk to hardware over I2C/SPI-like buses.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import NETWORK_BACKOFF_BASE, NETWORK_BACKOFF_MAX, NETWORK_MAX_RETRIES
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def build_http_session(
    total: int = NETWORK_MAX_RETRIES, backoff: float = NETWORK_BACKOFF_BASE
) -> requests.Session:
    """Return a `requests.Session` configured with retry/backoff and a
    trusted CA bundle, used for all outbound HTTP calls (ThingSpeak,
    Telegram REST fallback, etc.)."""
    retry = Retry(
        total=total,
        connect=total,
        read=total,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.verify = certifi.where()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def retry_with_backoff(
    max_attempts: int = NETWORK_MAX_RETRIES,
    base_delay: float = NETWORK_BACKOFF_BASE,
    max_delay: float = NETWORK_BACKOFF_MAX,
    exceptions: tuple = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry a function call with exponential backoff.

    Never raises after exhausting attempts when `default` is supplied
    via functools.partial-style wrapping is not needed here -- callers
    that want graceful degradation should catch the final exception.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            delay = base_delay
            last_exc: Exception | None = None
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    last_exc = exc
                    attempt += 1
                    logger.warning(
                        "%s failed (attempt %d/%d): %s",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                    )
                    if attempt >= max_attempts:
                        break
                    time.sleep(min(delay, max_delay))
                    delay *= 2
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


def is_internet_reachable(host: str = "https://api.telegram.org", timeout: float = 5.0) -> bool:
    """Best-effort connectivity probe used after boot / outages."""
    try:
        requests.head(host, timeout=timeout, verify=certifi.where())
        return True
    except requests.RequestException:
        return False


def wait_for_internet(poll_interval: float = 5.0, max_wait: float | None = None) -> bool:
    """Block until the internet becomes reachable (or max_wait elapses)."""
    waited = 0.0
    while not is_internet_reachable():
        logger.warning("No internet connectivity detected, waiting %.1fs...", poll_interval)
        time.sleep(poll_interval)
        waited += poll_interval
        if max_wait is not None and waited >= max_wait:
            return False
    return True
