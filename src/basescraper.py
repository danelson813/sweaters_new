import asyncio
import csv
from tqdm.asyncio import tqdm
from playwright.async_api import async_playwright


class BaseScraper:
    BASE_URL = ""
    TOTAL_PAGES = 1

    def __init__(self, batch_size=5, headless=True):
        self.batch_size = batch_size
        self.headless = headless

    # ----------------------------
    # METHODS CHILD CLASSES OVERRIDE
    # ----------------------------

    def parse(self, html):
        raise NotImplementedError

    def extract_items(self, tree):
        raise NotImplementedError

    # ----------------------------
    # INTERNAL ENGINE
    # ----------------------------

    async def scrape_page(self, page, url):
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(500)

            html = await page.content()
            tree = self.parse(html)

            return self.extract_items(tree)

        except Exception as e:
            print(f"Failed: {url} → {e}")
            return []

    # ----------------------------
    # MAIN SCRAPER LOOP
    # ----------------------------

    async def scrape_all(self):
        all_items = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            page_num = 1

            with tqdm(total=self.TOTAL_PAGES, desc="Scraping") as pbar:
                while page_num <= self.TOTAL_PAGES:
                    pages = [await browser.new_page() for _ in range(self.batch_size)]
                    tasks = []

                    for i, page in enumerate(pages):
                        current_page = page_num + i
                        if current_page > self.TOTAL_PAGES:
                            break

                        url = self.BASE_URL.format(current_page)
                        tasks.append(self.scrape_page(page, url))

                    results = await asyncio.gather(*tasks)

                    # Close tabs
                    for page in pages:
                        await page.close()

                    # Flatten results
                    batch_items = [i for sub in results for i in sub]
                    all_items.extend(batch_items)

                    pbar.update(len(results))
                    page_num += self.batch_size

            await browser.close()

        return all_items

    def save_csv(self, data, filename="data/books.csv"):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "price"])
            writer.writeheader()
            writer.writerows(data)
