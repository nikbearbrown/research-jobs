#!/usr/bin/env python3
"""Count data/labs.csv rows by institution and by unit, for a family of units.

    python3 scripts/count_units.py [--csv data/labs.csv] [--family econ]

Prints two tables: rows per institution (all of labs.csv), and rows per
(institution, unit) for the units of one family. The `econ` family is the
economics, business-school and policy units: every targets.csv row whose id
or name matches ECON below, plus every row with listed_in `econ-gap`. A row of
labs.csv belongs to a unit when its id starts with that target's id. Used on
2026-11-22 for the before/after counts of the econ-gap pass.
"""
import argparse
import collections
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ECON = re.compile(r"econ|business|hbs|sloan|questrom|kennedy|^hks-|fletcher|heller|carroll|d.amore|dmsb|policy|workforce|"
                  r"work and employment|digital economy|collective intelligence|future of work|stone-center|nber", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(ROOT / "data" / "labs.csv"))
    ap.add_argument("--family", default="econ")
    a = ap.parse_args()
    labs = list(csv.DictReader(open(a.csv, newline="")))
    targets = list(csv.DictReader(open(ROOT / "data" / "targets.csv", newline="")))
    fam = sorted((t for t in targets if ECON.search(t["id"]) or ECON.search(t["name"]) or t.get("listed_in") == "econ-gap"),
                 key=lambda t: -len(t["id"]))
    print(f"labs.csv rows: {len(labs)}")
    print("\nRows per institution")
    for inst, n in collections.Counter(r["institution"] for r in labs).most_common():
        print(f"{n:6d}  {inst}")
    per = collections.Counter()
    for r in labs:
        t = next((t for t in fam if r["id"] == t["id"] or r["id"].startswith(t["id"] + "-")), None)
        if t:
            per[(r["institution"], t["id"])] += 1
    names = {t["id"]: t["name"] for t in fam}
    print(f"\nRows per unit, {a.family} family ({sum(per.values())} rows in {len(per)} units; "
          f"{len(fam) - len(per)} family targets have no rows)")
    for (inst, tid), n in sorted(per.items()):
        print(f"{n:4d}  {inst} | {tid} | {names[tid]}")
    print("\nFamily targets with no rows: " + ", ".join(sorted(t["id"] for t in fam if not any(k[1] == t["id"] for k in per))))


if __name__ == "__main__":
    main()
