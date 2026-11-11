from contextlib import asynccontextmanager

from playwright.async_api import Page, Route, async_playwright

# Картинки, шрифты и медиа для сбора данных не нужны — блокируем, страницы грузятся в разы быстрее
BLOCKED_RESOURCES = {"image", "media", "font"}


async def _block_heavy(route: Route) -> None:
    if route.request.resource_type in BLOCKED_RESOURCES:
        await route.abort()
    else:
        await route.continue_()


@asynccontextmanager
async def open_page(headless: bool = True, block_resources: bool = True, timeout_ms: int = 20000):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (compatible; dynamic-scraper/1.0; portfolio project)",
            locale="en-US",
        )
        context.set_default_timeout(timeout_ms)
        if block_resources:
            await context.route("**/*", _block_heavy)
        page: Page = await context.new_page()
        try:
            yield page
        finally:
            await browser.close()
