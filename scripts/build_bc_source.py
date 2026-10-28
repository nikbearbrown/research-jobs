#!/usr/bin/env python3
"""One-off helper: build a data/sources/<id>.json breadth-pass file from a
BC department people page parsed with parse_bc_people.py.

Usage: python3 scripts/build_bc_source.py <target-id> <unit-name> <people-url>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402
from parse_bc_people import parse_people, PI_SECTIONS, is_pi_title  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def kebab(name):
    s = re.sub(r"[^\w\s-]", "", name).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    return s


def main():
    target_id, unit, people_url = sys.argv[1:4]
    result = fetch(people_url, render=True)
    sections = parse_people(result["text"])

    labs = []
    non_lab = []
    for sec, people in sections.items():
        for p in people:
            pi_by_title = is_pi_title(p["title"])
            is_pi = pi_by_title if pi_by_title is not None else (sec in PI_SECTIONS)
            if is_pi:
                lab_id = f"{target_id}-{kebab(p['name'])}"
                labs.append({
                    "id": lab_id,
                    "kind": "research-lab",
                    "lab_name": None,
                    "pi_name": p["name"],
                    "pi_title": p["title"],
                    "pi_email": p["email"],
                    "accepting_grad_students": None,
                    "lab_website": None,
                    "location": p["location"],
                    "phone": p["phone"],
                    "admin_name": None,
                    "admin_email": None,
                    "research_summary": None,
                    "member_count": None,
                    "member_breakdown": None,
                    "members_page_url": None,
                    "join_page_url": None,
                    "join_notes": None,
                    "profile_url": p["profile_url"],
                    "notes": f"Breadth pass from the department's own people page ({sec} section); lab website/member count/join info not yet read (later per-PI pass).",
                })
            else:
                non_lab.append({
                    "name": p["name"], "title": p["title"], "email": p["email"],
                    "why": f"{sec} — not an independent PI-led research track.",
                })

    data = {
        "id": target_id,
        "institution": "Boston College",
        "unit": unit,
        "city": "Chestnut Hill, MA",
        "checked_on": "2026-10-28",
        "listing_urls": [people_url],
        "labs": labs,
        "non_lab_people": non_lab,
        "notes": None,
    }
    out = ROOT / "data" / "sources" / f"{target_id}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{target_id}: {len(labs)} labs, {len(non_lab)} non-lab -> {out}")


if __name__ == "__main__":
    main()
