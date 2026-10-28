#!/usr/bin/env python3
"""Generic breadth-pass parser for MIT department faculty-listing pages that
repeat a simple `Name / Title(s) [/ one-line blurb]` block per person in the
page's visible text (as extracted by scripts/fetch.py).

Usage (library):
    from parse_name_title_blurb import parse_people
    people = parse_people(text)
    # -> [{"name", "title", "summary", "profile_url"}, ...]

Strategy: scan the body text for a line that looks like a person's name
immediately followed by a line containing a title keyword (Professor,
Director, Lecturer, ...). Once found, the next line is the title and (if it
doesn't itself look like another name) the line after that is treated as a
one-line research blurb. profile_url is looked up from the page's "other
links" section (scripts/fetch.py appends label -> url lines) by finding a
link whose label equals the name or starts with the name followed by a
space (covers templates that concatenate name+title+areas into one link
label, e.g. MIT AeroAstro's Opus theme).
"""
import re

NAME_RE = re.compile(r"^[A-ZÀ-Ý][\w.\-'’]+(?: [A-ZÀ-Ý][\w.\-'’]*\.?){1,3}$")
TITLE_KEYWORDS = re.compile(
    r"\b(professor|director|dean|chair|head|lecturer|scientist|fellow|engineer|"
    r"investigator|associate|assistant|instructor|research scientist|postdoc)\b",
    re.I,
)


def _outlink_lookup(text):
    links = []
    for line in text.splitlines():
        m = re.match(r"^'(.+?)' -> (\S+)$", line)
        if m:
            links.append((m.group(1), m.group(2)))
    return links


def _find_profile_url(name, links):
    for label, url in links:
        if label == name or label.startswith(name + " "):
            return url
    return None


GENERIC_LINK_LABELS = {"view profile", "profile", "read more", "learn more", "more info", "bio"}


def parse_card_links(text):
    """Fallback for card-grid directories with no inline title text: a bare
    'Name' -> url link immediately followed by a generic 'View Profile' (or
    similar) -> same-url link. Returns [{"name", "title": None, "summary":
    None, "profile_url"}, ...]."""
    links = _outlink_lookup(text)
    results = []
    seen = set()
    for idx in range(len(links) - 1):
        label, url = links[idx]
        next_label, next_url = links[idx + 1]
        if (
            NAME_RE.match(label)
            and label not in seen
            and next_label.lower() in GENERIC_LINK_LABELS
            and next_url == url
        ):
            seen.add(label)
            results.append({"name": label, "title": None, "summary": None, "profile_url": url})
    return results


def parse_people(text):
    lines = [ln.rstrip() for ln in text.splitlines()]
    links = _outlink_lookup(text)
    results = []
    seen = set()
    n = len(lines)
    i = 0
    while i < n - 1:
        name = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < n else ""
        if NAME_RE.match(name) and TITLE_KEYWORDS.search(nxt) and name not in seen:
            title = nxt
            summary = None
            j = i + 2
            if j < n:
                cand = lines[j].strip()
                if cand and not NAME_RE.match(cand.split(";")[0].strip()):
                    summary = cand
            seen.add(name)
            results.append({
                "name": name,
                "title": title,
                "summary": summary,
                "profile_url": _find_profile_url(name, links),
            })
            i += 2
        else:
            i += 1
    return results


if __name__ == "__main__":
    import sys
    import json

    text = open(sys.argv[1]).read()
    print(json.dumps(parse_people(text), indent=2, ensure_ascii=False))
