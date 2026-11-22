#!/usr/bin/env python3
"""Append new rows to data/targets.csv from a small JSON list, refusing duplicates.

    python3 scripts/add_targets.py rows.json [--dry-run]

rows.json is a list of objects with the targets.csv columns (id, name,
category, parent, city, start_url, people_url, careers_url, url_from,
priority, collect, listed_in, notes); status is set to `todo`. A row is
refused when its id is already in targets.csv, its start_url is already a
target's start_url, or its id is not lower kebab-case. Existing rows are never
changed. Used on 2026-11-22 to add the economics, business-school and policy
units the directory was missing (listed_in `econ-gap`).
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "targets.csv"


def canon(u):
    return re.sub(r"^(https?://)?(www\.)?", "", (u or "").strip(), flags=re.I).split("#")[0].rstrip("/").lower()


def main():
    new = json.loads(Path(sys.argv[1]).read_text())
    dry = "--dry-run" in sys.argv
    rows = list(csv.DictReader(open(PATH, newline="")))
    fields = list(rows[0].keys())
    ids = {r["id"] for r in rows}
    starts = {canon(r["start_url"]): r["id"] for r in rows if r["start_url"]}
    added = []
    for n in new:
        tid = n["id"]
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", tid):
            print(f"BAD ID {tid!r}")
            continue
        if tid in ids:
            print(f"SKIP {tid}: already a target")
            continue
        if canon(n["start_url"]) in starts:
            print(f"SKIP {tid}: start_url is already target {starts[canon(n['start_url'])]}")
            continue
        row = {f: n.get(f, "") for f in fields}
        row["status"] = "todo"
        rows.append(row)
        ids.add(tid)
        starts[canon(n["start_url"])] = tid
        added.append(tid)
    print(f"add_targets: {len(added)} added{' (dry run)' if dry else ''}: {', '.join(added)}")
    if added and not dry:
        with open(PATH, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")  # targets.csv uses CRLF
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
