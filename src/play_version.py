import asyncio
import csv
from playwright.async_api import async_playwright
from selectolax.lexbor import LexborHTMLParser


class BooksScraper:
    BASE_URL = "http://books.toscrape.com/catalogue/page-{}.html"

    # ---------- Parsing ----------
    def parse(self, html: str) -> LexborHTMLParser:
        return LexborHTMLParser(html)

    async def scrape_page(self, page, url):
        await page.goto(url)
        await page.wait_for_timeout(500)

        html = await page.content()
        tree = self.parse(html)

        return self.extract_books(tree)

    def extract_books(self, tree: LexborHTMLParser) -> list:
        books = []

        items = tree.css("article.product_pod")

        for item in items:
            title = item.css_first("h3 a").attributes["title"]
            price = item.css_first(".price_color").text(strip=True)
            rating = item.css_first("p.star-rating").attributes["class"].split()[-1]

            books.append({"title": title, "price": price, "rating": rating})

        return books

    # ---------- Scraping ----------
    async def scrape_all(self, batch_size=5):
        all_books = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            page_num = 1

            while True:
                print(f"\nScraping pages {page_num} → {page_num + batch_size - 1}")

                # Create tabs
                pages = [await browser.new_page() for _ in range(batch_size)]

                tasks = []

                for i, page in enumerate(pages):
                    url = self.BASE_URL.format(page_num + i)
                    tasks.append(self.scrape_page(page, url))

                results = await asyncio.gather(*tasks)

                # Close tabs
                for page in pages:
                    await page.close()

                # Flatten results
                batch_books = [book for page_books in results for book in page_books]

                # Stop condition
                if not batch_books:
                    print("No more books found. Stopping.")
                    break

                all_books.extend(batch_books)
                page_num += batch_size

            await browser.close()

        return all_books

    # ---------- Export ----------
    def save_csv(self, data, filename="books.csv"):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "price", "rating"])
            writer.writeheader()
            writer.writerows(data)

        print(f"\nSaved {len(data)} books to {filename}")


async def main():
    scraper = BooksScraper()
    books = await scraper.scrape_all()
    scraper.save_csv(books)


asyncio.run(main())
