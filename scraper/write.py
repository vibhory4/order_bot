"""WRITE layer — serialize validated models to CSV and JSONL.

Nested fields (variants, tags, image_urls) are JSON-encoded into single CSV
cells so the CSV stays flat and round-trippable; the JSONL keeps full structure.
"""
from __future__ import annotations

import csv
import json

from . import config
from .models import CompetitorCollection, CompetitorProduct

_PRODUCT_COLUMNS = [
    "source", "url", "product_name", "description", "meta_title", "meta_description",
    "handle", "category", "subcategory", "price", "variant_sizes_prices", "tags",
    "product_type", "image_urls", "scraped_at",
]
_COLLECTION_COLUMNS = [
    "source", "title", "meta_title", "meta_description", "handle", "product_count",
]


def _product_row(p: CompetitorProduct) -> dict:
    d = p.model_dump(mode="json")
    # Flatten list/dict fields into JSON strings for CSV.
    d["variant_sizes_prices"] = json.dumps(d["variant_sizes_prices"], ensure_ascii=False)
    d["tags"] = json.dumps(d["tags"], ensure_ascii=False)
    d["image_urls"] = json.dumps(d["image_urls"], ensure_ascii=False)
    return d


def write_products_csv(products: list[CompetitorProduct]) -> None:
    config.PRODUCTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with config.PRODUCTS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_PRODUCT_COLUMNS)
        writer.writeheader()
        for p in products:
            writer.writerow(_product_row(p))


def write_products_jsonl(products: list[CompetitorProduct]) -> None:
    config.PRODUCTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with config.PRODUCTS_JSONL.open("w", encoding="utf-8") as fh:
        for p in products:
            fh.write(json.dumps(p.model_dump(mode="json"), ensure_ascii=False) + "\n")


def write_collections_csv(collections: list[CompetitorCollection]) -> None:
    config.COLLECTIONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with config.COLLECTIONS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLLECTION_COLUMNS)
        writer.writeheader()
        for c in collections:
            writer.writerow(c.model_dump(mode="json"))
