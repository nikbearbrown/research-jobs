#!/usr/bin/env python3
"""Crawl Mass General Brigham's institutes/centers/labs search
(research.massgeneralbrigham.org) into a raw list of result tiles.

The search is a Coveo widget that only renders in a browser, 50 tiles per
page with a "Next" button. This drives it with Playwright, reads each page's
tiles (entity type tag, name, detail-page URL, one-line blurb), waits 1s
between pages, and writes everything to data/raw/mgb-search-<date>.json.

Usage: .venv/bin/python scripts/crawl_mgb_labs.py
"""
import datetime
import json
import time
from pathlib import Path

from fetch import USER_AGENT

ROOT = Path(__file__).resolve().parent.parent
URL = "https://research.massgeneralbrigham.org/en/institutes-centers/institutes-centers-search-results?q=all"

READ_TILES = """() => [...document.querySelectorAll('.site-result-tile')].map(t => {
  const a = t.querySelector('a.site-result-tile-name');
  return {
    type: [...t.querySelectorAll('ol li')].map(li => li.innerText.trim()).join('; '),
    name: a ? a.innerText.trim() : null,
    url: a ? a.href : null,
    blurb: (t.querySelector('p') || {}).innerText || null,
  };
})"""


def main():
    from playwright.sync_api import sync_playwright

    tiles, seen_pages = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_selector(".site-result-tile", timeout=30000)
        total_text = page.locator("text=/\\d+ results/").first.inner_text()
        while True:
            batch = page.evaluate(READ_TILES)
            seen_pages += 1
            tiles += batch
            print(f"page {seen_pages}: {len(batch)} tiles (total {len(tiles)})", flush=True)
            nxt = page.locator("button.pagination-next-button")
            if nxt.count() == 0 or nxt.first.is_disabled():
                break
            first_before = batch[0]["url"] if batch else None
            nxt.first.click()
            for _ in range(30):
                time.sleep(1)
                now = page.evaluate(READ_TILES)
                if now and now[0]["url"] != first_before:
                    break
            else:
                break  # page didn't change: last page
        browser.close()

    uniq = list({t["url"]: t for t in tiles if t["url"]}.values())
    out = ROOT / "data" / "raw" / f"mgb-search-{datetime.date.today().isoformat()}.json"
    out.write_text(json.dumps({"source": URL, "reported_total": total_text, "pages": seen_pages,
                               "tiles": uniq}, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(uniq)} unique tiles -> {out}")


if __name__ == "__main__":
    main()
