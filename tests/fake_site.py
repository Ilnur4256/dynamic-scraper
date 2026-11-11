"""Мини-сайт для тестов: страницы отдаются через page.route, без сети и без сервера."""

import json

from playwright.async_api import Route

BASE = "http://fake.test"
TOTAL = 25  # всего элементов на «сайте»
PER_PAGE = 10


def item(i: int) -> dict:
    return {
        "text": f"“Quote number {i}”",
        "author": {"name": f"Author {i % 3}"},
        "tags": [f"t{i % 2}"],
    }


def api_page(n: int) -> dict:
    start = (n - 1) * PER_PAGE
    items = [item(i) for i in range(start, min(start + PER_PAGE, TOTAL))]
    return {"page": n, "has_next": start + PER_PAGE < TOTAL, "quotes": items}


RENDER_JS = """
function render(qs) {
  const box = document.querySelector('.quotes');
  for (const q of qs) {
    const d = document.createElement('div');
    d.className = 'quote';
    d.innerHTML = `<span class="text">${q.text}</span><small class="author">${q.author.name}</small>`
      + q.tags.map(t => `<a class="tag">${t}</a>`).join('');
    box.appendChild(d);
  }
}
"""


def js_page(n: int) -> str:
    data = json.dumps(api_page(n)["quotes"])
    nxt = (
        f'<ul><li class="next"><a href="/js/page/{n + 1}/">Next</a></li></ul>'
        if api_page(n)["has_next"]
        else ""
    )
    return f"<html><body><div class='quotes'></div>{nxt}<script>{RENDER_JS} render({data});</script></body></html>"


SCROLL_PAGE = f"""<html><body style="margin:0"><div class='quotes'></div>
<div style="height:3000px"></div>
<script>{RENDER_JS}
let page = 1, loading = false, hasNext = true;
async function load() {{
  if (loading || !hasNext) return;
  loading = true;
  const r = await fetch('/api/quotes?page=' + page);
  const data = await r.json();
  render(data.quotes); hasNext = data.has_next; page += 1; loading = false;
}}
window.addEventListener('scroll', load);
load();
</script></body></html>"""


async def handler(route: Route) -> None:
    url = route.request.url
    if "/api/quotes" in url:
        n = int(url.split("page=")[1])
        await route.fulfill(json=api_page(n))
    elif "/js/page/" in url:
        n = int(url.rstrip("/").split("/")[-1])
        await route.fulfill(body=js_page(n), content_type="text/html")
    elif url.rstrip("/").endswith("/js"):
        await route.fulfill(body=js_page(1), content_type="text/html")
    elif "/scroll" in url:
        await route.fulfill(body=SCROLL_PAGE, content_type="text/html")
    else:
        await route.fulfill(status=404, body="not found")
