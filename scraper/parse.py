"""PARSE layer — pure functions that turn Shopify JSON into plain record dicts.

No network, no validation. Validation happens in ``validate.py``.
"""
from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(value: str | None) -> str | None:
    """Convert an HTML fragment (Shopify ``body_html``) to collapsed plain text."""
    if not value:
        return None
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text or None


def _split_tags(tags) -> list[str]:
    """Shopify returns tags as a comma-separated string or a list, depending on endpoint."""
    if isinstance(tags, list):
        return [t.strip() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []


def _min_price(variants: list[dict]) -> float | None:
    prices = []
    for v in variants:
        raw = v.get("price")
        if raw is None or raw == "":
            continue
        try:
            prices.append(float(raw))
        except (TypeError, ValueError):
            continue
    return min(prices) if prices else None


def parse_product(source: str, base_url: str, product: dict, category: str | None) -> dict:
    """Map a single Shopify product object to a normalized record dict."""
    handle = product.get("handle")
    variants = product.get("variants") or []
    images = product.get("images") or []

    return {
        "source": source,
        "url": f"{base_url}/products/{handle}" if handle else base_url,
        "product_name": product.get("title"),
        "description": strip_html(product.get("body_html")),
        # Shopify's public product JSON carries no SEO meta fields.
        "meta_title": None,
        "meta_description": None,
        "handle": handle,
        "category": category,
        "subcategory": None,
        "price": _min_price(variants),
        "variant_sizes_prices": [
            {"title": v.get("title"), "price": v.get("price"), "sku": v.get("sku")}
            for v in variants
        ],
        "tags": _split_tags(product.get("tags")),
        "product_type": product.get("product_type") or None,
        "image_urls": [img.get("src") for img in images if img.get("src")],
    }


def parse_products(source: str, base_url: str, payload: dict, category: str | None = None) -> list[dict]:
    """Parse a ``/products.json`` style payload into record dicts."""
    return [
        parse_product(source, base_url, p, category)
        for p in (payload.get("products") or [])
    ]


def parse_collections(source: str, payload: dict) -> list[dict]:
    """Parse a ``/collections.json`` payload into collection record dicts."""
    out = []
    for c in payload.get("collections") or []:
        out.append(
            {
                "source": source,
                "title": c.get("title"),
                "handle": c.get("handle"),
                "meta_title": None,
                "meta_description": strip_html(c.get("body_html")),
                "product_count": c.get("products_count"),
            }
        )
    return out
