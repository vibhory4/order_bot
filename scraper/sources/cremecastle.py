"""Creme Castle (Shopify) crawl orchestration.

Uses Shopify's public JSON endpoints rather than HTML:
  - /collections.json                          → the category map
  - /collections/<handle>/products.json        → products per category
  - /products.json                             → canonical catalogue (dedupe)

Returns raw record dicts (no validation here). In ``fixtures`` mode it reads
bundled sample JSON instead of the network, so the pipeline is testable offline.
"""
from __future__ import annotations

import logging

from .. import config, fetch, parse

log = logging.getLogger(__name__)

SOURCE = "cremecastle"
BASE_URL = config.SOURCES[SOURCE]


def _paginated(path_template: str) -> list[dict]:
    """Fetch every page of a Shopify JSON endpoint until a page returns 0 items.

    ``path_template`` must contain ``{page}``. Returns the raw page payloads.
    """
    payloads: list[dict] = []
    page = 1
    while True:
        url = f"{BASE_URL}{path_template.format(page=page, limit=config.PAGE_SIZE)}"
        payload = fetch.fetch_json(SOURCE, url)
        items = payload.get("products") or payload.get("collections") or []
        if not items:
            break
        payloads.append(payload)
        page += 1
    return payloads


def crawl(fixtures: bool = False) -> tuple[list[dict], list[dict]]:
    """Return ``(product_rows, collection_rows)`` for Creme Castle."""
    if fixtures:
        return _crawl_fixtures()
    return _crawl_live()


def _crawl_live() -> tuple[list[dict], list[dict]]:
    # 1. Collections (the category map).
    collection_rows: list[dict] = []
    collection_handles: list[str] = []
    for payload in _paginated("/collections.json?limit={limit}&page={page}"):
        rows = parse.parse_collections(SOURCE, payload)
        collection_rows.extend(rows)
        collection_handles.extend(c["handle"] for c in rows if c.get("handle"))

    # 2. Products per collection → build handle -> [category titles] membership map.
    handle_to_title = {c["handle"]: c["title"] for c in collection_rows if c.get("handle")}
    membership: dict[str, list[str]] = {}
    for handle in collection_handles:
        title = handle_to_title.get(handle)
        path = f"/collections/{handle}/products.json?limit={{limit}}&page={{page}}"
        for payload in _paginated(path):
            for row in parse.parse_products(SOURCE, BASE_URL, payload, category=title):
                membership.setdefault(row["handle"], []).append(title)

    # 3. Canonical catalogue; dedupe by handle, backfill category from membership.
    product_rows: list[dict] = []
    seen: set[str] = set()
    for payload in _paginated("/products.json?limit={limit}&page={page}"):
        for row in parse.parse_products(SOURCE, BASE_URL, payload):
            handle = row.get("handle")
            if handle in seen:
                continue
            seen.add(handle)
            cats = membership.get(handle, [])
            if cats:
                row["category"] = cats[0]
                # Extra collection memberships are recorded as tags for analysis.
                for extra in cats[1:]:
                    if extra and extra not in row["tags"]:
                        row["tags"].append(extra)
            product_rows.append(row)

    return product_rows, collection_rows


def _crawl_fixtures() -> tuple[list[dict], list[dict]]:
    """Offline path: parse bundled fixture payloads (single page each)."""
    collections_payload = fetch.load_fixture("collections.json")
    collection_rows = parse.parse_collections(SOURCE, collections_payload)

    # Per-collection products fixture carries a category label.
    coll_products = fetch.load_fixture("collection_products.json")
    category = collection_rows[0]["title"] if collection_rows else None
    membership: dict[str, list[str]] = {}
    for row in parse.parse_products(SOURCE, BASE_URL, coll_products, category=category):
        membership.setdefault(row["handle"], []).append(category)

    products_payload = fetch.load_fixture("products.json")
    product_rows: list[dict] = []
    seen: set[str] = set()
    for row in parse.parse_products(SOURCE, BASE_URL, products_payload):
        handle = row.get("handle")
        if handle in seen:
            continue
        seen.add(handle)
        if handle in membership:
            row["category"] = membership[handle][0]
        product_rows.append(row)

    return product_rows, collection_rows
