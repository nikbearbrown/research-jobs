#!/usr/bin/env python3
"""Find lab websites from a department's own listing pages.

`depth_pass.py sites` reads each PI's profile page for a lab link. Thousands
of labs have a profile page that links none. Many departments, though, keep a
page that lists their labs or research groups with links ("Research Labs",
"Research Groups", "Laboratories"), and some faculty directories carry a "Lab
website" link beside each name that the breadth pass, reading text only, did
not record. This reads those pages.

For each source file that has research-labs with a PI but no lab_website and
no member_count:

  pages read   the target's start_url; up to three links on it labelled as a
               labs / research-groups listing (or one hop through "Research");
               and the file's own listing_urls (the faculty directory).
  a match      a link is taken as a PI's lab site when
                 - its own label names the PI and a lab word ("Doe Lab",
                   "Jane Doe Research Group"), or
                 - it sits in the same small block of the page as the PI's
                   full name, no other PI of the department is named in that
                   block, and it is labelled as a lab / group / website link
                   or leads off the department's site.
               Profile pages, publication lists, social media and documents
               never count. A link found only as a bare "website" or off-site
               link must also show lab signs (its address names a lab or
               group, or its own menu has a people page), as in `sites`.
  decision     exactly one distinct link -> lab_website, with a note naming
               the page it was read from; several -> left null, not noted.

    python3 scripts/find_lab_listings.py [--dry-run] [--min 8] [--ids a,b] [--institution "Boston University"]

--dry-run prints the decisions and, per target, the listing pages it used.
"""
import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import depth_pass as dp  # noqa: E402
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LISTING_LABELS = [
    r"^(research |faculty |our )?(labs?|laboratories)$",
    r"\b(labs?|laboratories)\b",
    r"\bresearch (groups|sites|programs)\b|\bfaculty research\b|^(research )?groups$",
]
# links that mention a lab but are not a listing of the department's research labs
NOT_A_LISTING_RE = re.compile(r"undergrad|graduate|student|volunteer|internship|opportunit|safety|core|facilit|teaching|"
                              r"computer|manual|course|news|seminar|job|career|open|join|k-12|outreach|give|support|alumni|tour", re.I)
HOP_LABELS = [r"^research$", r"^research (overview|areas|at .{2,30})$", r"^faculty (and|&) research$"]
LAB_WORD_RE = re.compile(r"\b(lab|labs|laboratory|group|research (group|team|program))\b", re.I)
SITE_WORD_RE = re.compile(r"\b(lab|laboratory|group|research|personal|faculty)?\s*(web\s?site|web\s?page|home\s?page|site)\b|^\s*(lab|laboratory|group)\s*$", re.I)
PERSON_PATH_RE = re.compile(r"/(people|person|profile|profiles|faculty|directory|staff|bio|our-people|team)(/|$)", re.I)
SKIP_HREF = re.compile(r"^(mailto:|tel:|javascript:|#)", re.I)
BLOCK_TAGS = ("li", "tr", "article", "td", "p", "div", "section", "dd", "figure")


def host(u):
    return urllib.parse.urlsplit(u).netloc.lower().removeprefix("www.")


def same_site(a, b):
    ha, hb = host(a).split("."), host(b).split(".")
    return ha[-2:] == hb[-2:]


def labelled_links(res, patterns, limit):
    """Up to `limit` distinct same-site links whose label matches one of `patterns` (best pattern first)."""
    from bs4 import BeautifulSoup

    if not res.get("html"):
        return []
    here = dp.canon(res["url"])
    links = []
    for a in BeautifulSoup(res["html"], "lxml").find_all("a", href=True):
        href = a["href"].strip()
        if SKIP_HREF.search(href) or dp.DOC_HREF_RE.search(href):
            continue
        absu = urllib.parse.urljoin(res["url"], href).split("#")[0]
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        if absu.startswith("http") and label and len(label) <= 50 and dp.canon(absu) != here and same_site(absu, res["url"]):
            links.append((label, absu))
    out = []
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for label, absu in links:
            if rx.search(label) and not NOT_A_LISTING_RE.search(label) and dp.canon(absu) not in {dp.canon(u) for u in out}:
                out.append(absu)
            if len(out) >= limit:
                return out
    return out


def listing_pages(start_url, file_listing_urls):
    """Every page worth reading for one target: start page, labelled listing pages, the faculty directory."""
    pages, seen = [], set()

    def add(url, why):
        if url and dp.canon(url) not in seen:
            seen.add(dp.canon(url))
            res = fetch(url)
            if res.get("html"):
                pages.append((url, why, res))
                return res
        return None

    start = add(start_url, "start page") if start_url else None
    if start:
        found = labelled_links(start, LISTING_LABELS, 3)
        for hop in labelled_links(start, HOP_LABELS, 1):
            hop_res = add(hop, "research page")
            if hop_res:
                found += labelled_links(hop_res, LISTING_LABELS, 3)
        for u in found[:5]:
            add(u, "labs listing")
    for u in file_listing_urls or []:
        add(u, "faculty directory")
    return pages


def unwrap(url):
    """The address inside an Outlook "safelinks" wrapper (a page author pasted a link from an email)."""
    parts = urllib.parse.urlsplit(url)
    if parts.netloc.endswith("safelinks.protection.outlook.com"):
        inner = urllib.parse.parse_qs(parts.query).get("url")
        if inner:
            return inner[0]
    return url


def not_a_lab_link(absu, page_url, lab):
    if "/nucos-faculty-lab/" in absu:
        return True  # Northeastern College of Science's directory entry for a lab, not the lab's site
    if dp.NOT_A_LAB_SITE_RE.search(absu) or dp.DOC_HREF_RE.search(urllib.parse.urlsplit(absu).path):
        return True
    if lab.get("profile_url") and dp.canon(absu) == dp.canon(lab["profile_url"]):
        return True
    path = urllib.parse.urlsplit(absu).path
    if same_site(absu, page_url) and PERSON_PATH_RE.search(path) and not re.search(r"lab|group", path, re.I):
        return True  # the department's own page for the person, not a lab site
    return False


def candidates_on_page(soup, page_url, lab, roster):
    """[(url, label, how)] for one lab on one page; `roster` = folded full names of the file's other PIs."""
    first, last, lasts = dp.name_parts(lab["pi_name"])
    if not first or not last or len(last) < 3:
        return []
    full = f"{first} {last}"
    shared_last = sum(1 for name in roster if name.split()[-1] == last) > 1
    out = {}

    def consider(a, how):
        href = a["href"].strip()
        if SKIP_HREF.search(href):
            return
        absu = unwrap(urllib.parse.urljoin(page_url, href)).split("#")[0].strip()
        if not absu.startswith("http") or dp.canon(absu) == dp.canon(page_url) or not_a_lab_link(absu, page_url, lab):
            return
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()[:80]
        if not label and how == "offsite":
            return  # an unlabelled link (an image, an icon) says nothing about what it leads to
        if dp.NOT_A_SITE_LABEL_RE.search(label) or (dp.HUB_LABEL_RE.search(label) and not re.search(rf"\b{re.escape(last)}\b", dp.fold(label))):
            return
        out.setdefault(dp.canon(absu), (absu, label, how))

    # 1. a link whose own label names the PI and a lab word
    for a in soup.find_all("a", href=True):
        label = dp.fold(a.get_text(" ", strip=True))
        if len(label) <= 80 and re.search(rf"\b{re.escape(last)}\b", label) and LAB_WORD_RE.search(label):
            if shared_last and not re.search(rf"\b{re.escape(first)}\b", label):
                continue  # two PIs of this department share the last name and the label does not say which
            other_first = re.search(r"\b([a-z]+)\s+" + re.escape(last) + r"\b", label)
            if other_first and other_first.group(1) not in (first, "the", "prof", "professor", "dr") and len(other_first.group(1)) > 2 \
                    and not first.startswith(other_first.group(1)[:3]):
                continue  # "Mary Chen Lab" on a page where our PI is Jerry Chen
            consider(a, "named")
    # 2. a lab / website link in the same small block as the PI's full name
    for node in soup.find_all(string=lambda s: s and full in re.sub(r"\s+", " ", dp.fold(s))):
        block = node.parent
        for _ in range(6):
            if block is None or block.name in ("body", "html"):
                break
            text = re.sub(r"\s+", " ", dp.fold(block.get_text(" ", strip=True)))
            if block.name in BLOCK_TAGS and len(text) <= 700 and block.find("a", href=True):
                if any(name in text for name in roster if name != full):
                    break  # the block holds several PIs: a link in it could be anyone's
                for a in block.find_all("a", href=True):
                    label = a.get_text(" ", strip=True)
                    absu = urllib.parse.urljoin(page_url, a["href"].strip())
                    if LAB_WORD_RE.search(label) or SITE_WORD_RE.search(label):
                        consider(a, "block")
                    elif absu.startswith("http") and not same_site(absu, page_url):
                        consider(a, "offsite")
                break
            if len(text) > 700:
                break
            block = block.parent
    return list(out.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--min", type=int, default=8, help="only targets with at least this many labs to find")
    ap.add_argument("--ids")
    ap.add_argument("--institution", action="append")
    args = ap.parse_args()
    from bs4 import BeautifulSoup

    targets = {r["id"]: r for r in csv.DictReader(open(ROOT / "data" / "targets.csv", newline=""))}
    filled = several = looked = 0
    for path in sorted((ROOT / "data" / "sources").glob("*.json")):
        data = json.loads(path.read_text())
        tid = data["id"]
        if args.ids and tid not in args.ids.split(","):
            continue
        if args.institution and data.get("institution") not in args.institution:
            continue
        todo = [l for l in data["labs"] if l.get("kind") == "research-lab" and not l.get("lab_website") and l.get("pi_name")
                and l.get("member_count") is None]
        if len(todo) < args.min:
            continue
        pages = listing_pages((targets.get(tid) or {}).get("start_url"), data.get("listing_urls"))
        soups = [(url, why, BeautifulSoup(res["html"], "lxml")) for url, why, res in pages]
        roster = set()
        for l in data["labs"]:
            f, la, _ = dp.name_parts(l.get("pi_name") or "")
            if f and la:
                roster.add(f"{f} {la}")
        n_here = 0
        for lab in todo:
            looked += 1
            found = {}
            for url, why, soup in soups:
                for absu, label, how in candidates_on_page(soup, url, lab, roster):
                    found.setdefault(dp.canon(absu), (absu, label, how, url, why))
            cands = list(found.values())
            strong = [c for c in cands if c[2] in ("named", "block")]
            weak = [c for c in cands if c[2] == "offsite"]
            pick = None
            if len(strong) == 1:
                pick = strong[0]
            elif not strong and len(weak) == 1:
                absu = weak[0][0]
                parts = urllib.parse.urlsplit(absu)
                if dp.LABISH_URL_RE.search(parts.netloc + parts.path) or dp.site_roster_link(fetch(absu), absu):
                    pick = weak[0]
            elif len(strong) > 1 or len(weak) > 1:
                several += 1
                print(f"?? {lab['id']}\t" + " | ".join(f"{c[1]!r} {c[0]}" for c in (strong or weak)[:4]), flush=True)
            if pick:
                absu, label, how, page, why = pick
                if how == "block" and not LAB_WORD_RE.search(label):
                    parts = urllib.parse.urlsplit(absu)  # a bare "Website" link: needs lab signs, as in `sites`
                    if not (dp.LABISH_URL_RE.search(parts.netloc + parts.path) or dp.site_roster_link(fetch(absu), absu)):
                        print(f".. {lab['id']}\twebsite link with no lab signs\t{absu}", flush=True)
                        continue
                lab["lab_website"] = absu
                dp.append_note(lab, f"lab_website read from the department's {why} ({page}): link labelled {label!r}"
                               + {"named": ", which names the PI and the lab.", "block": ", shown beside the PI's name.",
                                  "offsite": ", the only outside link shown beside the PI's name; the site shows a lab or people page."}[how])
                filled += 1
                n_here += 1
                print(f"OK {lab['id']}\t{how}\t{label!r}\t{absu}", flush=True)
        print(f"-- {tid}: {n_here} of {len(todo)} found; pages: " + "; ".join(f"{why} {url}" for url, why, _ in soups), flush=True)
        if n_here and not args.dry_run:
            dp.save(path.resolve(), data)
    print(f"find_lab_listings: looked for {looked}, found {filled}, several candidates {several}"
          + (" (dry run, nothing written)" if args.dry_run else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
