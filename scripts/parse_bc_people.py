#!/usr/bin/env python3
"""Parser for Boston College's shared department people-page template
(bc.edu/content/bc-web/schools/.../people.html), rendered via Playwright.

Pattern: a flat list of section headers (Faculty, Research Faculty, Adjunct
Faculty, Visiting Scholars, Postdoctoral Fellows, Graduate Students,
Research Scientists, Research Technicians, Emeritus/Retired Faculty,
Teaching Lab Administration & Office Staff -- not all departments have all
sections) followed by repeated person blocks: Name, Title, [phone],
[email], [office location] -- phone/location optional, in no fixed count.

Names are anchored using scripts/fetch.py's outlink list (reliable), then
the raw text between one name and the next is parsed for title/phone/
email/location.

Usage (library):
    from parse_bc_people import parse_people
    sections = parse_people(text)
    # -> {section_name: [{"name","title","phone","email","location","profile_url"}, ...]}
"""
import re

SECTION_HEADERS = [
    "Faculty", "Research Faculty", "Adjunct Faculty", "Visiting Scholars",
    "Postdoctoral Fellows", "Graduate Students", "Research Scientists",
    "Research Technicians", "Emeritus/Retired Faculty",
    "Teaching Lab Administration & Office Staff", "Staff & Administration",
]

PI_SECTIONS = {"Faculty", "Research Faculty"}

NON_PI_TITLE_RE = re.compile(
    r"\b(emeritus|visiting|adjunct|postdoc|lecturer|instructor|graduate student|"
    r"research associate|research technician|research assistant(?!\s+professor)|"
    r"research scientist|teaching|staff|administrator|coordinator|manager|"
    r"undergraduate)\b",
    re.I,
)
PI_TITLE_RE = re.compile(r"\bprofessor\b", re.I)


def is_pi_title(title):
    """Classify by title text, independent of section header (BC pages vary
    in whether section headers repeat before each section's content)."""
    if not title:
        return None  # unknown -- let caller fall back to section
    if NON_PI_TITLE_RE.search(title):
        return False
    if PI_TITLE_RE.search(title):
        return True
    return None


OUTLINK_RE = re.compile(r"^'(.+?)' -> (\S+)$")
PHONE_RE = re.compile(r"^\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$")
EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")


def _outlinks(text):
    pairs = []
    for line in text.splitlines():
        m = OUTLINK_RE.match(line)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


def parse_people(text):
    lines = [ln.strip() for ln in text.splitlines()]
    name_to_url = {}
    for name, url in _outlinks(text):
        if name in SECTION_HEADERS:
            continue
        if "/people/" in url and name not in name_to_url:
            name_to_url[name] = url

    # Find indices of body lines matching a known name, in order of first
    # appearance in the body (not the outlinks section at the end).
    name_positions = []
    for i, ln in enumerate(lines):
        if ln in name_to_url:
            name_positions.append((i, ln))

    # Determine, for each name occurrence, which section header precedes it
    # (scan backwards from the name to the nearest preceding section header
    # that is followed immediately by content, i.e. not the nav list at top).
    header_positions = [(i, ln) for i, ln in enumerate(lines) if ln in SECTION_HEADERS]

    def section_for(pos):
        best = None
        for hi, hname in header_positions:
            if hi < pos:
                best = hname
            else:
                break
        return best or "Faculty"

    sections = {}
    for idx, (pos, name) in enumerate(name_positions):
        end = name_positions[idx + 1][0] if idx + 1 < len(name_positions) else len(lines)
        block = [ln for ln in lines[pos + 1:end] if ln]
        title = None
        phone = None
        email = None
        location = None
        rest = []
        for ln in block:
            if EMAIL_RE.match(ln) and email is None:
                email = ln
            elif PHONE_RE.match(ln) and phone is None:
                phone = ln
            elif title is None:
                title = ln
            else:
                rest.append(ln)
        if rest:
            location = rest[0]
        sec = section_for(pos)
        sections.setdefault(sec, []).append({
            "name": name,
            "title": title,
            "phone": phone,
            "email": email,
            "location": location,
            "profile_url": name_to_url[name],
        })
    return sections


if __name__ == "__main__":
    import sys
    import json

    text = open(sys.argv[1]).read()
    print(json.dumps(parse_people(text), indent=2, ensure_ascii=False))
