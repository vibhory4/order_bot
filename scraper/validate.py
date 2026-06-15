"""VALIDATE layer — coerce record dicts into Pydantic models, skipping bad rows.

Invalid records are logged and dropped so a single malformed row never crashes
the whole run. Callers receive only valid models plus a failure count.
"""
from __future__ import annotations

import logging

from pydantic import ValidationError

from .models import CompetitorCollection, CompetitorProduct

log = logging.getLogger(__name__)


def validate_products(rows: list[dict]) -> tuple[list[CompetitorProduct], int]:
    valid: list[CompetitorProduct] = []
    failures = 0
    for row in rows:
        try:
            valid.append(CompetitorProduct(**row))
        except ValidationError as exc:
            failures += 1
            log.warning(
                "skipping invalid product (handle=%r): %s",
                row.get("handle"),
                exc.errors(),
            )
    return valid, failures


def validate_collections(rows: list[dict]) -> tuple[list[CompetitorCollection], int]:
    valid: list[CompetitorCollection] = []
    failures = 0
    for row in rows:
        try:
            valid.append(CompetitorCollection(**row))
        except ValidationError as exc:
            failures += 1
            log.warning(
                "skipping invalid collection (handle=%r): %s",
                row.get("handle"),
                exc.errors(),
            )
    return valid, failures
