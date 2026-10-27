"""Merge every data/sources/*.json into data/labs.json and data/labs.csv.

Run from the repo root:  python3 scripts/build.py
"""
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SMALL, MEDIUM = 10, 20  # member_count thresholds (inclusive)

FIELDS = ["id", "kind", "size", "institution", "unit", "city", "lab_name", "pi_name",
          "pi_title", "pi_email", "accepting_grad_students", "admin_name", "admin_email",
          "phone", "location", "lab_website", "members_page_url", "member_count",
          "member_breakdown", "join_page_url", "join_notes", "research_summary",
          "profile_url", "notes", "checked_on"]


def size_of(lab):
    if lab.get("kind") != "research-lab":
        return "n/a"
    n = lab.get("member_count")
    if n is None:
        return "unknown"
    return "small" if n <= SMALL else "medium" if n <= MEDIUM else "large"


def main():
    labs = []
    for f in sorted((ROOT / "data" / "sources").glob("*.json")):
        src = json.loads(f.read_text())
        for lab in src["labs"]:
            row = {k: src.get(k) for k in ("institution", "unit", "city", "checked_on")}
            row.update(lab)
            row["size"] = size_of(row)
            labs.append(row)
    ids = [l["id"] for l in labs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate ids: {sorted(dupes)}")
    (ROOT / "data" / "labs.json").write_text(json.dumps(labs, indent=2, ensure_ascii=False) + "\n")
    with open(ROOT / "data" / "labs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(labs)
    counts = {}
    for l in labs:
        counts[l["size"]] = counts.get(l["size"], 0) + 1
    print(f"{len(labs)} entries; by size: {counts}")


if __name__ == "__main__":
    main()
