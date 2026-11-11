"""Три подхода к сайтам, где данные подгружает JavaScript.

1. pages   — данные рисует JS, переходим по кнопке «Next».
2. scroll  — бесконечная прокрутка: листаем вниз, пока появляются новые элементы.
3. network — перехватываем JSON-ответы внутреннего API сайта: быстрее и надёжнее,
             чем разбирать HTML, и не ломается при смене вёрстки.
"""

import asyncio
import json
import logging

from playwright.async_api import Page, Response

from dynscraper.models import Quote, clean

log = logging.getLogger(__name__)

EXTRACT_JS = """
els => els.map(el => ({
    text: el.querySelector('.text')?.innerText ?? '',
    author: el.querySelector('.author')?.innerText ?? '',
    tags: [...el.querySelectorAll('.tag')].map(t => t.innerText),
}))
"""


async def extract_quotes(page: Page) -> list[Quote]:
    raw = await page.eval_on_selector_all(".quote", EXTRACT_JS)
    return [
        Quote(clean(r["text"]), r["author"].strip(), tuple(r["tags"])) for r in raw if r["text"]
    ]


def _dedupe(items: list[Quote]) -> list[Quote]:
    seen, out = set(), []
    for q in items:
        key = (q.text, q.author)
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out


async def scrape_paginated(page: Page, url: str, max_pages: int | None = None) -> list[Quote]:
    await page.goto(url)
    results: list[Quote] = []
    page_no = 0
    while True:
        page_no += 1
        await page.wait_for_selector(".quote")
        quotes = await extract_quotes(page)
        log.info("Страница %s: %s элементов", page_no, len(quotes))
        results.extend(quotes)
        next_link = page.locator("li.next a")
        if (max_pages and page_no >= max_pages) or await next_link.count() == 0:
            break
        async with page.expect_navigation():
            await next_link.click()
    return _dedupe(results)


async def scrape_infinite_scroll(
    page: Page,
    url: str,
    max_items: int | None = None,
    idle_rounds: int = 3,
    pause: float = 0.6,
) -> list[Quote]:
    """Прокручиваем, пока количество элементов растёт. Если idle_rounds раз подряд
    ничего не добавилось — считаем, что дошли до конца."""
    await page.goto(url)
    await page.wait_for_selector(".quote")
    count, idle = 0, 0
    while idle < idle_rounds:
        await page.mouse.wheel(0, 20000)
        await asyncio.sleep(pause)
        new_count = await page.locator(".quote").count()
        if new_count > count:
            log.info("Загружено элементов: %s", new_count)
            count, idle = new_count, 0
        else:
            idle += 1
        if max_items and count >= max_items:
            break
    quotes = _dedupe(await extract_quotes(page))
    return quotes[:max_items] if max_items else quotes


async def scrape_via_network(
    page: Page,
    url: str,
    api_part: str = "/api/quotes",
    max_items: int | None = None,
    idle_rounds: int = 3,
    pause: float = 0.6,
) -> list[Quote]:
    """Слушаем ответы сервера и забираем данные прямо из JSON."""
    collected: list[Quote] = []
    finished = asyncio.Event()

    async def on_response(response: Response) -> None:
        if api_part not in response.url or response.status != 200:
            return
        try:
            data = json.loads(await response.text())
        except Exception:
            log.warning("Не удалось разобрать ответ %s", response.url)
            return
        collected.extend(Quote.from_api(item) for item in data.get("quotes", []))
        if not data.get("has_next", True):
            finished.set()

    page.on("response", on_response)
    await page.goto(url)
    idle, last = 0, -1
    while not finished.is_set() and idle < idle_rounds:
        if max_items and len(collected) >= max_items:
            break
        await page.mouse.wheel(0, 20000)
        await asyncio.sleep(pause)
        if len(collected) == last:
            idle += 1
        else:
            idle, last = 0, len(collected)
    await asyncio.sleep(pause)  # дождаться последнего ответа
    quotes = _dedupe(collected)
    return quotes[:max_items] if max_items else quotes
