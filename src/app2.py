import asyncio
import httpx
import csv
from selectolax.lexbor import LexborHTMLParser


class SportsmansScraper:
    BASE_URL = (
        "https://www.sportsmans.com/c/cat139633-hpf-pistols?q=%3Arelevance&page={}"
    )

    def __init__(self, timeout=30, max_concurrency=3):
        self.timeout = timeout
        self.client = None
        self.semaphore = asyncio.Semaphore(max_concurrency)

    # ---------- Context Manager ----------
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.aclose()

    # ---------- Network ----------
    async def fetch(self, url: str) -> httpx.Response:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        }

        async with self.semaphore:
            for attempt in range(3):
                try:
                    response = await self.client.get(url, headers=headers)

                    if response.status_code == 200:
                        await asyncio.sleep(1)  # <-- KEY anti-block delay
                        return response

                except httpx.RequestError:
                    pass

                await asyncio.sleep(2 * (attempt + 1))

        raise Exception("Failed after retries")

    # ---------- Parsing ----------
    def parse(self, html: str) -> LexborHTMLParser:
        return LexborHTMLParser(html)

    def extract_products(self, tree: LexborHTMLParser) -> list:
        print(tree.html[:500])
        products = []

        items = tree.css("div.product-tile")

        for item in items:
            name_node = item.css_first(".product-item")
            price_node = item.css_first(".smw-sale-price.displayed-price")

            products.append(
                {
                    "name": name_node.text(strip=True) if name_node else None,
                    "price": price_node.text(strip=True) if price_node else None,
                }
            )

        return products

    # ---------- Pagination ----------
    async def scrape_page(self, page: int) -> list:
        url = self.BASE_URL.format(page)

        response = await self.fetch(url)

        print("STATUS:", response.status_code)
        print("LENGTH:", len(response.text))
        print("FIRST 300 CHARS:")
        print(response.text[:300])
        print("-" * 40)

        tree = self.parse(response.text)

        return self.extract_products(tree)

    async def scrape_all(self, batch_size=3):
        page = 1
        all_products = []

        while True:
            print(f"Scraping pages {page} → {page + batch_size - 1}")

            tasks = [self.scrape_page(p) for p in range(page, page + batch_size)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            batch = []
            for r in results:
                if isinstance(r, list):
                    batch.extend(r)

            if not batch:
                print("No more pages found.")
                break

            all_products.extend(batch)
            page += batch_size

            # VERY important pause between bursts
            await asyncio.sleep(2)

        return all_products

    # ---------- Export ----------
    def save_csv(self, data, filename="products.csv"):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "price"])
            writer.writeheader()
            writer.writerows(data)

        print(f"Saved {len(data)} products to {filename}")


async def main():
    async with SportsmansScraper() as scraper:
        products = await scraper.scrape_all(batch_size=3)
        scraper.save_csv(products)


asyncio.run(main())
