#!/usr/bin/env python3
"""Correct profile_url values that point at another person's page.

In the Northeastern Bouve directory files and the Brandeis science files the
breadth pass paired some names with the NEXT person's profile link (the
listing pages label every link "Read Full Bio" / "ScholarWorks", so the link
text gave no check). This reads each file's listing pages again and matches
each person to a profile link by the name in the link's own address
(bouve.northeastern.edu/directory/<first>-<last>/,
scholarworks.brandeis.edu/esploro/profile/<first>_<last>/).

For every lab whose profile_url names someone else:
  - exactly one link on the listing page names this person -> profile_url is
    corrected to it;
  - none (or several) -> profile_url is set to null.
Either way a note records the old value, and notes written by earlier passes
about what "the profile page" showed are removed, because they described the
wrong page (so `depth_pass.py emails` and `sites` will read the right one).
An email that an earlier pass read from the wrong page is cleared when it does
not appear on the corrected page.

    python3 scripts/fix_profile_links.py [--dry-run]
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from depth_pass import addresses_on_page, append_note, fold, name_parts, save  # noqa: E402
from fetch import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FILES = ["northeastern-*.json", "brandeis-*.json"]
PROFILE_RE = re.compile(r"bouve\.northeastern\.edu/directory/(?:directory/)?([^/?#]+)|scholarworks\.brandeis\.edu/esploro/profile/([^/?#]+)")
# sentences earlier passes wrote about what the (wrong) profile page showed
STALE_NOTE_RE = re.compile(
    r" ?Depth pass [0-9-]+: (profile page (shows|is blocked|failed)[^.]*\.( pi_email[^.]*\.)?"
    r"|pi_email read from the profile page[^.]*\."
    r"|lab_website not checked: the profile page on record does not show this person's name[^.]*\.)")


HEADING_AS_NAME_RE = re.compile(r"^(teaching|emerit[iu]s?|affiliated|adjunct|research)? ?(faculty|staff)$", re.I)


def slug_of(url):
    m = PROFILE_RE.search(url or "")
    return (m.group(1) or m.group(2)) if m else None


def slug_names(slug):
    words = [w for w in re.split(r"[^a-z]+", fold(urllib.parse.unquote(slug))) if w]
    return set(words), "".join(words)


def slug_is(slug, pi_name):
    """True when the profile address names this person: first name and a last name both in the slug."""
    first, _, lasts = name_parts(pi_name)
    if not first or not slug:
        return False
    words, squashed = slug_names(slug)
    last_ok = any(re.sub(r"[^a-z]", "", ln) in words or (len(ln) >= 4 and re.sub(r"[^a-z]", "", ln) in squashed) for ln in lasts)
    first_ok = first in words or (len(first) >= 3 and any(w.startswith(first[:3]) for w in words))
    if len(words) == 1:
        return last_ok  # scholarworks.brandeis.edu/esploro/profile/meisel: the address is the last name alone
    return last_ok and first_ok


def listing_links(urls):
    from bs4 import BeautifulSoup

    out = {}
    for url in urls or []:
        res = fetch(url)
        if not res.get("html"):
            continue
        for a in BeautifulSoup(res["html"], "lxml").find_all("a", href=True):
            absu = urllib.parse.urljoin(url, a["href"].strip()).split("#")[0]
            s = slug_of(absu)
            if s:
                out[s] = absu
    return out


def main():
    dry = "--dry-run" in sys.argv
    fixed = nulled = emails_cleared = 0
    for pattern in FILES:
        for path in sorted((ROOT / "data" / "sources").glob(pattern)):
            data = json.loads(path.read_text())
            wrong = [l for l in data["labs"] if l.get("pi_name") and slug_of(l.get("profile_url"))
                     and not slug_is(slug_of(l["profile_url"]), l["pi_name"])]
            if not wrong:
                continue
            links = listing_links(data.get("listing_urls"))
            on_listing = set(links.values())
            # The file's own records are a second source: every address in them was read
            # from the listing page, only paired with the wrong name. (One Bouve listing
            # page has since moved and now returns 404.)
            for other in data["labs"]:
                if slug_of(other.get("profile_url")):
                    links.setdefault(slug_of(other["profile_url"]), other["profile_url"])
            for lab in wrong:
                old = lab["profile_url"]
                heading = HEADING_AS_NAME_RE.match(lab["pi_name"])
                if heading and ";" in (lab.get("pi_title") or ""):
                    # the parser took a section heading for the name and pushed the real name into the title
                    real, title = [x.strip() for x in lab["pi_title"].split(";", 1)]
                    append_note(lab, f"pi_name corrected: the breadth pass recorded the section heading {lab['pi_name']!r} "
                                     f"as the name; the listing page shows {real} under it.")
                    lab["pi_name"], lab["pi_title"] = real, title
                matches = sorted({u for s, u in links.items() if slug_is(s, lab["pi_name"])})
                notes = lab.get("notes") or ""
                email_from_wrong_page = bool(re.search(r"pi_email read from the profile page", notes))
                lab["notes"] = STALE_NOTE_RE.sub("", notes).strip() or None
                if len(matches) == 1:
                    lab["profile_url"] = matches[0]
                    where = ("the listing page links this person to the address now recorded" if matches[0] in on_listing else
                             "the address now recorded names this person and was read from the same listing page")
                    sentence = f"profile_url corrected: the earlier value ({old}) is another person's page; {where}."
                    fixed += 1
                else:
                    lab["profile_url"] = None
                    why = "no profile link naming this person" if not matches else "several links that could be this person"
                    sentence = (f"profile_url removed: the earlier value ({old}) is another person's page, "
                                f"and the listing page shows {why}.")
                    nulled += 1
                if email_from_wrong_page and lab.get("pi_email"):
                    shown = []
                    if lab["profile_url"] and not dry:
                        res = fetch(lab["profile_url"])
                        shown = addresses_on_page(res) if res.get("html") else []
                    if lab["pi_email"].lower() not in shown:
                        sentence += f" The email {lab['pi_email']} had been read from that other page and was removed."
                        lab["pi_email"] = None
                        emails_cleared += 1
                append_note(lab, sentence)
                print(f"{'OK ' if lab['profile_url'] else '-- '}{lab['id']}\t{slug_of(old)} -> {slug_of(lab['profile_url']) if lab['profile_url'] else None}"
                      + ("\t[email from the wrong page]" if email_from_wrong_page else ""), flush=True)
            if not dry:
                save(path, data)
    print(f"fix_profile_links: corrected {fixed}, set to null {nulled}, emails cleared {emails_cleared}"
          + (" (dry run, nothing written)" if dry else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
