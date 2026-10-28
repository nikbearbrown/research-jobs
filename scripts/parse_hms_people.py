#!/usr/bin/env python3
"""Parser for the Harvard Medical School Drupal "faculty_long_card" people
directory template, shared across many *.hms.harvard.edu department sites
(confirmed on bcmp, cellbio, dbmi, genetics, ghsm, hcp).

Usage (library):
    from parse_hms_people import fetch_all_people
    people = fetch_all_people("https://bcmp.hms.harvard.edu/people")
    # -> list of dicts: name, title, phone, email, lab_website, profile_url

Paginates via ?page=N until a page returns 0 cards or returns fewer cards
than the first page (last page). Each site's fetch is cached by fetch.py
as usual, so reruns are free.
"""
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402


def _parse_cards(html, base_url):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    people = []
    for card in soup.select("div.views-row"):
        name_a = card.select_one("p.leadership--name a")
        if not name_a:
            continue
        name = name_a.get_text(" ", strip=True)
        profile_url = urllib.parse.urljoin(base_url, name_a.get("href", ""))
        title_div = card.select_one("div.leadership--position")
        title = title_div.get_text(" ", strip=True) if title_div else None
        phone_a = card.select_one("div.leadership--phone a")
        phone = phone_a.get_text(" ", strip=True) if phone_a else None
        email_a = card.select_one("div.leadership--email a[href^='mailto:']")
        email = email_a["href"][7:].split("?")[0].strip() if email_a else None
        site_a = card.select_one("div.leadership--site a")
        lab_website = site_a.get("href") if site_a else None
        people.append({
            "name": name,
            "title": title,
            "phone": phone,
            "email": email,
            "lab_website": lab_website,
            "profile_url": profile_url,
        })
    return people


def fetch_all_people(people_url, render=False, max_pages=30):
    """Fetch page 0 (the bare people_url) then ?page=1, 2, ... until done.
    Returns (people, fetched_urls)."""
    all_people = []
    fetched_urls = []
    seen_urls = set()
    first_page_count = None
    for page in range(max_pages):
        url = people_url if page == 0 else f"{people_url}?page={page}"
        result = fetch(url, render=render)
        if not result["html"]:
            break
        fetched_urls.append(url)
        people = _parse_cards(result["html"], url)
        if page == 0:
            first_page_count = len(people)
        if not people:
            break
        new = [p for p in people if p["profile_url"] not in seen_urls]
        for p in new:
            seen_urls.add(p["profile_url"])
        all_people.extend(new)
        if first_page_count and len(people) < first_page_count:
            break  # short page = last page
    return all_people, fetched_urls


if __name__ == "__main__":
    import json

    url = sys.argv[1]
    people, fetched_urls = fetch_all_people(url)
    print(json.dumps({"people": people, "fetched_urls": fetched_urls}, indent=2))
    print(f"\n# {len(people)} people total across {len(fetched_urls)} pages", file=sys.stderr)
