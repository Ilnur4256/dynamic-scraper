import csv
import json

import pytest
import pytest_asyncio

from dynscraper import strategies
from dynscraper.browser import open_page
from dynscraper.export import save
from dynscraper.models import Quote, clean
from tests.fake_site import BASE, TOTAL, handler


@pytest_asyncio.fixture
async def page():
    async with open_page() as p:
        await p.route(f"{BASE}/**", handler)
        yield p


async def test_paginated(page):
    quotes = await strategies.scrape_paginated(page, f"{BASE}/js/")
    assert len(quotes) == TOTAL
    assert quotes[0] == Quote("Quote number 0", "Author 0", ("t0",))


async def test_paginated_max_pages(page):
    assert len(await strategies.scrape_paginated(page, f"{BASE}/js/", max_pages=2)) == 20


async def test_infinite_scroll(page):
    quotes = await strategies.scrape_infinite_scroll(page, f"{BASE}/scroll", pause=0.2)
    assert len(quotes) == TOTAL
    assert quotes[-1].text == "Quote number 24"


async def test_infinite_scroll_limit(page):
    quotes = await strategies.scrape_infinite_scroll(
        page, f"{BASE}/scroll", max_items=12, pause=0.2
    )
    assert len(quotes) == 12


async def test_network_interception(page):
    quotes = await strategies.scrape_via_network(page, f"{BASE}/scroll", pause=0.2)
    assert len(quotes) == TOTAL
    assert {q.author for q in quotes} == {"Author 0", "Author 1", "Author 2"}


def test_clean_and_from_api():
    assert clean("  “Hello” ") == "Hello"
    q = Quote.from_api({"text": "“Hi”", "author": {"name": "A"}, "tags": ["x"]})
    assert q == Quote("Hi", "A", ("x",))


def test_export(tmp_path):
    quotes = [Quote("Привет", "Автор", ("a", "b"))]
    save(quotes, tmp_path / "q.json")
    assert json.loads((tmp_path / "q.json").read_text(encoding="utf-8"))[0]["tags"] == ["a", "b"]
    save(quotes, tmp_path / "q.csv")
    with (tmp_path / "q.csv").open(encoding="utf-8-sig") as f:
        assert list(csv.reader(f))[1] == ["Привет", "Автор", "a, b"]
    with pytest.raises(ValueError):
        save(quotes, tmp_path / "q.txt")
