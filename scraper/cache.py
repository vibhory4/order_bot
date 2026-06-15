"""Raw-response cache.

Every fetched URL is written to ``data/raw/<source>/<sha256(url)>.json`` alongside
a small sidecar recording the original URL. If a cache entry exists we skip the
network entirely, so re-parsing never re-hits the site and runs are resumable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import config


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _paths(source: str, url: str) -> tuple[Path, Path]:
    base = config.RAW_DIR / source
    key = _key(url)
    return base / f"{key}.body", base / f"{key}.meta.json"


def read_cache(source: str, url: str) -> bytes | None:
    """Return cached raw bytes for ``url`` or ``None`` if not cached."""
    body_path, _ = _paths(source, url)
    if body_path.exists():
        return body_path.read_bytes()
    return None


def write_cache(source: str, url: str, body: bytes) -> None:
    """Persist raw bytes plus a sidecar mapping the hash back to the URL."""
    body_path, meta_path = _paths(source, url)
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_bytes(body)
    meta_path.write_text(json.dumps({"url": url}), encoding="utf-8")
