#!/usr/bin/env python3
"""Web-search pass: find lab websites the university pages do not link.

About 3,950 labs have a PI but no lab website and no size: the PI's profile
page links no lab site (`depth_pass.py sites`) and the department has no
labs listing that names it (`find_lab_listings.py`). The project owner decided
on 2026-11-17 that a web search may be used to FIND a candidate site for
these. A candidate is still recorded only when the site itself confirms it:
this script fetches the candidate and checks it before writing anything.

    python3 scripts/web_search_pass.py worklist --out data/raw/web-search/batch-001-worklist.json [--limit 100]
                                                [--institution "MIT"] [--source data/sources/mit-biology.json]

        The next labs to search for: research-labs with a PI, no lab_website,
        no member_count, and no earlier web-search note. Labs that already
        have a PI email come first (a sized lab with a contact is the goal).
        Each item carries the PI, title, institution, unit, profile_url and
        two suggested queries.

    python3 scripts/web_search_pass.py apply data/raw/web-search/batch-001-results.json [--dry-run]

        Results are a JSON list, one object per worklist item:
          {"source": ..., "lab_id": ..., "lab_website": "<candidate or null>",
           "query": "<the search that found it>", "note": "<optional, one sentence>"}
        For each candidate the script fetches the page (scripts/fetch.py:
        robots.txt, one request per second per host) and accepts it only if
          1. it is not a profile, publication, social, news or directory page;
          2. the site names the PI (full name, or "<Last> Lab / Group");
          3. the site is tied to the PI's institution (it is on the
             institution's domain, or its text names the institution or
             shows an address at it);
          4. the site looks like a lab or group site (its address or title
             names a lab or group, or its menu has a people / team page).
        Accepted -> lab_website is set, with a note giving the query and what
        was checked. Rejected -> lab_website stays null and the note says why.
        A null candidate -> a note that the search found no lab site, so the
        lab is not searched again. Source files are only ever changed by this
        command, never by hand.

After a batch is applied, the new sites are read for sizes like any others:
`depth_pass.py prep-sizes --only-note "found by web search"`, then the reading
described in scripts/depth_read_brief.md, `merge_read_results.py` and
`depth_pass.py apply`. See web-search-pass.md for the whole routine.
"""
import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import depth_pass as dp  # noqa: E402
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# institution -> (domains, names to look for in the site's text; a short all-capital name is matched case-sensitively)
INSTITUTIONS = {
    "Harvard": (["harvard.edu"], ["Harvard"]),
    "Harvard University": (["harvard.edu"], ["Harvard"]),
    "MIT": (["mit.edu"], ["Massachusetts Institute of Technology", "MIT"]),
    "Boston University": (["bu.edu"], ["Boston University", "BU"]),
    "Northeastern University": (["northeastern.edu", "neu.edu"], ["Northeastern University", "Northeastern"]),
    "Tufts University": (["tufts.edu"], ["Tufts"]),
    "Boston College": (["bc.edu"], ["Boston College"]),
    "Brandeis University": (["brandeis.edu"], ["Brandeis"]),
    "UMass Boston": (["umb.edu"], ["UMass Boston", "University of Massachusetts Boston", "University of Massachusetts, Boston"]),
    "Massachusetts General Hospital": (["massgeneral.org", "mgh.harvard.edu", "massgeneralbrigham.org"], ["Massachusetts General Hospital", "Mass General", "MGH"]),
    "Mass General Brigham": (["massgeneralbrigham.org", "massgeneral.org", "mgh.harvard.edu", "bwh.harvard.edu", "brighamandwomens.org"],
                             ["Mass General", "Massachusetts General Hospital", "Brigham and Women", "MGH", "BWH"]),
    "Brigham and Women's Hospital": (["brighamandwomens.org", "bwh.harvard.edu", "massgeneralbrigham.org"], ["Brigham and Women", "BWH"]),
    "Dana-Farber Cancer Institute": (["dana-farber.org", "dfci.harvard.edu"], ["Dana-Farber", "DFCI"]),
    "Beth Israel Deaconess Medical Center": (["bidmc.org", "bidmc.harvard.edu"], ["Beth Israel Deaconess", "BIDMC"]),
    "Boston Children's Hospital": (["childrenshospital.org", "childrens.harvard.edu"], ["Boston Children", "Children's Hospital Boston"]),
    "Joslin Diabetes Center": (["joslin.org", "joslin.harvard.edu"], ["Joslin"]),
    "Broad Institute of MIT and Harvard": (["broadinstitute.org"], ["Broad Institute"]),
    "Whitehead Institute for Biomedical Research": (["wi.mit.edu"], ["Whitehead Institute"]),
    "Forsyth Institute": (["forsyth.org"], ["Forsyth"]),
    "Hebrew SeniorLife": (["hebrewseniorlife.org", "marcusinstituteforaging.org"], ["Hebrew SeniorLife", "Marcus Institute"]),
    "Mass Eye and Ear": (["masseyeandear.org", "meei.harvard.edu"], ["Mass Eye and Ear", "Massachusetts Eye and Ear"]),
}
# places a search often returns that are never a lab's own site
NOT_A_SITE_HOST_RE = re.compile(
    r"(wikipedia\.org|ratemyprofessors|zoominfo|rocketreach|prabook|academictree|frontiersin\.org|publons|dblp\.|openreview\.net|"
    r"medium\.com|substack\.com|scholar\.archive|ieee\.org|acm\.org|nature\.com|sciencedirect|springer|wiley\.com|biorxiv|medrxiv|"
    r"nih\.gov|nsf\.gov|grantome|crunchbase|bloomberg\.com|glassdoor|indeed\.com|coursera|edx\.org|ted\.com|amazon\.|goodreads|"
    r"vimeo\.com|soundcloud|reddit\.com|quora\.com|pinterest|tiktok|threads\.net)", re.I)
PERSON_PATH_RE = re.compile(r"/(people|person|profile|profiles|faculty|directory|staff|bio|our-people|faculty-staff|team_member)(/|$)", re.I)
LAB_TITLE_RE = re.compile(r"\b(lab|labs|laboratory|group|research (group|team|program)|team)\b", re.I)
SEARCH_NOTE_RE = re.compile(r"web search", re.I)


def host(u):
    return urllib.parse.urlsplit(u).netloc.lower().removeprefix("www.")


def norm(text):
    """dp.fold plus the letters NFKD leaves alone (Turkish dotless i, Polish l, Scandinavian o ...)."""
    return dp.fold(text).translate(str.maketrans({"\u0131": "i", "\u0142": "l", "\u00f8": "o", "\u0111": "d", "\u00df": "ss", "\u00e6": "ae"}))


def people_link(home, url):
    """A people / team link on the candidate's home page. The page may have been reached through a
    redirect (wisecircuits.bu.edu -> sites.bu.edu/wisecircuits), so any host of the same site counts."""
    from bs4 import BeautifulSoup

    site = host(url).split(".")[-2:]
    for a in BeautifulSoup(home["html"], "lxml").find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absu = urllib.parse.urljoin(url, href).split("#")[0]
        if absu.startswith("http") and host(absu).split(".")[-2:] == site and dp.canon(absu) != dp.canon(url) \
                and dp.PEOPLE_LINK_RE.search(a.get_text(" ", strip=True) or ""):
            return absu
    return None


def on_domain(url, domains):
    h = host(url)
    return any(h == d or h.endswith("." + d) for d in domains)


def cmd_worklist(args):
    paths = [Path(p) for p in args.source] if args.source else sorted((ROOT / "data" / "sources").glob("*.json"))
    items = []
    for path in paths:
        data = json.loads(path.read_text())
        if args.institution and data.get("institution") not in args.institution:
            continue
        for lab in data["labs"]:
            if lab.get("kind") != "research-lab" or lab.get("lab_website") or lab.get("member_count") is not None:
                continue
            first, last, _ = dp.name_parts(lab.get("pi_name") or "")
            if not first or not last or first == last or SEARCH_NOTE_RE.search(lab.get("notes") or ""):
                continue
            name, inst, unit = lab["pi_name"], data.get("institution"), data.get("unit")
            items.append({
                "source": str(path.resolve().relative_to(ROOT)), "lab_id": lab["id"], "pi_name": name, "pi_title": lab.get("pi_title"),
                "institution": inst, "unit": unit, "profile_url": lab.get("profile_url"), "has_email": bool(lab.get("pi_email")),
                "queries": [f'"{name}" {inst} lab', f'"{name}" {unit} research group'],
            })
    items.sort(key=lambda i: (not i["has_email"], i["source"], i["lab_id"]))
    total = len(items)
    items = items[: args.limit]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n")
    print(f"worklist: {len(items)} labs -> {out} ({total} still to search in all)", file=sys.stderr)


def check_candidate(url, lab, institution):
    """(ok, reason or evidence sentence). Fetches the candidate and its people page, if it links one."""
    from bs4 import BeautifulSoup

    if not re.match(r"https?://", url or ""):
        return False, "the candidate is not a web address"
    if dp.NOT_A_LAB_SITE_RE.search(url) or NOT_A_SITE_HOST_RE.search(url) or dp.DOC_HREF_RE.search(urllib.parse.urlsplit(url).path):
        return False, "it is a publication, social-media, news, directory or document page, not a lab site"
    if lab.get("profile_url") and dp.canon(url) == dp.canon(lab["profile_url"]):
        return False, "it is the PI's profile page already on record"
    domains, names = INSTITUTIONS.get(institution, ([], [institution]))
    path = urllib.parse.urlsplit(url).path
    if on_domain(url, domains) and PERSON_PATH_RE.search(path) and not re.search(r"lab|group", path, re.I):
        return False, "it is the institution's own page for the person, not a lab site"
    home = fetch(url)
    if home["status"] == "blocked-by-robots":
        return False, "robots.txt does not allow reading it, so it could not be checked"
    if not home.get("html"):
        return False, f"it could not be read to check ({str(home['status'])[:60]})"
    pages = [(url, home)]
    people = dp.find_link(home, dp.PEOPLE_LINK_RE, dp.PEOPLE_HREF_RE) or people_link(home, url)
    if people:
        pres = fetch(people)
        if pres.get("html"):
            pages.append((people, pres))
    first, last, lasts = dp.name_parts(lab["pi_name"])
    first, last = norm(first), norm(last)
    text = " ".join(norm(p["text"] or "") for _, p in pages)
    raw = " ".join(p["text"] or "" for _, p in pages)
    soup = BeautifulSoup(home["html"], "lxml")
    title = norm(" ".join([soup.title.get_text(" ", strip=True) if soup.title else ""] + [h.get_text(" ", strip=True) for h in soup.find_all("h1")[:3]]))
    # 2. the site names the PI
    full = re.search(rf"\b{re.escape(first)}\b[a-z. ]{{0,20}}\b{re.escape(last)}\b", text)
    last_lab = re.search(rf"\b{re.escape(last)}\b\s+(lab|laboratory|group|research)", text)
    if not (full or (last_lab and re.search(rf"\b{re.escape(last)}\b", title))):
        return False, f"the site does not name {lab['pi_name']}"
    # 3. the site is tied to the institution
    tie = None
    if on_domain(url, domains):
        tie = f"the site is on the institution's domain ({host(url)})"
    else:
        for name in names:
            if (name.isupper() and len(name) <= 5 and re.search(rf"\b{re.escape(name)}\b", raw)) or \
                    (not (name.isupper() and len(name) <= 5) and norm(name) in text):
                tie = f"the site names {name}"
                break
        if not tie and any(re.search(rf"[@/.]{re.escape(d)}\b", home["html"], re.I) for d in domains):
            tie = "the site shows an address at the institution"
    if not tie:
        return False, f"the site does not show a tie to {institution}"
    # 4. it looks like a lab or group site
    parts = urllib.parse.urlsplit(url)
    if dp.LABISH_URL_RE.search(parts.netloc + parts.path):
        signs = "its address names a lab or group"
    elif LAB_TITLE_RE.search(title):
        signs = "its title names a lab or group"
    elif people or dp.site_roster_link(home, url):
        signs = "its menu links a people or team page"
    else:
        return False, "it shows no lab signs (no lab or group in its address or title, no people page); it looks like a personal page"
    who = "names the PI" if full else f"is titled after the PI ({last} lab)"
    return True, f"the site {who}; {tie}; {signs}"


def cmd_apply(args):
    results = json.loads(Path(args.results).read_text())
    by_source = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)
    counts = {"accepted": 0, "rejected": 0, "none": 0, "skipped": 0}
    for src, rs in by_source.items():
        path = ROOT / src
        data = json.loads(path.read_text())
        labs = {l["id"]: l for l in data["labs"]}
        for r in rs:
            lab = labs.get(r["lab_id"])
            if lab is None or lab.get("lab_website") or SEARCH_NOTE_RE.search(lab.get("notes") or ""):
                counts["skipped"] += 1
                print(f"-- {r['lab_id']}\tskipped (unknown lab, already has a website, or already searched)", flush=True)
                continue
            query = (r.get("query") or "").strip() or "not recorded"
            url = (r.get("lab_website") or "").strip()
            if not url:
                counts["none"] += 1
                dp.append_note(lab, f"web search found no lab or group site (query: {query})." + (f" {r['note'].strip()}" if r.get("note") else ""))
                print(f".. {lab['id']}\tno candidate", flush=True)
                continue
            ok, why = check_candidate(url, lab, data.get("institution"))
            if ok:
                counts["accepted"] += 1
                lab["lab_website"] = url
                dp.append_note(lab, f"lab_website found by web search (query: {query}) and checked against the site itself: {why}.")
                print(f"OK {lab['id']}\t{url}\t{why}", flush=True)
            else:
                counts["rejected"] += 1
                dp.append_note(lab, f"web search candidate {url} not recorded: {why} (query: {query}).")
                print(f"XX {lab['id']}\t{url}\t{why}", flush=True)
        if not args.dry_run:
            dp.save(path.resolve(), data)
    print(f"web_search_pass apply: {counts}" + (" (dry run, nothing written)" if args.dry_run else ""), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("worklist")
    w.add_argument("--out", required=True)
    w.add_argument("--limit", type=int, default=100)
    w.add_argument("--institution", action="append")
    w.add_argument("--source", action="append")
    a = sub.add_parser("apply")
    a.add_argument("results")
    a.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    {"worklist": cmd_worklist, "apply": cmd_apply}[args.cmd](args)


if __name__ == "__main__":
    main()
