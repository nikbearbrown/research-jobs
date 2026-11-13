#!/usr/bin/env python3
"""Fetch the pages a reader needs for each target and write a worklist.

For policy centers, think tanks, schools and social-science departments
(priority 2 and 3) the "lab" is the organization or program itself, so there
is no per-site parser to write: each target is read by eye from a handful of
pages. This script gathers those pages politely (scripts/fetch.py: cache,
robots.txt, one request per second per host) so the reading can be done from
the cache:

  start    the target's start_url
  people   targets.csv people_url, else the best people / team / staff link on the start page
  about    an About / Leadership link on the start page, when it is a different page
  careers  targets.csv careers_url, else the best careers / jobs / opportunities link
  list     any address written in the target's notes ("Centers list: https://...")

    python3 scripts/prep_targets.py --priority 2 --out data/raw/priority-2/worklist.json
                                    [--only-prefix harvard-,mit-] [--ids a,b,c] [--status todo]

The worklist has one item per target: the targets.csv row plus `pages`, a list
of {role, url, status, text (path under cache/_text/, or null), found_by}.
Reading and writing the source files is described in
scripts/center_read_brief.md; scripts/check_center_sources.py checks the
result before it goes into data/sources/.
"""
import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from depth_pass import text_path_for  # noqa: E402
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# link labels, best first
PEOPLE_LABELS = [
    r"^(our )?(people|team|staff)$", r"^(people|team|staff)\b", r"^meet (the|our) (team|staff|people)",
    r"^who we are$", r"^(faculty|faculty (and|&) staff|staff (and|&) faculty)$", r"^(researchers|research (staff|team))",
    r"^(directory|members|fellows|affiliates|leadership)$", r"\b(our team|our people|our staff)\b",
]
ABOUT_LABELS = [r"^about( us| the (center|institute|program|lab|initiative|project))?$", r"^(leadership|mission|contact( us)?)$"]
CAREERS_LABELS = [
    r"^(careers?|jobs?|employment|job openings|open positions|opportunities)$", r"^(work|join) (with|at) us$", r"^join (us|our team|the team)$",
    r"\b(careers?|employment|job (openings|opportunities)|open positions|we.?re hiring)\b",
    r"\b(research assistant|pre-?doc|internships?|fellowships?)\b.*\b(positions?|program|opportunit|apply|openings)\b",
    r"^(internships?|fellowships?|get involved|opportunities for students|student opportunities)$",
]
SKIP_HREF = re.compile(r"^(mailto:|tel:|javascript:|#)|\.(pdf|docx?|pptx?|xlsx?|zip|jpe?g|png)($|\?)", re.I)


def best_link(res, patterns, same_site=True):
    """First link (by pattern rank, then page order) whose label matches one of `patterns`."""
    from bs4 import BeautifulSoup

    if not res.get("html"):
        return None, None
    base = urllib.parse.urlsplit(res["url"])
    here = res["url"].split("#")[0].rstrip("/")
    links = []
    for a in BeautifulSoup(res["html"], "lxml").find_all("a", href=True):
        href = a["href"].strip()
        if SKIP_HREF.search(href):
            continue
        absu = urllib.parse.urljoin(res["url"], href).split("#")[0]
        if not absu.startswith("http") or absu.rstrip("/") == here:
            continue
        if same_site and urllib.parse.urlsplit(absu).netloc.lower().removeprefix("www.") != base.netloc.lower().removeprefix("www."):
            continue
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        if label and len(label) <= 60:
            links.append((label, absu))
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for label, absu in links:
            if rx.search(label):
                return absu, label
    return None, None


def grab(url, role, found_by):
    res = fetch(url)
    if res["html"] is not None and len(res["text"] or "") < 400 and res.get("method") != "playwright":
        res = fetch(url, render=True, force=True)
    page = {"role": role, "url": url, "status": str(res["status"])[:120], "text": None, "found_by": found_by}
    if res["text"]:
        tp = text_path_for(url)
        tp.write_text(res["text"], encoding="utf-8")
        page["text"] = str(tp.relative_to(ROOT))
    return page, res


def prep(row):
    pages, seen = [], set()

    def add(url, role, found_by):
        key = url.split("#")[0].rstrip("/").lower()
        if not url or key in seen:
            return None
        seen.add(key)
        page, res = grab(url, role, found_by)
        pages.append(page)
        return res

    start = add(row["start_url"], "start", "targets.csv start_url") if row.get("start_url") else None
    if row.get("people_url"):
        add(row["people_url"], "people", "targets.csv people_url")
    elif start:
        url, label = best_link(start, PEOPLE_LABELS)
        if url:
            add(url, "people", f"start page link labelled {label!r}")
    if start:
        url, label = best_link(start, ABOUT_LABELS)
        if url:
            add(url, "about", f"start page link labelled {label!r}")
    if row.get("careers_url"):
        add(row["careers_url"], "careers", "targets.csv careers_url")
    elif start:
        url, label = best_link(start, CAREERS_LABELS, same_site=False)
        if url:
            add(url, "careers", f"start page link labelled {label!r}")
    for url in re.findall(r"https?://[^\s;,)]+", row.get("notes") or ""):
        add(url.rstrip("."), "list", "address written in targets.csv notes")
    return pages


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--priority", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--status", default="todo")
    ap.add_argument("--only-prefix", help="comma-separated id prefixes")
    ap.add_argument("--not-prefix", help="comma-separated id prefixes to leave out")
    ap.add_argument("--ids", help="comma-separated target ids")
    args = ap.parse_args()
    rows = [r for r in csv.DictReader(open(ROOT / "data" / "targets.csv")) if r["priority"] == args.priority and r["status"] == args.status]
    if args.only_prefix:
        rows = [r for r in rows if r["id"].startswith(tuple(args.only_prefix.split(",")))]
    if args.not_prefix:
        rows = [r for r in rows if not r["id"].startswith(tuple(args.not_prefix.split(",")))]
    if args.ids:
        rows = [r for r in rows if r["id"] in set(args.ids.split(","))]
    work = []
    for row in rows:
        item = dict(row)
        try:
            item["pages"] = prep(row)
        except Exception as e:  # one bad site must not stop the batch
            item["pages"] = []
            item["prep_error"] = str(e)[:200]
        work.append(item)
        print(f"{row['id']}\t" + " ".join(f"{p['role']}={'ok' if p['text'] else 'FAIL'}" for p in item["pages"]), flush=True)
    out = ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(work, indent=2, ensure_ascii=False) + "\n")
    print(f"prep_targets: {len(work)} targets -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
