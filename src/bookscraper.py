from bs4 import BeautifulSoup
import asyncio
from basescraper import BaseScraper
import csv


def save_csv(data, filename="books.csv"):
    keys = data.keys()
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)


class BookScraper(BaseScraper):
    BASE_URL = "https://books.toscrape.com/catalogue/page-{}.html"
    TOTAL_PAGES = 50

    def parse(self, html):
        return BeautifulSoup(html, "html.parser")

    def extract_items(self, tree):
        books = []

        cards = tree.select("article.product_pod")

        for card in cards:
            title = card.select_one("img")["alt"]
            price = card.select_one(".price_color")

            books.append(
                {
                    "title": title if title else "",
                    "price": price.text.strip() if price else "",
                }
            )

        return books


async def main():
    scraper = BookScraper(batch_size=5)
    books = await scraper.scrape_all()
    books_list = [dict(book) for book in books]
    print(books)
    save_csv(data=books_list, filename="data/books.csv")
    print(f"Collected {len(books)} books")


asyncio.run(main())
