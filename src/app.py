import asyncio
import httpx
import csv
from selectolax.lexbor import LexborHTMLParser


BASE_URL = "https://www.sportsmans.com/c/cat139633-hpf-pistols?q=%3Arelevance&page={}"


async def fetch(client, url: str) -> httpx.Response:
    return await client.get(url)


def parse(response: httpx.Response) -> LexborHTMLParser:
    return LexborHTMLParser(response.text)


def gather_info(html_parser: LexborHTMLParser) -> list:
    conts = html_parser.css("div.product-item.js-product-item")

    results = []

    for cont in conts:
        name_node = cont.css_first("a")
        price_node = cont.css_first(".smw-sale-price.displayed-price")

        results.append(
            {
                "name": name_node.text(strip=True) if name_node else None,
                "price": price_node.text(strip=True) if price_node else None,
            }
        )

    return results


async def scrape_all_pages():
    all_items = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            url = BASE_URL.format(page)
            print(f"Scraping page {page}...")

            response = await fetch(client, url)
            tree = parse(response)
            items = gather_info(tree)

            if not items:
                print("No more products found. Stopping.")
                break

            all_items.extend(items)
            page += 1

    return all_items


def save_to_csv(data, filename="products.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "price"])
        writer.writeheader()
        writer.writerows(data)

    print(f"Saved {len(data)} items to {filename}")


async def main():
    products = await scrape_all_pages()
    save_to_csv(products)


asyncio.run(main())
