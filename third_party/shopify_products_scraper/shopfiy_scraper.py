# Vendored from: https://github.com/grabowskiadrian/shopify-products-scraper
#   file: shopfiy_scraper.py  (upstream filename preserved, sic)
#   upstream license: NONE STATED — see ./NOTICE. Retained for research use only.
#
# Local modifications (minimal "politeness" layer; behaviour & output columns unchanged):
#   * all HTTP goes through a shared requests.Session with a descriptive research User-Agent
#   * a per-request timeout and a ~1 request/second throttle
#   * per-product errors are logged and skipped instead of crashing the whole run
# Modified lines are marked with:  # [politeness]
import csv
import time  # [politeness]
import sys  # [politeness]
import argparse

import requests  # [politeness] (replaces urllib.request for all fetches)
import pandas as pd
from bs4 import BeautifulSoup

# --- politeness configuration ------------------------------------------------
USER_AGENT = (
    "ShopifyResearchBot/1.0 (+competitive product research; non-commercial; "
    "contact: vibhugupta97@gmail.com)"
)  # [politeness]
RATE_LIMIT_SECONDS = 1.0  # ~1 req/s  # [politeness]
REQUEST_TIMEOUT_SECONDS = 30.0  # [politeness]

SESSION = requests.Session()  # [politeness]
SESSION.headers.update({"User-Agent": USER_AGENT})  # [politeness]
_last_request_at = 0.0  # [politeness]


def _get(target):  # [politeness]
    """Throttled GET through the shared session, with timeout and a descriptive UA."""
    global _last_request_at
    wait = RATE_LIMIT_SECONDS - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()
    resp = SESSION.get(target, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp


parser = argparse.ArgumentParser(description="Scrap products data from Shopify store")
parser.add_argument('-t', '--target', dest='website_url', type=str, help='URL to Shopify store (https://shopifystore.com)')
parser.add_argument('-v', '--variants', dest='variants',  action="store_true", help='Scrap also with variants data')
args = parser.parse_args()

if not args.website_url:
    print("usage: shopfiy_scraper.py [-h] [-t WEBSITE_URL] [-v]")
    exit(0)

base_url = args.website_url
url = base_url + '/products.json'

with_variants = args.variants


def get_page(page):
    resp = _get(url + '?page={}'.format(page))  # [politeness]
    products = resp.json()['products']  # [politeness]

    return products


def safe_get_page(page):  # [politeness] clean exit instead of a raw traceback
    try:
        return get_page(page)
    except requests.RequestException as exc:
        print("[!] aborting: request failed on page {} for {} ({})".format(page, base_url, exc),
              file=sys.stderr)
        sys.exit(1)


def get_tags_from_product(product):
    r = _get(product).content  # [politeness]
    soup = BeautifulSoup(r, "html.parser")

    title = soup.title.string if soup.title else ''  # [politeness] guard against missing <title>
    description = ''

    meta = soup.find_all('meta')
    for tag in meta:
        if 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() == 'description':
            description = tag.attrs['content'];

    return [title, description]

def get_inventory_from_product(product_url):
    get_product = _get(product_url)  # [politeness]
    product_json = get_product.json()
    product_variants = pd.DataFrame(product_json['product']['variants'])

    return product_variants


with open('products.csv', 'w') as f:
    page = 1

    print("[+] Starting script")

    # create file header
    writer = csv.writer(f)
    if with_variants:
        writer.writerow([
            'Name', 'Variant ID', 'Product ID', 'Variant Title', 'Price', 'SKU',
            'Position', 'Inventory Policy', 'Compare At Price', 'Fulfillment Service',
            'Inventory Management', 'Option1', 'Option2', 'Option3', 'Created At',
            'Updated At', 'Taxable', 'Barcode', 'Grams', 'Image ID', 'Weight',
            'Weight Unit', 'Inventory Quantity', 'Old Inventory Quantity',
            'Tax Code', 'Requires Shipping', 'Quantity Rule', 'Price Currency',
            'Compare At Price Currency', 'Quantity Price Breaks',
            'URL', 'Meta Title', 'Meta Description', 'Product Description'
        ])
    else:
        writer.writerow(['Name', 'URL', 'Meta Title', 'Meta Description', 'Product Description'])

    print("[+] Checking products page")

    products = safe_get_page(page)
    while products:
        for product in products:
            product_url = base_url + '/products/' + product.get('handle', '')  # [politeness]
            try:  # [politeness] one bad product must not crash the whole run
                name = product['title']
                category = product['product_type']

                body_description = BeautifulSoup(product.get('body_html') or '', "html.parser")
                body_description = body_description.get_text()

                print(" ├ Scraping: " + product_url)

                title, description = get_tags_from_product(product_url)

                if with_variants:
                    variants_df = get_inventory_from_product(product_url + '.json')
                    for _, variant in variants_df.iterrows():
                        row = [
                            name, variant['id'], variant['product_id'], variant['title'],
                            variant['price'], variant['sku'], variant['position'],
                            variant['inventory_policy'], variant['compare_at_price'],
                            variant['fulfillment_service'], variant['inventory_management'],
                            variant['option1'], variant['option2'], variant['option3'],
                            variant['created_at'], variant['updated_at'], variant['taxable'],
                            variant['barcode'], variant['grams'], variant['image_id'],
                            variant['weight'], variant['weight_unit'], variant['inventory_quantity'],
                            variant['old_inventory_quantity'], variant['tax_code'],
                            variant['requires_shipping'], variant['quantity_rule'],
                            variant['price_currency'], variant['compare_at_price_currency'],
                            variant['quantity_price_breaks'],
                            product_url, title, description, body_description
                        ]
                        writer.writerow(row)
                else:
                    row = [name, product_url, title, description, body_description]
                    writer.writerow(row)
            except Exception as exc:  # [politeness]
                print(" ├ ! skipping {} ({})".format(product_url, exc), file=sys.stderr)
                continue
        page += 1
        products = safe_get_page(page)
