#!/usr/bin/env python3
"""Parser for BU WordPress department directory pages whose outbound links
(as surfaced by scripts/fetch.py's text extraction) are labeled
"FullName Title[; Title2...]" pointing at a bu.edu/<dept>/profile/<slug>/
page -- confirmed on bu.edu/math/people/faculty, several bu.edu/eng/...
department pages.

Usage (library):
    from parse_bu_people import parse_people
    people = parse_people(text)
    # -> [{"name", "title", "profile_url"}, ...]
"""
import re

TITLE_START = re.compile(
    r"\b(Professor|Lecturer|Associate|Assistant|Clinical|Research|Senior|"
    r"Affiliated|Chair|Director|Instructor|Emeritus|Dean|Chief|Head)\b"
)
OUTLINK_RE = re.compile(r"^'(.+?)' -> (\S+)$")


def parse_people(text):
    results = []
    seen = set()
    for line in text.splitlines():
        m = OUTLINK_RE.match(line)
        if not m:
            continue
        label, url = m.group(1), m.group(2)
        if "/profile/" not in url:
            continue
        tm = TITLE_START.search(label)
        if not tm:
            continue
        name = label[: tm.start()].strip()
        # strip a leading all-caps initials artifact from the page's avatar
        # span (e.g. "YA Yves Atchade" -> "Yves Atchade")
        im = re.match(r"^([A-Z]{2,3}) ([A-Z][a-z].*)$", name)
        if im:
            name = im.group(2)
        title = label[tm.start():].strip().rstrip(";").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        results.append({"name": name, "title": title, "profile_url": url})
    return results


NON_LAB_TITLE_RE = re.compile(
    r"\b(lecturer|clinical|professor of the practice|master lecturer|"
    r"adjunct|visiting)\b",
    re.I,
)


def is_non_lab_title(title):
    return bool(NON_LAB_TITLE_RE.search(title or ""))


if __name__ == "__main__":
    import sys
    import json

    text = open(sys.argv[1]).read()
    print(json.dumps(parse_people(text), indent=2, ensure_ascii=False))
