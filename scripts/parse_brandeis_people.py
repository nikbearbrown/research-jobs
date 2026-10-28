#!/usr/bin/env python3
"""Parser for Brandeis department faculty-directory pages (confirmed on
biology, chemistry, physics, neuroscience, psychology): a repeating text
block per person --

    Name
    Title line(s) (1-3 lines, no phone/email pattern)
    phone (###-###-####)
    email (...@brandeis.edu)
    office location
    "Expertise:" (or "Expertise" on its own line, colon on the next)
    one-line summary
    ["Lab Website"]
    ["|"]
    ["ScholarWorks"]

"Lab Website" / "ScholarWorks" link targets are resolved separately from
scripts/fetch.py's outlinks section, in the same order they appear in the
body text, and zipped back onto the matching person by position.

Usage (library):
    from parse_brandeis_people import parse_people
    people = parse_people(text)
    # -> [{"name", "titles": [...], "phone", "email", "location",
    #      "summary", "lab_website", "scholarworks"}, ...]
"""
import re

PHONE_RE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
EMAIL_RE = re.compile(r"^[\w.\-+]+@brandeis\.edu$", re.I)
NAME_RE = re.compile(r"^[A-ZÀ-Ý][\w.\-'’]+(?: [A-Z][\w.\-'’]*\.?){1,4}$")
# Title-like phrases that happen to match NAME_RE's capitalized-words shape
# (e.g. "University Professor") -- never treat these as a person's name, and
# never accept an address/footer block as a person.
NAME_BLOCKLIST = {
    "University Professor", "Research Professor", "Brandeis University",
    "Department Chair", "Program Director", "Graduate Program",
    "Associate Chair", "Assistant Chair", "Research Assistant",
}
OUTLINK_RE = re.compile(r"^'(.+?)' -> (\S+)$")
BARE_URL_RE = re.compile(r"^https?://\S+$")


def _ordered_links(text, label):
    """Every outlink whose label equals `label`, in body order."""
    urls = []
    for line in text.splitlines():
        m = OUTLINK_RE.match(line)
        if m and m.group(1) == label:
            urls.append(m.group(2))
    return urls


def parse_people(text):
    lines = [ln.strip() for ln in text.splitlines()]
    # Only look at the body, not the nav/outlinks reference sections appended
    # by fetch.py -- cut at the first "--- mailto:" or "--- other links" marker.
    body_end = len(lines)
    for i, ln in enumerate(lines):
        if ln.startswith("--- mailto:") or ln.startswith("--- other links"):
            body_end = i
            break
    body = lines[:body_end]

    lab_links = iter(_ordered_links(text, "Lab Website"))
    scholar_links = iter(_ordered_links(text, "ScholarWorks"))

    people = []
    n = len(body)
    i = 0
    while i < n:
        if PHONE_RE.match(body[i]):
            # walk backwards over title lines to find the name
            j = i - 1
            titles = []
            while j >= 0 and body[j] and (not NAME_RE.match(body[j]) or body[j] in NAME_BLOCKLIST):
                titles.insert(0, body[j])
                j -= 1
                if len(titles) > 4:
                    break
            if j >= 0 and NAME_RE.match(body[j]) and body[j] not in NAME_BLOCKLIST:
                name = body[j]
                phone = body[i]
                email = body[i + 1] if i + 1 < n and EMAIL_RE.match(body[i + 1]) else None
                k = i + 2 if email else i + 1
                location = body[k] if k < n else None
                k += 1
                summary = None
                if k < n and body[k].lower().startswith("expertise"):
                    k += 1
                    if k < n and body[k].strip() == ":":
                        k += 1
                    if k < n:
                        summary = body[k]
                has_lab_site = False
                has_scholarworks = False
                look_ahead = body[k + 1:k + 4]
                if "Lab Website" in look_ahead:
                    has_lab_site = True
                if "ScholarWorks" in look_ahead:
                    has_scholarworks = True
                people.append({
                    "name": name,
                    "titles": titles,
                    "phone": phone,
                    "email": email,
                    "location": location,
                    "summary": summary,
                    "lab_website": next(lab_links, None) if has_lab_site else None,
                    "scholarworks": next(scholar_links, None) if has_scholarworks else None,
                })
            i += 1
        else:
            i += 1
    return people


if __name__ == "__main__":
    import sys
    import json

    text = open(sys.argv[1]).read()
    print(json.dumps(parse_people(text), indent=2, ensure_ascii=False))
