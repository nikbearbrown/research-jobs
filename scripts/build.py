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


VALID_KINDS = {"research-lab", "core-facility", "faculty-no-lab"}

# Optional extra columns: H-1B sponsorship evidence per lab, produced by
# scripts/sponsorship_step4_tiers.py. Merged in by lab id when the file exists;
# delete the file and rebuild to drop the columns. See sponsorship_research/summary.md.
SPONSORSHIP = ROOT / "sponsorship_research" / "lab_sponsorship.csv"


def load_sponsorship():
    if not SPONSORSHIP.exists():
        return [], {}
    with open(SPONSORSHIP, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    cols = [c for c in rows[0].keys() if c != "id"] if rows else []
    clash = set(cols) & set(FIELDS)
    if clash:
        raise SystemExit(f"sponsorship columns would overwrite existing ones: {sorted(clash)}")
    return cols, {r["id"]: r for r in rows}


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
            if row.get("kind") not in VALID_KINDS:
                raise SystemExit(f"{row['id']}: invalid kind {row.get('kind')!r} (expected one of {sorted(VALID_KINDS)})")
            row["size"] = size_of(row)
            labs.append(row)
    ids = [l["id"] for l in labs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate ids: {sorted(dupes)}")
    extra_cols, extra = load_sponsorship()
    for lab in labs:
        row = extra.get(lab["id"], {})
        for c in extra_cols:
            lab[c] = row.get(c) or None
    (ROOT / "data" / "labs.json").write_text(json.dumps(labs, indent=2, ensure_ascii=False) + "\n")
    # labs.csv is a list of real labs: faculty-no-lab entries (clinical-only
    # faculty, lecturers, anyone with no lab of their own) are recorded in
    # labs.json for completeness but left out of the CSV.
    csv_labs = [l for l in labs if l.get("kind") != "faculty-no-lab"]
    with open(ROOT / "data" / "labs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS + extra_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(csv_labs)
    counts = {}
    for l in labs:
        counts[l["size"]] = counts.get(l["size"], 0) + 1
    kind_counts = {}
    for l in labs:
        kind_counts[l.get("kind")] = kind_counts.get(l.get("kind"), 0) + 1
    print(f"{len(labs)} entries ({len(csv_labs)} in labs.csv); by size: {counts}; by kind: {kind_counts}")
    if extra_cols:
        print(f"merged {len(extra_cols)} sponsorship columns for {sum(1 for l in labs if l['id'] in extra)} labs")


if __name__ == "__main__":
    main()
