#!/usr/bin/env python3
"""Sponsorship research, step 4: tier each employer and produce the per-lab
sponsorship fields.

The last column is named sponsorship_notes, not notes, because the lab list
already has a notes column and nothing existing may be overwritten.

Reads, all from sponsorship_research/:
  entities.csv, lab_entity_map.csv        (step 1)
  entity_role_profile.csv, entity_filing_summary.csv, step2_numbers.json (step 2)
  entity_policies.csv, policy_reading.csv (step 3; the reading is a person's
                                           judgment of each written policy)

Writes:
  entity_tiers.csv      one row per employer: tier, evidence labels, reasons
  lab_sponsorship.csv   one row per lab id with the 13 sponsorship columns
  summary.md

It does not touch data/. scripts/build.py merges lab_sponsorship.csv into
data/labs.csv and data/labs.json as extra columns the next time it runs.

    python3 scripts/sponsorship_step4_tiers.py
    python3 scripts/build.py
"""
import collections
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sponsorship_research")

ENTRY = ["research technician / lab technician",
         "research assistant / research associate (entry-level)",
         "computational / bioinformatics / data analyst",
         "software or ML engineer"]
SENIOR = ["postdoc / research fellow", "scientist / staff scientist", "faculty / instructor"]
CAP_EXEMPT_TYPES = {"university", "university-affiliated nonprofit/hospital",
                    "nonprofit research organization", "government research organization"}
SHORT = {ENTRY[0]: "technician", ENTRY[1]: "research assistant/associate",
         ENTRY[2]: "computational/data", ENTRY[3]: "software/ML",
         SENIOR[0]: "postdoc/fellow", SENIOR[1]: "scientist", SENIOR[2]: "faculty/instructor"}

# Tier thresholds (evidence from filings)
A_MIN_POSITIONS = 10      # new-employment positions, entry-level families, Level I-II, confidently classified
A_MIN_YEARS = 2           # ...seen in at least this many fiscal years
B_MIN_NEW = 20            # enough filings to judge
B_MIN_SENIOR_SHARE = 0.60
B_MAX_ENTRY_SHARE = 0.15

SPONSOR_FIELDS = ["legal_entity_name", "entity_type", "cap_exempt_likely", "sponsorship_tier",
                  "entry_level_roles_sponsored", "senior_roles_sponsored",
                  "new_employment_filings_3yr", "median_entry_wage", "policy_summary",
                  "policy_url", "evidence_as_of", "confidence", "sponsorship_notes"]


def read(name):
    return list(csv.DictReader(open(os.path.join(OUT, name), encoding="utf-8")))


def label(n):
    return "frequent" if n >= 10 else "occasional" if n >= 1 else "none seen"


def n(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def main():
    ents = {}
    for r in read("entities.csv"):
        ents.setdefault(r["entity_key"], r)
    prof = collections.defaultdict(dict)
    for r in read("entity_role_profile.csv"):
        prof[r["entity_key"]][r["role_family"]] = r
    summ = {r["entity_key"]: r for r in read("entity_filing_summary.csv")}
    pol = {r["legal_entity_name"]: r for r in read("entity_policies.csv")}
    reading = {r["legal_entity_name"]: r for r in read("policy_reading.csv")}
    nums = json.load(open(os.path.join(OUT, "step2_numbers.json")))
    log = [json.loads(l) for l in open(os.path.join(ROOT, "cache", "dol-lca", "filtered", "extract_log.jsonl"))]
    log = [l for l in log if l.get("state", nums["state"]) == nums["state"]]
    d_min = min(l["decision_min"] for l in log if l["decision_min"])
    d_max = max(l["decision_max"] for l in log if l["decision_max"])
    accessed = max((r["accessed_date"] for r in pol.values() if r["accessed_date"]), default="")
    as_of = "LCA decisions %s to %s (%s worksites); written policies read %s" % (d_min, d_max, nums["state"], accessed)

    # filings are keyed by entity_key; ragon shares a legal entity with mgh
    filing_key = {k: ("mgh" if k == "ragon" else k) for k in ents}

    tiers = {}
    for key, e in ents.items():
        fk = filing_key[key]
        s = summ.get(fk, {})
        new, entry_new = n(s.get("new_employment_positions")), n(s.get("entry_family_new_positions"))
        entry_conf, entry_fys = n(s.get("entry_new_positions_level_I_II_confident")), n(s.get("fiscal_years_with_confident_entry_filings"))
        senior_new = n(s.get("senior_family_new_positions"))
        name, etype = e["legal_entity_name"], e["entity_type"]
        rd = reading.get(name, {}).get("policy_reading", "unknown")
        p = pol.get(name, {})

        def fam_labels(fams):
            parts = []
            for f in fams:
                r = prof.get(fk, {}).get(f)
                cnt = n(r["new_employment_positions"]) if r else 0
                txt = "%s: %s" % (SHORT[f], label(cnt)) + (" (%d)" % cnt if cnt else "")
                if r and n(r["certified_filings"]) and n(r["filings_with_uncertain_classification"]) * 2 > n(r["certified_filings"]):
                    txt += " [most of these titles may not be entry-level here]" if f in ENTRY else " [classification uncertain]"
                parts.append(txt)
            return "; ".join(parts)

        ev_a = entry_conf >= A_MIN_POSITIONS and entry_fys >= A_MIN_YEARS
        ev_b = (new >= B_MIN_NEW and not ev_a and senior_new >= B_MIN_SENIOR_SHARE * new
                and entry_new <= B_MAX_ENTRY_SHARE * new)
        reasons, conflict = [], ""
        if etype == "for-profit":
            tier = "D"
            reasons.append("For-profit employer: cap-subject, the lottery applies.")
        elif etype not in CAP_EXEMPT_TYPES:
            tier = "unknown"
            reasons.append("Employer type not established.")
        else:
            by_filings = "A" if ev_a else "B" if ev_b else "C"
            if rd == "restrictive":
                tier = "B"
                reasons.append("Written policy is restrictive.")
                if ev_a:
                    conflict = "Written policy is restrictive but filings show %d entry-level new-employment positions at Level I-II across %d fiscal years. Policy decides: Tier B." % (entry_conf, entry_fys)
            elif rd == "permissive":
                tier = "A"
                reasons.append("Written policy allows staff positions.")
                if not ev_a:
                    conflict = "Written policy allows staff positions but filings show only %d entry-level new-employment positions at Level I-II (of %d new-employment positions in all). Policy decides: Tier A." % (entry_conf, new)
            else:
                tier = by_filings
                reasons.append("Written policy is %s, so filings decide." % ("mixed" if rd == "mixed" else "unknown or not public"))
            if by_filings == "A":
                reasons.append("Filings: %d entry-level new-employment positions at Level I-II, confidently classified, in %d fiscal years." % (entry_conf, entry_fys))
            elif by_filings == "B":
                reasons.append("Filings: %d of %d new-employment positions are postdoc, fellow, scientist or faculty titles; %d in entry-level families." % (senior_new, new, entry_new))
            else:
                reasons.append("Filings: %d new-employment positions in all, %d entry-level at Level I-II. Too few, or too mixed, to call." % (new, entry_conf))
        if key == "ragon":
            reasons.append("Tier taken from Mass General, the employer that files for Ragon worksites.")
        if etype == "government research organization":
            reasons.append("Federal agency: its own positions usually require citizenship.")
        if key == "ibm":
            reasons.append("Filings shown are IBM's Massachusetts filings as a whole, not the MIT-IBM lab.")

        if p.get("policy_status") in ("public", "partial") and reading.get(name):
            psum = "%s (%s): %s" % (rd.capitalize(), p["policy_status"] + " policy", reading[name]["reason"])
        elif reading.get(name):
            psum = "No written policy read (%s). %s" % (p.get("policy_status", "not checked"), reading[name]["reason"])
        else:
            psum = "Not looked up (not a cap-exempt employer type)."
        tiers[key] = {
            "entity_key": key, "legal_entity_name": name, "entity_type": etype,
            "cap_exempt_likely": "yes" if etype in CAP_EXEMPT_TYPES else "no" if etype == "for-profit" else "unknown",
            "sponsorship_tier": tier, "policy_reading": rd if etype in CAP_EXEMPT_TYPES else "",
            "tier_by_filings_alone": ("A" if ev_a else "B" if ev_b else "C") if etype in CAP_EXEMPT_TYPES else "",
            "entry_level_roles_sponsored": fam_labels(ENTRY),
            "senior_roles_sponsored": fam_labels(SENIOR),
            "new_employment_filings_3yr": new,
            "entry_new_positions_level_I_II_confident": entry_conf,
            "fiscal_years_with_entry_filings": entry_fys,
            "median_entry_wage": s.get("median_entry_wage_level_I_II_confident", ""),
            "policy_summary": psum, "policy_url": p.get("source_url", ""),
            "evidence_as_of": as_of, "mapping_confidence": e["confidence"],
            "tier_reasons": " ".join(reasons), "policy_vs_filings_conflict": conflict,
        }
    tier_rows = sorted(tiers.values(), key=lambda d: (d["sponsorship_tier"], -d["entry_new_positions_level_I_II_confident"], d["legal_entity_name"]))
    with open(os.path.join(OUT, "entity_tiers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tier_rows[0].keys()))
        w.writeheader()
        w.writerows(tier_rows)

    # ---- per-lab fields
    lab_rows, lab_tier = [], collections.Counter()
    for m in read("lab_entity_map.csv"):
        key = m["assigned_entity_key"]
        row = dict.fromkeys(SPONSOR_FIELDS, "")
        row["id"] = m["lab_id"]
        if key:
            t = tiers[key]
            for c in ("legal_entity_name", "entity_type", "cap_exempt_likely", "sponsorship_tier",
                      "entry_level_roles_sponsored", "senior_roles_sponsored", "new_employment_filings_3yr",
                      "median_entry_wage", "policy_summary", "policy_url", "evidence_as_of"):
                row[c] = t[c]
            row["confidence"] = m["confidence"]
            note = t["tier_reasons"]
            if t["policy_vs_filings_conflict"]:
                note += " " + t["policy_vs_filings_conflict"]
            if m["confidence"] != "high":
                note += " Hiring entity is the likely one, not confirmed for this lab."
            row["sponsorship_notes"] = note
            lab_tier[t["sponsorship_tier"]] += 1
        else:
            cands = [k for k in m["candidate_entity_keys"].split(" | ") if k]
            kinds = {tiers[k]["cap_exempt_likely"] for k in cands}
            row["cap_exempt_likely"] = "yes" if kinds == {"yes"} else "unknown"
            row["evidence_as_of"] = as_of
            row["confidence"] = "low"
            row["sponsorship_notes"] = ("Hiring entity not settled, so the employer fields are left blank. Candidates: "
                            + "; ".join("%s (Tier %s)" % (tiers[k]["legal_entity_name"], tiers[k]["sponsorship_tier"]) for k in cands)
                            + ". See sponsorship_research/ambiguous_labs.csv for what would settle it.")
            lab_tier["not assigned (ambiguous)"] += 1
        lab_rows.append(row)
    with open(os.path.join(OUT, "lab_sponsorship.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id"] + SPONSOR_FIELDS)
        w.writeheader()
        w.writerows(lab_rows)

    # ---- summary.md
    ent_tier = collections.Counter(t["sponsorship_tier"] for t in tiers.values())
    legal_tier = collections.Counter()
    seen = set()
    for t in tiers.values():
        if t["legal_entity_name"] not in seen:
            seen.add(t["legal_entity_name"])
            legal_tier[t["sponsorship_tier"]] += 1
    labs_by_entity = collections.Counter(r["legal_entity_name"] for r in lab_rows if r["legal_entity_name"])
    top = [t for t in tier_rows if t["cap_exempt_likely"] == "yes" and t["entity_key"] != "ragon"]
    top.sort(key=lambda d: -d["entry_new_positions_level_I_II_confident"])
    conflicts = [t for t in tier_rows if t["policy_vs_filings_conflict"]]
    L = []
    A = L.append
    A("# Sponsorship research: summary\n")
    A("## Executive summary\n")
    A("**What this is.** Each lab in `data/labs.csv` now carries 13 columns saying which legal employer it most likely hires through, whether that employer is exempt from the H-1B lottery, and what public evidence says about the kinds of positions it sponsors. Written %s.\n" % accessed)
    A("**The short answer.** Of %d labs, %d are assigned to an employer and %d are left unassigned because the row does not settle who the employer is. Almost every employer here is a cap-exempt type. The ones with repeated entry-level filings (Tier A) are mostly the hospitals and institutes, led by Dana-Farber; the big universities with a written policy (Harvard, MIT, Boston University) sponsor academic and senior research appointments only (Tier B).\n" % (len(lab_rows), len(lab_rows) - lab_tier["not assigned (ambiguous)"], lab_tier["not assigned (ambiguous)"]))
    A("**How far to trust it.** The tiers are evidence labels, not promises. A Tier A employer has filed for entry-level roles before; that does not mean a given lab will. A Tier C employer may sponsor freely and simply file little. Read the limits section before using a tier to advise anyone.\n")
    A("## Tier counts\n")
    A("| Tier | Meaning | Legal employers | Labs |\n|---|---|---|---|")
    meaning = {"A": "Sponsors entry-level staff (policy allows it, or repeated entry-level filings)",
               "B": "Academic or senior research appointments only",
               "C": "Cap-exempt type, too little evidence to tell",
               "D": "For-profit, cap-subject: the lottery applies",
               "unknown": "Employer type not established"}
    for t in ("A", "B", "C", "D", "unknown"):
        A("| %s | %s | %d | %d |" % (t, meaning[t], legal_tier[t], lab_tier[t]))
    A("| | Hiring entity not settled (employer fields blank) | | %d |" % lab_tier["not assigned (ambiguous)"])
    A("\nThe Ragon Institute is counted under Mass General's legal entity. Employers with zero labs are ones that appear only as a second affiliation on ambiguous labs.\n")
    A("**Tier A line.** At least %d new-employment positions in entry-level role families (technician, research assistant or associate, computational, software), at prevailing-wage Level I or II, with a confidently classified title, seen in at least %d fiscal years. **Tier B line.** At least %d new-employment positions, at least %d%% of them postdoc, fellow, scientist or faculty titles, and no more than %d%% in entry-level families. A written policy overrides both.\n" % (A_MIN_POSITIONS, A_MIN_YEARS, B_MIN_NEW, B_MIN_SENIOR_SHARE * 100, B_MAX_ENTRY_SHARE * 100))
    A("## Employers by entry-level sponsorship evidence\n")
    A("New-employment positions are the ones relevant to someone coming off OPT. Period: decisions %s to %s.\n" % (d_min, d_max))
    A("| Employer | Tier | Entry-level new positions, Level I-II | Fiscal years | All new positions | Median entry wage | Labs assigned | Entry-level roles |\n|---|---|---|---|---|---|---|---|")
    for t in top:
        if t["new_employment_filings_3yr"] == 0 and labs_by_entity.get(t["legal_entity_name"], 0) == 0:
            continue
        wage = ("$%s" % format(int(t["median_entry_wage"]), ",")) if t["median_entry_wage"] else ""
        A("| %s | %s | %d | %d | %d | %s | %d | %s |" % (t["legal_entity_name"], t["sponsorship_tier"], t["entry_new_positions_level_I_II_confident"], t["fiscal_years_with_entry_filings"], t["new_employment_filings_3yr"], wage, labs_by_entity.get(t["legal_entity_name"], 0), t["entry_level_roles_sponsored"]))
    A("\n## Where written policy and filings disagree\n")
    if conflicts:
        for t in conflicts:
            A("- **%s.** %s" % (t["legal_entity_name"], t["policy_vs_filings_conflict"]))
    else:
        A("None under the thresholds above.")
    A("\n__NOTES__\n")
    A("## Limits of this evidence\n")
    A("- **J-1 and O-1 hires are invisible.** An employer that puts research staff on J-1 files no LCA for them, so low counts can understate real hiring of international staff, and say nothing about H-1B willingness.")
    A("- **An LCA is not a hire.** It is a filing made before a petition. One LCA can cover several positions, and some certified LCAs are never used.")
    A("- **Absence is not refusal.** No filings in a role family does not prove an employer will not sponsor that role.")
    A("- **Written policies change,** and most of the hospitals keep theirs behind a login. Only %d of %d employers had a policy that could be read in full." % (sum(1 for r in pol.values() if r["policy_status"] == "public"), len(pol)))
    A("- **A pending federal rule may change cap exemption.** The H-1B reform rule under review (RIN 1615-AD00) is reported to revisit the definitions of affiliated nonprofits and research organizations. `cap_exempt_likely` reflects the rules as they stood on %s." % accessed)
    A("- **Primary worksite only.** The filter uses the primary worksite state in the main LCA file. Positions listed only in DOL's separate worksites file are not counted.")
    A("- **Titles are classified by keyword and occupation code.** %d certified filings fell into 'administrative / other' and %d carry a caution flag; both are listed in `unclassified_titles.csv`." % (nums["unclassified_certified_rows"], nums["flagged_certified_rows"]))
    A("- **The lab-to-employer step is the weakest link.** A lab is assigned to its listed institution unless the row names another employer. Many rows have no PI email, so some hospital-based labs are still counted under Harvard or Boston University.")
    A("\n## How to rerun, here or for another city\n")
    A("```bash\npython3 scripts/sponsorship_step1_entities.py                 # lab list -> entities, ambiguous labs, lab map\npython3 scripts/sponsorship_step2_lca.py extract --state MA   # slow; once per new LCA file\npython3 scripts/sponsorship_step2_lca.py profile --state MA\npython3 scripts/sponsorship_step3_policies.py                 # merge policy rows\npython3 scripts/sponsorship_step4_tiers.py                    # tiers, lab_sponsorship.csv, this file\npython3 scripts/build.py                                      # merges the columns into data/labs.csv and labs.json\n```\n")
    A("- **New LCA quarter:** download the file in a browser from the DOL performance-data page (the site refuses scripted requests), put it in `cache/dol-lca/`, and run from the `extract` line down.")
    A("- **Another state:** change `--state`. The extract keeps every H-1B row for that state, so nothing else in step 2's first stage changes.")
    A("- **Another lab list:** pass `--labs` to step 1 with the same column names, then add the new institutions to `ENTITIES`, `DEFAULT_ENTITY` and the signal tables in step 1, and to `ENTITY_MATCH` in step 2. Those three tables are the only Boston-specific code.")
    A("- **Policies** are read by a person or an agent, never inferred: add rows to `policy_parts/`, add a line to `policy_reading.csv`, and rerun steps 3 and 4.")
    A("- **Removing the columns:** delete `sponsorship_research/lab_sponsorship.csv` and run `scripts/build.py`. The 25 original columns are produced exactly as before.")
    notes_path = os.path.join(OUT, "summary_notes.md")
    notes = open(notes_path, encoding="utf-8").read().strip() if os.path.exists(notes_path) else ""
    text = "\n".join(L).replace("__NOTES__", notes)
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write(text + "\n")

    print("legal employers by tier:", dict(legal_tier))
    print("labs by tier:", dict(lab_tier))
    for t in tier_rows:
        print("  %-8s %-58s policy=%-11s filings=%s entryL12=%-4d new=%-4d labs=%d" % (
            t["sponsorship_tier"], t["legal_entity_name"][:58], t["policy_reading"], t["tier_by_filings_alone"],
            t["entry_new_positions_level_I_II_confident"], t["new_employment_filings_3yr"],
            labs_by_entity.get(t["legal_entity_name"], 0)))
    for t in conflicts:
        print("CONFLICT:", t["legal_entity_name"], "|", t["policy_vs_filings_conflict"])


if __name__ == "__main__":
    main()
