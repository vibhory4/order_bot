"""robots.txt enforcement.

Uses the stdlib ``urllib.robotparser``. Each site's robots.txt is fetched once
(via httpx, so it shares our timeout/UA) and cached in-process. If robots.txt
cannot be fetched we fail open (allow) but log it — Shopify generally allows the
JSON endpoints, and we do not want a transient robots fetch error to block a run.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from . import config

log = logging.getLogger(__name__)

_PARSERS: dict[str, RobotFileParser] = {}


def _parser_for(url: str) -> RobotFileParser:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin in _PARSERS:
        return _PARSERS[origin]

    rp = RobotFileParser()
    robots_url = f"{origin}/robots.txt"
    try:
        import httpx  # lazy import — not needed in --fixtures mode

        resp = httpx.get(
            robots_url,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            log.warning("robots.txt %s returned HTTP %s; allowing", robots_url, resp.status_code)
            rp.allow_all = True
    except Exception as exc:  # noqa: BLE001 - fail open, but loudly
        log.warning("could not fetch robots.txt %s (%s); allowing", robots_url, exc)
        rp.allow_all = True

    _PARSERS[origin] = rp
    return rp


def can_fetch(url: str) -> bool:
    """Return whether our User-Agent is permitted to fetch ``url``."""
    return _parser_for(url).can_fetch(config.USER_AGENT, url)
