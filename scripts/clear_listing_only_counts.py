#!/usr/bin/env python3
"""Clear member counts of 1 that came from a listing page naming only the PI.

Northeastern's College of Science has a page per lab
(cos.northeastern.edu/nucos-faculty-lab/<lab>/). An earlier pass counted the
people named on that page and, where it names only the PI, recorded
member_count 1 with the breakdown "1 PI + 0 other member(s) listed on the lab
page". That page is a directory entry, not a roster, so the 1 is not the
lab's size (the Lewis Lab was recorded as one person). This sets
member_count, member_breakdown and members_page_url back to null for exactly
those records and says so in notes. The lab's own website, where one is
recorded, can then be read for a real count with
`depth_pass.py prep-sizes --only-note "member_count cleared"`.

    python3 scripts/clear_listing_only_counts.py [--dry-run]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from depth_pass import append_note, save  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MARK = "+ 0 other member"


def main():
    dry = "--dry-run" in sys.argv
    cleared = with_site = 0
    for path in sorted((ROOT / "data" / "sources").glob("northeastern-*.json")):
        data = json.loads(path.read_text())
        n = 0
        for lab in data["labs"]:
            breakdown = lab.get("member_breakdown")
            if lab.get("member_count") != 1 or not isinstance(breakdown, str) or MARK not in breakdown:
                continue
            page = lab.get("members_page_url")
            lab["member_count"] = None
            lab["member_breakdown"] = None
            lab["members_page_url"] = None
            append_note(lab, f"member_count cleared: the earlier value of 1 came from the College of Science page for this lab "
                             f"({page}), which names only the PI and is not a roster.")
            n += 1
            with_site += bool(lab.get("lab_website"))
        if n:
            cleared += n
            print(f"{path.name}: {n}", flush=True)
            if not dry:
                save(path, data)
    print(f"clear_listing_only_counts: cleared {cleared} ({with_site} have a lab website to read)"
          + (" (dry run, nothing written)" if dry else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
