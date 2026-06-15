"""CLI entrypoint: orchestrate fetch → parse → validate → write, print a summary.

Usage:
    python -m scraper.run --source cremecastle              # live crawl
    python -m scraper.run --source cremecastle --fixtures   # offline dry-run
"""
from __future__ import annotations

import argparse
import logging

from . import validate, write
from .sources import cremecastle

log = logging.getLogger("scraper")

SOURCE_CRAWLERS = {
    "cremecastle": cremecastle.crawl,
}


def run(source: str, fixtures: bool) -> None:
    crawl = SOURCE_CRAWLERS[source]
    log.info("crawling %s%s", source, " (fixtures)" if fixtures else "")

    product_rows, collection_rows = crawl(fixtures=fixtures)

    products, product_failures = validate.validate_products(product_rows)
    collections, collection_failures = validate.validate_collections(collection_rows)

    write.write_products_csv(products)
    write.write_products_jsonl(products)
    write.write_collections_csv(collections)

    failures = product_failures + collection_failures
    print(
        f"[{source}] collections={len(collections)} "
        f"products={len(products)} validation_failures={failures} "
        f"(product_failures={product_failures}, collection_failures={collection_failures})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Competitive-research cake-site scraper.")
    parser.add_argument(
        "--source", choices=sorted(SOURCE_CRAWLERS), default="cremecastle",
        help="which site to crawl (default: cremecastle)",
    )
    parser.add_argument(
        "--fixtures", action="store_true",
        help="offline dry-run against bundled sample JSON (no network)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    run(args.source, args.fixtures)


if __name__ == "__main__":
    main()
