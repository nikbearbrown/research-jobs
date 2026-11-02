#!/usr/bin/env python3
"""Build data/sources/mgh-lab-search.json from the Mass General Brigham
institutes/centers/labs search (crawled by scripts/crawl_mgb_labs.py).

For every "Lab" tile:
  * tiles pointing at research.massgeneralbrigham.org are MGB's own lab
    pages. Their static HTML has a "people-grid" block (one teamLeader link
    plus one link per member), the hero's phone/email, and optional "Open
    Positions"/"Contact" sections. The people links themselves
    (/people-cfo/...) are robots.txt-blocked, but the rendered lab page
    shows each member's name and title, so the page is also rendered once.
  * tiles pointing anywhere else (a lab's own site, mol.bio, a center site)
    are recorded as lab name + website only: PI and size come from a later
    per-lab read.

Labs whose PI already appears in another hospital source file are left out
and listed in the file's notes, so the directory doesn't double-count them.

Usage: .venv/bin/python scripts/build_mgb_source.py data/raw/mgb-search-<date>.json [out.json]
(out.json defaults to data/sources/mgh-lab-search.json)
"""
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

from fetch import fetch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources" / "mgh-lab-search.json"
HOSPITAL_SOURCES = ("mgh-", "bwh-", "mclean-", "meei-", "spaulding-", "mgb-", "brigham-")

HOSPITALS = [
    (re.compile(r"Massachusetts General Hospital|Mass General Hospital|\bMGH\b"), "Massachusetts General Hospital"),
    (re.compile(r"Brigham and Women|Brigham & Women|\bBWH\b"), "Brigham and Women's Hospital"),
    (re.compile(r"McLean Hospital"), "McLean Hospital"),
    (re.compile(r"Mass Eye and Ear|Massachusetts Eye and Ear"), "Mass Eye and Ear"),
    (re.compile(r"Spaulding"), "Spaulding Rehabilitation"),
]
ROLE_PATTERNS = [
    ("postdocs", r"post-?doc|research fellow|postdoctoral"),
    ("grad students", r"graduate student|ph\.?d\.? (student|candidate)|doctoral student"),
    ("medical students", r"medical student"),
    ("undergrads", r"undergrad|intern\b|co-op"),
    ("research staff", r"technician|research assistant|research associate|research coordinator|lab manager|scientist|instructor|research specialist|analyst|engineer"),
    ("faculty", r"professor|investigator|physician|faculty"),
    ("admins", r"administrat|assistant to|coordinator"),
]


def slug(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def name_from_slug(sl):
    return " ".join(p.capitalize() for p in sl.split("-"))


def existing_hospital_pis():
    pis = {}
    for p in (ROOT / "data" / "sources").glob("*.json"):
        if p.name == OUT.name or not p.name.startswith(HOSPITAL_SOURCES):
            continue
        for lab in json.loads(p.read_text())["labs"]:
            if lab.get("pi_name"):
                pis[slug(re.sub(r",.*$", "", lab["pi_name"]))] = p.stem
    return pis


def norm_url(u):
    return re.sub(r"^https?://(www\.)?", "", (u or "").lower()).rstrip("/")


def existing_sites():
    """lab_website/profile_url of every lab in any other source file -> that file's id."""
    sites = {}
    for p in (ROOT / "data" / "sources").glob("*.json"):
        if p.name == OUT.name:
            continue
        for lab in json.loads(p.read_text())["labs"]:
            for k in ("lab_website", "profile_url"):
                if lab.get(k):
                    sites[norm_url(lab[k])] = f"{p.stem}: {lab['id']}"
    return sites


def team_from_static(html):
    soup = BeautifulSoup(html, "lxml")
    grid = soup.find(class_="people-grid")
    if not grid:
        return None, []
    leader, members = None, []
    for row in grid.find_all("div", recursive=False):
        a = row.find("a", href=re.compile(r"/people-cfo/"))
        if not a:
            continue
        sl = a["href"].rstrip("/").split("/")[-1]
        if "teamLeader" in row.get_text(" ", strip=True) and leader is None:
            leader = sl
        members.append(sl)
    return leader, members


def titles_from_rendered(text, slugs):
    """Map each people slug to (display name, title line) from rendered text."""
    lines = [ln.strip() for ln in text.split("\n--- mailto")[0].splitlines() if ln.strip()]
    out = {}
    for i, ln in enumerate(lines):
        base = slug(re.sub(r",.*$", "", ln))
        for sl in slugs:
            if sl not in out and base == sl and i + 1 < len(lines):
                out[sl] = (re.sub(r"\s+", " ", ln), lines[i + 1])
    return out


def section_text(soup, heading_re):
    h = soup.find(re.compile("^h[1-6]$"), string=heading_re)
    if not h:
        return None, None
    parts = []
    for sib in h.find_next_siblings():
        if re.match(r"^h[1-6]$", sib.name or ""):
            break
        parts.append(sib.get_text(" ", strip=True))
    return h.get("id"), " ".join(p for p in parts if p)[:500] or None


def breakdown(leader_title, titled):
    counts = {}
    for _, title in titled:
        t = title.lower()
        for label, pat in ROLE_PATTERNS:
            if re.search(pat, t):
                counts[label] = counts.get(label, 0) + 1
                break
        else:
            counts["other"] = counts.get("other", 0) + 1
    singular = {"postdocs": "postdoc", "grad students": "grad student", "medical students": "medical student",
                "undergrads": "undergrad", "admins": "admin"}
    parts = ["1 PI"] + [f"{n} {singular.get(k, k) if n == 1 else k}" for k, n in counts.items()]
    return ", ".join(parts)


def internal_lab(tile):
    static = fetch(tile["url"])
    if static["html"] is None:
        return None, f"lab page failed to load ({static['status']})"
    soup = BeautifulSoup(static["html"], "lxml")
    main = soup.find("main") or soup.body
    leader, members = team_from_static(static["html"])
    h1 = main.find("h1")
    heading = h1.get_text(" ", strip=True) if h1 else None
    page_text = main.get_text(" ", strip=True)
    emails = [a["href"][7:].split("?")[0].strip().strip("%20").lower()
              for a in main.find_all("a", href=re.compile(r"^mailto:", re.I))]
    emails = [re.sub(r"^%20", "", e) for e in emails]
    emails += [e.lower() for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", page_text)]
    phone = re.search(r"Call:\s*(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4})", page_text)
    join_id, join_text = section_text(main, re.compile(r"open positions|positions available|join (us|the lab|our)|current openings", re.I))
    _, contact_text = section_text(main, re.compile(r"^contact", re.I))

    rendered_titles, leader_name, leader_title = {}, None, None
    if members:
        r = fetch(tile["url"] + ("&" if "?" in tile["url"] else "?") + "rendered=1", render=True)
        if r["text"]:
            rendered_titles = titles_from_rendered(r["text"], members)
    if leader:
        leader_name, leader_title = rendered_titles.get(leader, (None, None))
        if leader_name is None:
            leader_name = name_from_slug(leader)

    heading_pi = None
    if not leader and heading:
        # "Laboratory of Jane Doe, PhD" / "Doe Lab: Jane Doe, MD" -- a name followed by a degree comma
        m = re.search(r"(?:Lab(?:oratory)?\s+of|Lab(?:oratory)?:)\s+(?:Dr\.?\s+)?"
                      r"([A-Z][A-Za-z.'’-]+(?:\s+[A-Z][A-Za-z.'’-]*){1,3}?)\s*,", heading)
        if m:
            heading_pi = m.group(1)
            leader_name = heading_pi

    hospital = None
    for pat, label in HOSPITALS:
        if pat.search((leader_title or "") + " " + (heading or "") + " " + page_text[:1500]):
            hospital = label
            break

    lab = {
        "lab_name": tile["name"],
        "pi_name": re.sub(r",.*$", "", leader_name).strip() if leader_name else None,
        "pi_title": leader_title,
        "pi_email": None,
        "phone": phone.group(1).strip() if phone else None,
        "member_count": len(members) if len(members) > 1 else None,
        "member_breakdown": None,
        "members_page_url": tile["url"] if members else None,
        "join_page_url": (tile["url"] + "#" + join_id) if join_text and join_id else None,
        "join_notes": ("Open Positions section on the lab page: " + join_text[:300]) if join_text else None,
    }
    notes = []
    if hospital:
        notes.append(f"Hospital (from page text): {hospital}.")
    if emails:
        # the hero's contact address: the PI's own only if it matches their name
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from depth_pass import email_matches_pi
        mine = [e for e in dict.fromkeys(emails) if lab["pi_name"] and email_matches_pi(e, lab["pi_name"])]
        if len(mine) == 1:
            lab["pi_email"] = mine[0]
        else:
            notes.append(f"Contact address(es) on the page not clearly the PI's: {', '.join(list(dict.fromkeys(emails))[:3])}.")
    if len(members) == 1:
        notes.append("The page's Research Team grid lists only one person, so the roster looks incomplete; size left unknown.")
    elif members:
        titled = [rendered_titles[s] for s in members if s != leader and s in rendered_titles]
        if len(titled) == len(members) - (1 if leader else 0):
            lab["member_breakdown"] = breakdown(leader_title, titled) if leader else None
        notes.append(f"Member count = the page's Research Team grid ({len(members)} people"
                     + (" incl. the team leader)." if leader else "; no team leader marked, so a PI may not be among them)."))
    else:
        notes.append("Page has no Research Team grid; size unknown.")
    if heading_pi:
        notes.append(f"PI taken from the page heading ({heading!r}); no team leader marked in a team grid.")
    elif not leader:
        notes.append("No team leader marked on the page; PI not identified.")
    return lab, " ".join(notes)


def blank_lab():
    keys = ["id", "kind", "lab_name", "pi_name", "pi_title", "pi_email", "accepting_grad_students", "lab_website",
            "location", "phone", "admin_name", "admin_email", "research_summary", "member_count", "member_breakdown",
            "members_page_url", "join_page_url", "join_notes", "profile_url", "notes"]
    return {k: None for k in keys}


def main():
    raw = json.loads(Path(sys.argv[1]).read_text())
    tiles = [t for t in raw["tiles"] if t["type"] == "Lab"]
    known = existing_hospital_pis()
    sites = existing_sites()
    labs, skipped, used_ids = [], [], set()
    for i, t in enumerate(tiles, 1):
        lab = blank_lab()
        lab["kind"] = "research-lab"
        lab["lab_name"] = t["name"]
        internal = "research.massgeneralbrigham.org" in t["url"]
        if internal:
            got, note = internal_lab(t)
            if got:
                lab.update(got)
            lab["profile_url"] = t["url"]
            lab["notes"] = "From the MGB institutes/centers/labs search (MGB's own lab page). " + note
        else:
            lab["lab_website"] = t["url"]
            lab["notes"] = ("From the MGB institutes/centers/labs search; the tile links straight to an external site, "
                            "so PI, contact and size are not yet read.")
        site_key = norm_url(lab["lab_website"] or lab["profile_url"])
        if site_key in sites:
            skipped.append(f"{t['name']} ({sites[site_key]})")
            continue
        if lab["pi_name"] and slug(lab["pi_name"]) in known:
            skipped.append(f"{lab['pi_name']} ({known[slug(lab['pi_name'])]})")
            continue
        base = "mgh-lab-search-" + slug(lab["pi_name"] or t["name"])
        lid, n = base, 2
        while lid in used_ids:
            lid, n = f"{base}-{n}", n + 1
        used_ids.add(lid)
        lab["id"] = lid
        labs.append(lab)
        print(f"{i}/{len(tiles)}\t{lid}\tmembers={lab['member_count']}\temail={lab['pi_email']}", flush=True)

    data = json.loads(OUT.read_text())
    data["checked_on"] = datetime.date.today().isoformat()
    data["listing_urls"] = [raw["source"]]
    data["labs"] = labs
    data["notes"] = (
        f"Full crawl of the Mass General Brigham-wide institutes/centers/labs search ({raw['reported_total']}; "
        f"{len(tiles)} tagged Lab) via scripts/crawl_mgb_labs.py + scripts/build_mgb_source.py. Covers MGH, BWH, "
        "McLean, Mass Eye and Ear and Spaulding at once (bwh-research, mgh-research-institute and meei-research point "
        "here). Each lab's hospital, where its page names one, is in its notes. Labs on MGB's own pages have a PI "
        "(the page's team leader), a member count from the page's Research Team grid, and roles from the rendered "
        "page; labs whose tile links to an external site are name + website only so far. "
        f"Left out as already recorded in another source file, by PI name or website ({len(skipped)}): " + "; ".join(skipped) + "."
    )
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(labs)} labs written, {len(skipped)} skipped as duplicates -> {out}")


if __name__ == "__main__":
    main()
