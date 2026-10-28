#!/usr/bin/env python3
"""Parser for UMass Boston's repeating faculty-directory text block:
Lastname / FullName / 'Title:' / title / 'Department:' / dept / 'Email:' /
email / 'Expertise:' / ... -- confirmed on several umb.edu/science-mathematics
department faculty-staff pages.

Usage (library):
    from parse_umb_people import parse_people
    people = parse_people(text)
    # -> [{"name", "title", "dept", "email"}, ...]
"""


def parse_people(text):
    lines = text.splitlines()
    people = []
    n = len(lines)
    i = 0
    while i < n:
        if lines[i].strip() == "Title:" and i >= 1:
            name = lines[i - 1].strip()
            title = lines[i + 1].strip() if i + 1 < n else None
            dept = None
            email = None
            j = i + 2
            if j < n and lines[j].strip() == "Department:":
                dept = lines[j + 1].strip() if j + 1 < n else None
                j += 2
            if j < n and lines[j].strip() == "Email:":
                email = lines[j + 1].strip() if j + 1 < n else None
            people.append({"name": name, "title": title, "dept": dept, "email": email})
        i += 1
    return people


NON_LAB_TITLE_RE = None
import re  # noqa: E402

NON_LAB_TITLE_RE = re.compile(r"\b(lecturer|adjunct|emeritus|emerita|visiting|instructor)\b", re.I)


def is_non_lab_title(title):
    return bool(NON_LAB_TITLE_RE.search(title or ""))


if __name__ == "__main__":
    import sys
    import json

    text = open(sys.argv[1]).read()
    print(json.dumps(parse_people(text), indent=2, ensure_ascii=False))
