# Competitive-research scraper

Polite, resumable scraper that pulls **public** product/collection data for SEO/naming
analysis. This iteration covers **Creme Castle** (a Shopify store) via its public JSON
endpoints. Bakingo is planned but not yet implemented.

## Install & run

```bash
pip install -r scraper/requirements.txt

# Offline dry-run against bundled sample JSON (no network needed):
python -m scraper.run --source cremecastle --fixtures

# Live crawl (requires network egress to cremecastle.in):
python -m scraper.run --source cremecastle

# Live crawl + SEO meta enrichment (Pass 2, see below):
python -m scraper.run --source cremecastle --enrich-meta

# Scrape only ONE collection (category) by its handle:
python -m scraper.run --source cremecastle --collection birthday-cakes --enrich-meta
```

The collection handle is the slug in the site's category URL, e.g.
`cremecastle.in/collections/birthday-cakes` → `birthday-cakes`. Run without
`--collection` (or list `/collections.json`) to see all available handles.

Outputs are written to `data/`:
- `competitor_products.csv` / `.jsonl`
- `competitor_collections.csv`

A summary is printed per source: `#collections`, `#products`, `#validation_failures`.

## How it works (layers)

| Module | Layer | Responsibility |
|---|---|---|
| `fetch.py` | fetch | httpx GET with research-bot UA, ~1 req/s throttle, exp. backoff on 429/5xx, robots check, cache-through. httpx is imported lazily so `--fixtures` needs only pydantic. |
| `cache.py` | fetch | Caches every raw response to `data/raw/<source>/<sha256(url)>` → resumable; re-parsing never re-hits the site. |
| `robots.py` | fetch | robots.txt enforcement (stdlib `urllib.robotparser`). |
| `parse.py` | parse | Pure functions: Shopify JSON → record dicts (HTML-stripped descriptions, variants, tags, images). |
| `validate.py` | validate | Coerce dicts into `CompetitorProduct` / `CompetitorCollection`; log & skip invalid rows. |
| `write.py` | write | Serialize to CSV (nested fields JSON-encoded per cell) + JSONL. |
| `sources/cremecastle.py` | — | Orchestrates the Shopify crawl (collections → per-collection products → canonical catalogue with category backfill). |
| `run.py` | — | CLI entrypoint + summary. |

## Two passes

- **Pass 1 (default):** the Shopify `*.json` endpoints give names, descriptions, prices,
  variants, tags, categories, and images. Fast and complete, but Shopify's public JSON has
  **no SEO `meta_title` / `meta_description`**, so those stay null.
- **Pass 2 (`--enrich-meta`):** for an SEO analysis, this fetches each product's HTML page and
  reads `<title>`, `<meta name="description">`, and JSON-LD `Product` schema — filling the meta
  fields and backfilling `description` / `price` only where Pass 1 left them empty. It roughly
  doubles request count but reuses the same cache + 1 req/s throttle. Parsing uses the stdlib
  `html.parser` (no BeautifulSoup dependency).

## Notes

- **Shopify limitation:** the public product JSON has no SEO `meta_title` / `meta_description`
  and no breadcrumb category, so `meta_*` need Pass 2 (`--enrich-meta`) and `category` is derived
  from the collection a product belongs to.
- **Network:** Claude Code cloud sessions block non-allowlisted hosts; allowlist
  `cremecastle.in` (network egress settings) for live runs, or run locally.
- **User-Agent:** one honest, descriptive research-bot UA — no browser spoofing.
