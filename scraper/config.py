"""Static configuration for the scraper.

Kept dependency-free so it can be imported in ``--fixtures`` mode without httpx.
"""
from __future__ import annotations

from pathlib import Path

# --- Sources -----------------------------------------------------------------
# Per-source base URLs. Only Creme Castle is implemented in this iteration.
SOURCES: dict[str, str] = {
    "cremecastle": "https://cremecastle.in",
}

# --- HTTP politeness ----------------------------------------------------------
# One honest, descriptive User-Agent that names this as a research bot and gives
# a contact. We deliberately do NOT spoof a browser (UA stance deferred).
USER_AGENT = (
    "CakeResearchBot/1.0 (+competitive SEO research; non-commercial; "
    "contact: vibhugupta97@gmail.com)"
)

RATE_LIMIT_SECONDS = 1.0          # ~1 request/second
REQUEST_TIMEOUT_SECONDS = 30.0

# Exponential backoff on 429 / 5xx.
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0        # 2, 4, 8, 16
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# Shopify paginates; 250 is the max page size it honours.
PAGE_SIZE = 250

# --- Paths --------------------------------------------------------------------
# Repo root is the parent of this package.
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Output files.
PRODUCTS_CSV = DATA_DIR / "competitor_products.csv"
PRODUCTS_JSONL = DATA_DIR / "competitor_products.jsonl"
COLLECTIONS_CSV = DATA_DIR / "competitor_collections.csv"
