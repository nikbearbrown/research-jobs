#!/usr/bin/env python3
"""Polite fetcher with disk cache, robots.txt check, per-host rate limit,
and optional Playwright rendering for JS-heavy pages.

Usage:
    python3 scripts/fetch.py <url> [--render] [--force] [--text]

  --render   Always use Playwright (headless Chromium) instead of plain HTTP.
             Without this flag, fetch.py first tries a plain HTTP GET; if the
             returned HTML looks too thin (likely JS-rendered), it retries
             with Playwright automatically.
  --force    Refetch even if a cached copy exists.
  --text     Print extracted visible text (for reading) instead of raw HTML
             path. This is the default when run from the command line.
  --html     Print the path to the cached raw HTML file instead of text.

    python3 scripts/fetch.py --batch urls.txt [--render]

  Batch mode: fetch every URL in urls.txt (one per line) in one process, so
  the per-host rate limit and robots.txt cache are honoured across all of
  them. For each URL this also writes the extracted text to
  cache/_text/<host>/<slug>.txt (easy to Read afterwards) and prints a
  manifest line "<status>\t<method>\t<text-path-or-> \t<url>".

Cache layout: cache/<host>/<slug-of-path-and-query>.html
A sibling .meta.json records the url, fetch method and timestamp.

Library use:
    from fetch import fetch
    result = fetch(url)   # dict: html, text, cache_path, status, method
"""
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache"
USER_AGENT = "research-jobs-bot/0.1 (+https://github.com/nikbearbrown/research-jobs; contact: agents@humanitarians.ai)"
MIN_INTERVAL = 1.0  # seconds between requests to the same host
MIN_HTML_LEN_FOR_STATIC = 1500  # below this, suspect JS rendering is needed

_last_request_at = {}
_robots_cache = {}


def _slug_for(url):
    parsed = urllib.parse.urlsplit(url)
    path_q = (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", path_q).strip("-").lower()
    if not slug:
        slug = "index"
    if len(slug) > 120:
        slug = slug[:80] + "-" + hashlib.sha1(path_q.encode()).hexdigest()[:10]
    return slug


def _cache_paths(url):
    parsed = urllib.parse.urlsplit(url)
    host_dir = CACHE_DIR / parsed.netloc.lower()
    host_dir.mkdir(parents=True, exist_ok=True)
    slug = _slug_for(url)
    return host_dir / f"{slug}.html", host_dir / f"{slug}.meta.json"


def _respect_rate_limit(host):
    now = time.time()
    last = _last_request_at.get(host, 0)
    wait = MIN_INTERVAL - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request_at[host] = time.time()


def _robots_allowed(url):
    parsed = urllib.parse.urlsplit(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    rp = _robots_cache.get(base)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base + "/robots.txt")
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                rp.parse(resp.read().decode("utf-8", "replace").splitlines())
        except Exception:
            rp = None  # no robots.txt or unreadable -> treat as allowed
        _robots_cache[base] = rp
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)


def _fetch_http(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.status, resp.read().decode(charset, "replace")


def _fetch_playwright(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="networkidle", timeout=30000)
        html = page.content()
        browser.close()
        return 200, html


def html_to_text(html):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    mailtos = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            addr = href[7:].split("?")[0].strip()
            label = a.get_text(" ", strip=True)
            if addr:
                mailtos.append(f"{addr}  (link text: {label!r})" if label else addr)
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if mailtos:
        lines.append("")
        lines.append("--- mailto: links found on this page (match to the nearest name above) ---")
        seen = set()
        for m in mailtos:
            if m not in seen:
                seen.add(m)
                lines.append(m)
    return "\n".join(lines)


def fetch(url, render=False, force=False):
    """Fetch url with cache, robots check, rate limit. Returns a dict."""
    html_path, meta_path = _cache_paths(url)

    if not force and html_path.exists() and meta_path.exists():
        html = html_path.read_text(encoding="utf-8", errors="replace")
        meta = json.loads(meta_path.read_text())
        return {"html": html, "text": html_to_text(html), "cache_path": str(html_path),
                "status": meta.get("status"), "method": meta.get("method"), "cached": True, "url": url}

    if not _robots_allowed(url):
        meta = {"url": url, "status": "blocked-by-robots", "method": None, "fetched_at": time.time()}
        meta_path.write_text(json.dumps(meta, indent=2))
        return {"html": None, "text": None, "cache_path": None, "status": "blocked-by-robots",
                "method": None, "cached": False, "url": url}

    host = urllib.parse.urlsplit(url).netloc
    method = "playwright" if render else "http"
    status = None
    html = None

    if not render:
        _respect_rate_limit(host)
        try:
            status, html = _fetch_http(url)
            if html is None or len(html) < MIN_HTML_LEN_FOR_STATIC:
                method = "playwright"
                html = None
        except Exception as e:
            method = "playwright"
            html = None
            status = f"http-error: {e}"

    if html is None:
        _respect_rate_limit(host)
        try:
            status, html = _fetch_playwright(url)
        except Exception as e:
            status = f"playwright-error: {e}"
            html = None

    if html is not None:
        html_path.write_text(html, encoding="utf-8")
    meta = {"url": url, "status": status, "method": method, "fetched_at": time.time()}
    meta_path.write_text(json.dumps(meta, indent=2))

    text = html_to_text(html) if html else None
    return {"html": html, "text": text, "cache_path": str(html_path) if html else None,
            "status": status, "method": method, "cached": False, "url": url}


def _batch(urls_file, render, force):
    text_root = CACHE_DIR / "_text"
    for line in Path(urls_file).read_text().splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        result = fetch(url, render=render, force=force)
        if result["status"] == "blocked-by-robots":
            print(f"blocked-by-robots\t-\t-\t{url}")
            continue
        if result["text"] is None:
            print(f"{result['status']}\t{result['method']}\t-\t{url}")
            continue
        host = urllib.parse.urlsplit(url).netloc.lower()
        host_dir = text_root / host
        host_dir.mkdir(parents=True, exist_ok=True)
        text_path = host_dir / f"{_slug_for(url)}.txt"
        text_path.write_text(result["text"], encoding="utf-8")
        cached_flag = " (cached)" if result["cached"] else ""
        print(f"{result['status']}{cached_flag}\t{result['method']}\t{text_path}\t{url}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    render = "--render" in args
    force = "--force" in args

    if args[0] == "--batch":
        urls_file = args[1]
        _batch(urls_file, render=render, force=force)
        return

    url = args[0]
    want_html_path = "--html" in args

    result = fetch(url, render=render, force=force)
    if result["status"] == "blocked-by-robots":
        print(f"BLOCKED BY ROBOTS.TXT: {url}", file=sys.stderr)
        sys.exit(2)
    if result["html"] is None:
        print(f"FETCH FAILED ({result['status']}): {url}", file=sys.stderr)
        sys.exit(1)

    print(f"# fetched via {result['method']}{' (cached)' if result['cached'] else ''}: {url}", file=sys.stderr)
    if want_html_path:
        print(result["cache_path"])
    else:
        print(result["text"])


if __name__ == "__main__":
    main()
