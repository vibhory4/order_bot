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


def crawl(
    fixtures: bool = False,
    enrich_meta: bool = False,
    collection: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return ``(product_rows, collection_rows)`` for Creme Castle.

    If ``collection`` (a collection handle) is given, only that one category is
    scraped instead of the whole site.

    When ``enrich_meta`` is set, a second pass fetches each product's HTML page
    to fill the SEO ``meta_title`` / ``meta_description`` fields (and backfill
    description / price from JSON-LD) that the public JSON does not expose.
    """
    if collection:
        product_rows, collection_rows = _crawl_collection(collection, fixtures=fixtures)
    elif fixtures:
        product_rows, collection_rows = _crawl_fixtures()
    else:
        product_rows, collection_rows = _crawl_live()

    if enrich_meta:
        _enrich_meta(product_rows, fixtures=fixtures)

    return product_rows, collection_rows


def _all_collection_rows(fixtures: bool) -> list[dict]:
    """Fetch and parse every collection (the full category map)."""
    if fixtures:
        return parse.parse_collections(SOURCE, fetch.load_fixture("collections.json"))
    rows: list[dict] = []
    for payload in _paginated("/collections.json?limit={limit}&page={page}"):
        rows.extend(parse.parse_collections(SOURCE, payload))
    return rows


def _crawl_collection(handle: str, fixtures: bool) -> tuple[list[dict], list[dict]]:
    """Scrape a single collection: its metadata + the products inside it."""
    # 1. Find this collection's own metadata (title, description, count).
    match = next((c for c in _all_collection_rows(fixtures) if c.get("handle") == handle), None)
    if match is None:
        log.warning("collection %r not found in /collections.json; scraping products only", handle)
    title = match["title"] if match else None
    collection_rows = [match] if match else []

    # 2. Fetch the products that belong to this collection.
    if fixtures:
        payloads = [fetch.load_fixture("collection_products.json")]
    else:
        path = f"/collections/{handle}/products.json?limit={{limit}}&page={{page}}"
        payloads = _paginated(path)

    product_rows: list[dict] = []
    seen: set[str] = set()
    for payload in payloads:
        for row in parse.parse_products(SOURCE, BASE_URL, payload, category=title):
            h = row.get("handle")
            if h in seen:
                continue
            seen.add(h)
            product_rows.append(row)

    return product_rows, collection_rows


def _enrich_meta(product_rows: list[dict], fixtures: bool) -> None:
    """Pass 2: fill SEO meta fields from each product's HTML page. Mutates rows."""
    for row in product_rows:
        try:
            if fixtures:
                # Prefer a per-handle page fixture (mirrors live: each product
                # fetches its own page); fall back to a generic sample.
                try:
                    html_text = fetch.load_fixture_text(f"pages/{row.get('handle')}.html")
                except FileNotFoundError:
                    html_text = fetch.load_fixture_text("product_page.html")
            else:
                html_text = fetch.fetch_text(SOURCE, row["url"])
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the run
            log.warning("meta enrichment failed for %s: %s", row.get("handle"), exc)
            continue

        meta = parse.parse_product_meta(html_text)
        if meta.get("meta_title"):
            row["meta_title"] = meta["meta_title"]
        if meta.get("meta_description"):
            row["meta_description"] = meta["meta_description"]
        # Backfill from JSON-LD only when the JSON pass left these empty.
        if not row.get("description") and meta.get("jsonld_description"):
            row["description"] = meta["jsonld_description"]
        if row.get("price") is None and meta.get("jsonld_price") is not None:
            row["price"] = meta["jsonld_price"]


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
