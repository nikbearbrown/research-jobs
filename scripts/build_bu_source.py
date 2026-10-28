#!/usr/bin/env python3
"""One-off helper: build a data/sources/<id>.json breadth-pass file from a
BU department people page already parsed with parse_bu_people.py.

Usage: python3 scripts/build_bu_source.py <target-id> <unit-name> <city> <text-file> <people-url> [<listing-url2> ...]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_bu_people import parse_people, is_non_lab_title  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def kebab(name):
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    return s


def main():
    target_id, unit, city, text_file, people_url = sys.argv[1:6]
    listing_urls = [people_url] + sys.argv[6:]
    text = Path(text_file).read_text()
    people = parse_people(text)

    labs = []
    non_lab = []
    for p in people:
        if is_non_lab_title(p["title"]):
            non_lab.append({"name": p["name"], "title": p["title"], "email": None,
                             "why": "Teaching-track/lecturer title, not an independent research lab."})
            continue
        lab_id = f"{target_id}-{kebab(p['name'])}"
        labs.append({
            "id": lab_id,
            "kind": "research-lab",
            "lab_name": None,
            "pi_name": p["name"],
            "pi_title": p["title"],
            "pi_email": None,
            "accepting_grad_students": None,
            "lab_website": None,
            "location": None,
            "phone": None,
            "admin_name": None,
            "admin_email": None,
            "research_summary": None,
            "member_count": None,
            "member_breakdown": None,
            "members_page_url": None,
            "join_page_url": None,
            "join_notes": None,
            "profile_url": p["profile_url"],
            "notes": "Breadth pass from department faculty directory; no email or lab site shown on the listing page itself.",
        })

    data = {
        "id": target_id,
        "institution": "Boston University",
        "unit": unit,
        "city": city,
        "checked_on": "2026-10-28",
        "listing_urls": listing_urls,
        "labs": labs,
        "non_lab_people": non_lab,
        "notes": None,
    }
    out = ROOT / "data" / "sources" / f"{target_id}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{target_id}: {len(labs)} labs, {len(non_lab)} non-lab -> {out}")


if __name__ == "__main__":
    main()
