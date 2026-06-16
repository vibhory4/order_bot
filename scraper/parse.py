"""PARSE layer — pure functions that turn Shopify JSON into plain record dicts.

No network, no validation. Validation happens in ``validate.py``.
"""
from __future__ import annotations

import html
import json
import logging
import re
from html.parser import HTMLParser

log = logging.getLogger(__name__)

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


# --- Pass 2: HTML SEO-meta enrichment ---------------------------------------
# Shopify's public product JSON has no meta_title / meta_description, so for an
# SEO analysis we read those from each product's HTML page: <title>,
# <meta name="description">, and any JSON-LD Product block.


class _MetaExtractor(HTMLParser):
    """Pulls <title>, meta description, and ld+json script bodies from a page."""

    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.meta_description: str | None = None
        self.ldjson_blocks: list[str] = []
        self._in_title = False
        self._in_ldjson = False
        self._title_buf: list[str] = []
        self._ld_buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
            self._title_buf = []
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key in ("description", "og:description") and not self.meta_description:
                self.meta_description = a.get("content") or None
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_ldjson = True
            self._ld_buf = []

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_buf).strip() or None
        elif tag == "script" and self._in_ldjson:
            self._in_ldjson = False
            self.ldjson_blocks.append("".join(self._ld_buf))

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)
        if self._in_ldjson:
            self._ld_buf.append(data)


def _iter_jsonld_objects(blocks: list[str]):
    """Yield every JSON-LD object, flattening @graph and top-level lists."""
    for block in blocks:
        try:
            data = json.loads(block)
        except (ValueError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            if isinstance(obj.get("@graph"), list):
                for node in obj["@graph"]:
                    if isinstance(node, dict):
                        yield node
            else:
                yield obj


def _is_product(obj: dict) -> bool:
    t = obj.get("@type")
    if isinstance(t, list):
        return any(str(x).lower() == "product" for x in t)
    return str(t).lower() == "product"


def _jsonld_price(offers) -> float | None:
    """Extract a price from a JSON-LD offers value (dict, list, or AggregateOffer)."""
    if isinstance(offers, list):
        for o in offers:
            price = _jsonld_price(o)
            if price is not None:
                return price
        return None
    if isinstance(offers, dict):
        for field in ("price", "lowPrice", "highPrice"):
            raw = offers.get(field)
            if raw not in (None, ""):
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    continue
    return None


def parse_product_meta(html_text: str) -> dict:
    """Extract SEO meta from a product HTML page.

    Returns keys: meta_title, meta_description, jsonld_name, jsonld_description,
    jsonld_price (any of which may be None).
    """
    extractor = _MetaExtractor()
    try:
        extractor.feed(html_text)
    except Exception as exc:  # noqa: BLE001 - malformed HTML must not crash a run
        log.warning("HTML parse error during meta extraction: %s", exc)

    result = {
        "meta_title": extractor.title,
        "meta_description": (extractor.meta_description or "").strip() or None,
        "jsonld_name": None,
        "jsonld_description": None,
        "jsonld_price": None,
    }

    for obj in _iter_jsonld_objects(extractor.ldjson_blocks):
        if _is_product(obj):
            result["jsonld_name"] = obj.get("name") or result["jsonld_name"]
            result["jsonld_description"] = strip_html(obj.get("description")) or result["jsonld_description"]
            price = _jsonld_price(obj.get("offers"))
            if price is not None:
                result["jsonld_price"] = price
            break

    return result
