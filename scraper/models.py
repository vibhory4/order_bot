"""Pydantic schemas for normalized competitor records.

Every record is validated against these before it is written; invalid rows are
logged and skipped by ``validate.py`` so a bad row never crashes the run.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VariantPrice(BaseModel):
    """One purchasable variant — for cakes this is usually a size (0.5kg, 1kg...)."""

    title: str | None = None
    price: float | None = None
    sku: str | None = None


class CompetitorProduct(BaseModel):
    # Required — a record without these is not useful.
    source: str
    url: str
    product_name: str
    handle: str

    # Optional / best-effort.
    description: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    price: float | None = None
    variant_sizes_prices: list[VariantPrice] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    product_type: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=_utcnow)


class CompetitorCollection(BaseModel):
    source: str
    title: str
    handle: str

    meta_title: str | None = None
    meta_description: str | None = None
    product_count: int | None = None
