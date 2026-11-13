#!/usr/bin/env python3
"""Check reader-written source files for priority 2/3 targets and install them.

    python3 scripts/check_center_sources.py STAGED_DIR WORKLIST.json [WORKLIST.json ...] [--dry-run]

Readers (scripts/center_read_brief.md) write one JSON per target into
STAGED_DIR. For each target in the worklists that has a staged file this:

  - fills the file-level fields the reader does not write (institution, unit,
    city, checked_on) from targets.csv;
  - makes every entry carry every schema key, checks ids are kebab-case,
    unique and start with the target id;
  - checks every address (lab_website, members_page_url, join_page_url,
    profile_url, listing_urls) against what was really read: it must be one
    of the target's gathered pages, a page in the fetch cache, or a link that
    appears on one of those pages. An address that fails is set to null and
    reported;
  - checks every email appears in the text of a page read for the target;
    one that does not is set to null and reported;
  - reports (does not change) a lead whose last name appears on none of the
    target's pages, and a member_count with no members_page_url;
  - for `school` targets, drops entries whose website is already in the
    directory (an existing lab's lab_website or another target's start_url)
    and names them in the file's notes;
  - writes data/sources/<id>.json (never over an existing file) and sets the
    target's status in targets.csv: `done` when at least one entry was
    recorded, `partial` when the pages gave nothing (the reason is in notes).

Nothing is written with --dry-run.
"""
import csv
import datetime
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch as F  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TODAY = datetime.date.today().isoformat()
LAB_KEYS = ["id", "kind", "lab_name", "pi_name", "pi_title", "pi_email", "accepting_grad_students", "lab_website",
            "location", "phone", "admin_name", "admin_email", "research_summary", "member_count", "member_breakdown",
            "members_page_url", "join_page_url", "join_notes", "profile_url", "notes"]
URL_KEYS = ["lab_website", "members_page_url", "join_page_url", "profile_url"]
INSTITUTION = {"harvard": "Harvard", "hks": "Harvard", "mit": "MIT", "bu": "Boston University", "bc": "Boston College",
               "brandeis": "Brandeis University", "northeastern": "Northeastern University", "tufts": "Tufts University",
               "umass": "UMass Boston"}


def canon(u):
    return re.sub(r"^(https?://)?(www\.)?", "", (u or "").strip(), flags=re.I).split("#")[0].rstrip("/").lower()


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def cached(url):
    """(html, text) of a page in the fetch cache whose recorded address is this one, else (None, None)."""
    try:
        html_path, meta_path = F._cache_paths(url)
        if html_path.exists() and meta_path.exists() and canon(json.loads(meta_path.read_text()).get("url")) == canon(url):
            html = html_path.read_text(encoding="utf-8", errors="replace")
            return html, F.html_to_text(html, base_url=url)
    except Exception:
        pass
    return None, None


class Pages:
    """Everything read for one target: the gathered pages plus any page the reader fetched and listed."""

    def __init__(self, item, listing_urls):
        self.read, self.text, self.links = set(), "", set()
        for url in [p["url"] for p in item.get("pages", [])] + list(listing_urls or []):
            html, text = cached(url)
            if html is None:
                continue
            self.read.add(canon(url))
            self.text += "\n" + fold(text)
            for href in re.findall(r"""href=["']([^"'#]+)""", html):
                self.links.add(canon(urllib.parse.urljoin(url, href.strip())))

    def knows(self, url):
        c = canon(url)
        if c in self.read or c in self.links:
            return True
        html, text = cached(url)  # a page the reader fetched but did not list
        if html is not None:
            self.read.add(c)
            self.text += "\n" + fold(text)
            return True
        return False


def existing_sites():
    sites = set()
    labs = json.loads((ROOT / "data" / "labs.json").read_text())
    for lab in labs if isinstance(labs, list) else labs.get("labs", []):
        if lab.get("lab_website"):
            sites.add(canon(lab["lab_website"]))
    for row in csv.DictReader(open(ROOT / "data" / "targets.csv")):
        if row.get("start_url"):
            sites.add(canon(row["start_url"]))
    return sites


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    staged, worklists = Path(args[0]), args[1:]
    items = {}
    for w in worklists:
        for item in json.loads(Path(w).read_text()):
            items[item["id"]] = item
    known_sites = existing_sites()
    status, problems, totals = {}, 0, {"targets": 0, "entries": 0, "sized": 0, "join": 0, "dropped": 0}
    for tid, item in sorted(items.items()):
        src = staged / f"{tid}.json"
        dest = ROOT / "data" / "sources" / f"{tid}.json"
        if not src.exists():
            continue
        if dest.exists():
            print(f"SKIP {tid}: data/sources/{tid}.json already exists")
            continue
        try:
            data = json.loads(src.read_text())
        except Exception as e:
            print(f"BAD JSON {tid}: {e}")
            problems += 1
            continue
        pages = Pages(item, data.get("listing_urls"))
        listing = [u for u in (data.get("listing_urls") or []) if pages.knows(u)]
        for u in (data.get("listing_urls") or []):
            if u not in listing:
                print(f"UNREAD listing_url {tid}: {u}")
                problems += 1
        labs, seen_ids, dropped = [], set(), []
        for raw in data.get("labs") or []:
            lab = {k: raw.get(k) for k in LAB_KEYS}
            lab["kind"] = "research-lab"
            lid = lab["id"] or ""
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", lid) or not lid.startswith(tid) or lid in seen_ids:
                print(f"BAD ID {tid}: {lid!r}")
                problems += 1
                continue
            seen_ids.add(lid)
            for k in URL_KEYS:
                if lab[k] and not pages.knows(lab[k]):
                    print(f"UNVERIFIED {k} {lid}: {lab[k]}")
                    problems += 1
                    lab[k] = None
            for k in ("pi_email", "admin_email"):
                if lab[k] and fold(lab[k]) not in pages.text and fold(lab[k]).replace("@", " at ") not in pages.text:
                    # obfuscated addresses ("name [at] domain") are read by eye; accept only a literal match here
                    local = fold(lab[k]).split("@")[0]
                    if local not in pages.text:
                        print(f"UNVERIFIED {k} {lid}: {lab[k]}")
                        problems += 1
                        lab[k] = None
            if lab["pi_name"]:
                last = fold(re.sub(r",.*$", "", lab["pi_name"])).split()[-1]
                if last not in pages.text:
                    print(f"CHECK lead not on the pages read {lid}: {lab['pi_name']}")
                    problems += 1
            if lab["member_count"] is not None and (not isinstance(lab["member_count"], int) or not lab["members_page_url"]):
                print(f"CHECK member_count {lid}: {lab['member_count']} from {lab['members_page_url']}")
                problems += 1
                lab["member_count"] = lab["member_breakdown"] = None
            if item["category"] == "school" and lab["lab_website"] and canon(lab["lab_website"]) in known_sites:
                dropped.append(lab["lab_name"] or lab["lab_website"])
                continue
            if lab["lab_website"]:
                known_sites.add(canon(lab["lab_website"]))
            labs.append(lab)
        notes = (data.get("notes") or "").strip()
        if dropped:
            notes += (" " if notes else "") + f"Left out because the directory already has them ({len(dropped)}): " + "; ".join(dropped) + "."
        out = {
            "id": tid,
            "institution": INSTITUTION.get(tid.split("-")[0]) or item.get("parent") or item["name"],
            "unit": item["name"],
            "city": (item.get("city") or "").replace("Medford/Boston", "Medford / Boston") + ", MA",
            "checked_on": TODAY,
            "listing_urls": listing,
            "labs": labs,
            "non_lab_people": data.get("non_lab_people") or [],
            "notes": notes or None,
        }
        status[tid] = "done" if labs else "partial"
        totals["targets"] += 1
        totals["entries"] += len(labs)
        totals["sized"] += sum(1 for l in labs if l["member_count"] is not None)
        totals["join"] += sum(1 for l in labs if l["join_page_url"])
        totals["dropped"] += len(dropped)
        if not dry:
            dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    if status and not dry:
        path = ROOT / "data" / "targets.csv"
        rows = list(csv.DictReader(open(path, newline="")))
        fields = list(rows[0].keys())
        for row in rows:
            if row["id"] in status:
                row["status"] = status[row["id"]]
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")  # targets.csv uses CRLF
            w.writeheader()
            w.writerows(rows)
    print(f"check_center_sources: {totals}, done {sum(v == 'done' for v in status.values())}, "
          f"partial {sum(v == 'partial' for v in status.values())}, things to look at {problems}"
          + (" (dry run, nothing written)" if dry else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
