# shopify_products_scraper (vendored)

A vendored copy of [grabowskiadrian/shopify-products-scraper](https://github.com/grabowskiadrian/shopify-products-scraper)
with a small politeness layer added. It extracts a Shopify store's products plus
each product's SEO meta tags. See [`NOTICE`](./NOTICE) for attribution, the
(unstated) upstream license, and the list of local modifications.

> **Products only.** This tool does not scrape collections. For collections,
> caching, validation, and per-collection targeting, use the project's own
> [`scraper/`](../../scraper/README.md) package.

## Install

```bash
pip install -r third_party/shopify_products_scraper/requirements.txt
```

(Upstream's `requirements.txt` listed only `beautifulsoup4`; the script also
needs `requests` and `pandas`, which this corrected list includes.)

## Usage

```bash
cd third_party/shopify_products_scraper

# products + meta tags:
python3 shopfiy_scraper.py -t https://store.myshopify.com

# one row per variant (adds Variant Title, Price, SKU, inventory, etc.):
python3 shopfiy_scraper.py -t https://store.myshopify.com -v
```

Writes **`products.csv`** in the working directory.

| Mode | Columns |
|---|---|
| default | `Name, URL, Meta Title, Meta Description, Product Description` |
| `-v` | the above **plus** full variant detail (`Variant Title, Price, SKU, …`) |

## Politeness layer (added locally)

- Descriptive research **User-Agent** on every request
- **~1 request/second** throttle and a **30s timeout**
- Per-product errors are **logged to stderr and skipped** (one bad product won't
  crash the run)

## Network note

Running against a live store needs outbound access to that store. In Claude Code
cloud sessions, non-allowlisted hosts return `403 Host not in allowlist` — add the
target store to the environment's network egress settings, or run this on your own
machine.
