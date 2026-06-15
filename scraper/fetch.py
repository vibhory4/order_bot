"""FETCH layer — the only place that touches the network.

Responsibilities: rate limiting (~1 req/s), exponential backoff on 429/5xx,
robots.txt enforcement, and cache-through to ``data/raw/``. httpx is imported
lazily so that ``--fixtures`` mode (which calls :func:`load_fixture`) needs only
the stdlib + pydantic, not httpx.
"""
from __future__ import annotations

import json
import logging
import time

from . import cache, config, robots

log = logging.getLogger(__name__)

_last_request_at = 0.0


class RobotsDisallowed(Exception):
    """Raised when robots.txt forbids fetching a URL."""


def _throttle() -> None:
    """Block until at least RATE_LIMIT_SECONDS have passed since the last request."""
    global _last_request_at
    wait = config.RATE_LIMIT_SECONDS - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def fetch_bytes(source: str, url: str) -> bytes:
    """Return raw bytes for ``url``, using the cache when possible.

    Network path: respect robots.txt, throttle, then GET with retry/backoff on
    429/5xx. The response body is cached before returning so subsequent runs and
    re-parses never re-hit the site.
    """
    cached = cache.read_cache(source, url)
    if cached is not None:
        log.debug("cache hit %s", url)
        return cached

    if not robots.can_fetch(url):
        raise RobotsDisallowed(url)

    import httpx  # lazy import

    headers = {"User-Agent": config.USER_AGENT}
    last_exc: Exception | None = None

    for attempt in range(config.MAX_RETRIES + 1):
        _throttle()
        try:
            resp = httpx.get(
                url,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            last_exc = exc
            log.warning("request error for %s (attempt %d): %s", url, attempt + 1, exc)
        else:
            if resp.status_code in config.RETRY_STATUS_CODES:
                log.warning("HTTP %s for %s (attempt %d)", resp.status_code, url, attempt + 1)
                last_exc = httpx.HTTPStatusError(
                    f"status {resp.status_code}", request=resp.request, response=resp
                )
            else:
                resp.raise_for_status()
                cache.write_cache(source, url, resp.content)
                return resp.content

        if attempt < config.MAX_RETRIES:
            backoff = config.BACKOFF_BASE_SECONDS * (2 ** attempt)
            log.info("backing off %.0fs before retrying %s", backoff, url)
            time.sleep(backoff)

    raise RuntimeError(f"failed to fetch {url} after {config.MAX_RETRIES + 1} attempts") from last_exc


def fetch_json(source: str, url: str) -> dict:
    """Fetch ``url`` and parse the body as JSON."""
    return json.loads(fetch_bytes(source, url))


def load_fixture(name: str) -> dict:
    """Load a bundled fixture JSON file (offline dry-run mode). No network."""
    path = config.FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))
