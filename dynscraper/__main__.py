"""python -m dynscraper --mode network --out quotes.csv"""

import argparse
import asyncio
import logging
import sys
import time
from collections import Counter
from pathlib import Path

from dynscraper import strategies
from dynscraper.browser import open_page
from dynscraper.export import save

DEFAULT_URLS = {
    "pages": "https://quotes.toscrape.com/js/",
    "scroll": "https://quotes.toscrape.com/scroll",
    "network": "https://quotes.toscrape.com/scroll",
}


async def run(args) -> int:
    url = args.url or DEFAULT_URLS[args.mode]
    started = time.monotonic()
    async with open_page(headless=not args.show) as page:
        try:
            if args.mode == "pages":
                quotes = await strategies.scrape_paginated(page, url, args.max_pages)
            elif args.mode == "scroll":
                quotes = await strategies.scrape_infinite_scroll(page, url, args.max_items)
            else:
                quotes = await strategies.scrape_via_network(page, url, max_items=args.max_items)
        except Exception:
            # Скриншот страницы в момент ошибки сильно упрощает отладку
            await page.screenshot(path="error.png", full_page=True)
            logging.exception("Ошибка; скриншот сохранён в error.png")
            return 1
    took = time.monotonic() - started
    print(f"Собрано: {len(quotes)} за {took:.1f} с ({args.mode})")
    top = Counter(q.author for q in quotes).most_common(3)
    if top:
        print("Чаще всего встречаются:", ", ".join(f"{a} ({n})" for a, n in top))
    if args.out:
        save(quotes, args.out)
        print(f"Сохранено: {args.out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="dynscraper", description="Парсер JS-сайтов на Playwright")
    p.add_argument("--mode", choices=["pages", "scroll", "network"], default="network")
    p.add_argument("--url")
    p.add_argument("--out", type=Path)
    p.add_argument("--max-pages", type=int)
    p.add_argument("--max-items", type=int)
    p.add_argument("--show", action="store_true", help="Показать окно браузера")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
