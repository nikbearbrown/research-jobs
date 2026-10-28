#!/usr/bin/env python3
"""Parser for Bouvé College of Health Sciences faculty-and-staff-directory
pages: a repeating block of Name / Degree(s) / Title(s) / Department-tag /
"Contact Info" / "Close Info" / [location/phone] / "Email" / "Read Full Bio"
per person, with "Read Full Bio" linking to bouve.northeastern.edu/directory/<slug>/.

Usage (library):
    from parse_bouve_people import parse_people
    people = parse_people(text)
    # -> [{"name", "title", "dept", "profile_url"}, ...]
"""
import re

NAME_RE = re.compile(r"^[A-Z][a-zA-Z.'\-]+(?: [A-Z][a-zA-Z.'\-]+){1,3}$")
PROFILE_RE = re.compile(r"^'Read Full Bio' -> (\S+)$")


ANCHOR_RE = re.compile(r"^(Read Full Bio|Search)$")


def parse_people(text):
    lines = [l.strip() for l in text.splitlines()]
    profile_urls = [m.group(1) for l in lines if (m := PROFILE_RE.match(l))]
    people = []
    idx_profile = 0
    i = 0
    n = len(lines)
    while i < n:
        if ANCHOR_RE.match(lines[i]) and i + 1 < n and NAME_RE.match(lines[i + 1]):
            name = lines[i + 1]
            j = i + 2
            middle = []
            while j < n and lines[j] != "Contact Info" and len(middle) < 6:
                middle.append(lines[j])
                j += 1
            if j < n and lines[j] == "Contact Info":
                dept = middle[-1] if middle else None
                title = " ".join(middle[:-1]) if len(middle) > 1 else (middle[0] if middle else None)
                profile_url = profile_urls[idx_profile] if idx_profile < len(profile_urls) else None
                idx_profile += 1
                people.append({"name": name, "title": title, "dept": dept, "profile_url": profile_url})
                i = j
                continue
        i += 1
    return people


if __name__ == "__main__":
    import sys
    import json
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from fetch import fetch

    url = sys.argv[1]
    r = fetch(url)
    print(json.dumps(parse_people(r["text"]), indent=2, ensure_ascii=False))
