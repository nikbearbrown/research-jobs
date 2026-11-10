#!/usr/bin/env python3
"""Fill profile_url for UMass Boston labs from the department listing pages.

The breadth pass (parse_umb_people.py) read each Faculty & Staff page as text,
so it never saw that every name on the page links to that person's own
umb.edu/directory/<slug>/ page. This reads the same listing pages again as
HTML and records that link as profile_url, matching by name. Nothing else is
changed; `depth_pass.py emails` and `depth_pass.py sites` then read the
profile pages for an email and a lab website.

    python3 scripts/umb_profiles.py [--dry-run]
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from depth_pass import append_note, fold, name_parts, save  # noqa: E402
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def key(name):
    first, last, _ = name_parts(name)
    return (first, last) if first else None


def directory_links(url):
    """{(first, last): profile url} for every name linked to /directory/<slug>/ on a listing page."""
    from bs4 import BeautifulSoup

    res = fetch(url)
    out, clash = {}, set()
    if not res.get("html"):
        return out, res["status"]
    for a in BeautifulSoup(res["html"], "lxml").find_all("a", href=True):
        if not re.match(r"^/directory/[^/]+/?$", urllib.parse.urlsplit(a["href"]).path):
            continue
        name = a.get_text(" ", strip=True)
        k = key(name) if name else None
        if not k:
            continue
        absu = urllib.parse.urljoin(url, a["href"]).split("#")[0]
        if k in out and out[k] != absu:
            clash.add(k)  # two different people with the same first and last name: match neither
        out[k] = absu
    for k in clash:
        out.pop(k, None)
    return out, res["status"]


def main():
    dry = "--dry-run" in sys.argv
    filled = missing = 0
    paths = sorted((ROOT / "data" / "sources").glob("umass-boston-*.json"))
    per_file, everywhere = {}, {}
    for path in paths:
        links = {}
        for url in json.loads(path.read_text()).get("listing_urls") or []:
            found, status = directory_links(url)
            links.update(found)
        per_file[path] = links
        everywhere.update(links)
    for path in paths:
        data = json.loads(path.read_text())
        links = per_file[path]
        changed = False
        for lab in data["labs"]:
            if lab.get("kind") != "research-lab" or lab.get("profile_url"):
                continue
            k = key(lab.get("pi_name") or "")
            url = links.get(k)
            # centers list people whose directory link is on their home department's page
            where = "the department listing page" if url else "another UMass Boston department's listing page"
            url = url or everywhere.get(k)
            if url:
                lab["profile_url"] = url
                append_note(lab, f"profile_url read from the name link on {where}.")
                filled += 1
                changed = True
            else:
                missing += 1
                print(f"-- no directory link for {lab['id']}", flush=True)
        print(f"{path.name}: {len(links)} directory links on the listing page(s)", flush=True)
        if changed and not dry:
            save(path, data)
    print(f"umb_profiles: filled {filled}, no link found {missing}" + (" (dry run)" if dry else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
