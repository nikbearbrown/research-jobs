#!/usr/bin/env python3
"""Sponsorship research, step 3: merge the written-policy records.

The policy rows themselves are read from pages by a person or an agent, never
inferred from filing data. They live in sponsorship_research/policy_parts/:

  part-*.csv              one row per employer, as first read
  verified-in-browser.csv rows re-read in a real browser after the first pass
                          was blocked; these replace the part-* row of the
                          same legal_entity_name

This script merges them into sponsorship_research/entity_policies.csv and
checks that every cap-exempt entity in entities.csv has a row.

    python3 scripts/sponsorship_step3_policies.py
"""
import csv
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sponsorship_research")
COLS = ["legal_entity_name", "policy_status", "eligible_categories", "exclusions",
        "fellowship_rule", "j1_default", "fee_payer", "policy_quote", "source_url",
        "accessed_date", "checker_notes"]
SKIP_TYPES = {"for-profit", "unknown"}


def main():
    rows = {}
    for p in sorted(glob.glob(os.path.join(OUT, "policy_parts", "part-*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            rows[r["legal_entity_name"]] = r
    v = os.path.join(OUT, "policy_parts", "verified-in-browser.csv")
    if os.path.exists(v):
        for r in csv.DictReader(open(v, encoding="utf-8")):
            rows[r["legal_entity_name"]] = r
    need = {}
    for e in csv.DictReader(open(os.path.join(OUT, "entities.csv"), encoding="utf-8")):
        if e["entity_type"] not in SKIP_TYPES:
            need[e["legal_entity_name"]] = e["entity_type"]
    for name, etype in need.items():
        if name not in rows:
            rows[name] = dict.fromkeys(COLS, "")
            rows[name].update(legal_entity_name=name, policy_status="not checked",
                              checker_notes="No policy page was looked for (%s)." % etype)
    with open(os.path.join(OUT, "entity_policies.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for name in sorted(rows):
            w.writerow(rows[name])
    by = {}
    for r in rows.values():
        by[r["policy_status"]] = by.get(r["policy_status"], 0) + 1
    print(len(rows), "policy rows;", by)
    extra = sorted(set(rows) - set(need))
    if extra:
        print("rows not matching a cap-exempt entity name in entities.csv:", extra)


if __name__ == "__main__":
    main()
