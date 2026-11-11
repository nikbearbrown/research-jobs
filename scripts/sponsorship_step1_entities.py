#!/usr/bin/env python3
"""Sponsorship research, step 1: inventory and entity mapping.

Reads the lab list (read-only) and writes three files to sponsorship_research/:

  entities.csv         one row per legal employer that a lab in the list hires
                       through, or may hire through
  ambiguous_labs.csv   labs whose hiring entity cannot be told from the row
  lab_entity_map.csv   every lab id -> assigned entity (or blank), candidates,
                       confidence. Later steps join on this.

Nothing here fetches a page or edits data/. Legal names come from the ENTITIES
table below; each one says where the name came from and how sure it is.

Rerun for another city: pass --labs with a CSV that has the same columns
(id, institution, unit, pi_title, pi_email, lab_name, location, lab_website,
notes) and extend ENTITIES / DEFAULT_ENTITY / the signal tables for the new
institutions.

    python3 scripts/sponsorship_step1_entities.py
"""
import argparse
import collections
import csv
import os
import re
from urllib.parse import urlparse

UNI = "university"
AFF = "university-affiliated nonprofit/hospital"
NRO = "nonprofit research organization"
GOV = "government research organization"
FP = "for-profit"

# key -> (legal_entity_name, entity_type, confidence, source_or_reasoning)
# "USCIS FY2023" = the employer name as it appears in the USCIS H-1B Employer
# Data Hub fiscal 2023 export (a local copy, partial). USCIS shortens names, so
# it confirms the employer exists and files, not the exact legal spelling.
ENTITIES = {
    "harvard": ("President and Fellows of Harvard College", UNI, "high",
                "Legal name supplied by the owner and used by Harvard on filings; USCIS FY2023 lists it as HARVARD UNIVERSITY, Cambridge MA. Caution: Harvard Medical School department listings include some hospital-based faculty. Labs are flagged only when the row names a hospital; about 300 Harvard-listed labs have no PI email recorded, so some hospital-based labs are probably still counted here."),
    "mit": ("Massachusetts Institute of Technology", UNI, "high",
            "USCIS FY2023: MASSACHUSETTS INST OF TECHNOLOGY, Cambridge MA. Koch, McGovern, Picower, CSAIL, Media Lab, Haystack and Lincoln Laboratory are parts of MIT, not separate employers."),
    "bu": ("Trustees of Boston University", UNI, "high",
           "USCIS FY2023: TRUSTEES OF BOSTON UNIVERSITY, Boston MA. Caution: clinical sections on the medical campus (Pulmonary Center, Whitaker, Evans Center and similar) may employ staff through Boston Medical Center; labs are flagged only when the row names BMC, and 901 BU labs have no PI email recorded."),
    "tufts": ("Trustees of Tufts College", UNI, "high",
              "Corporate name of Tufts University (from general knowledge, not read from a filing). USCIS FY2023 lists TUFTS UNIVERSITY, Medford and Boston MA. Step 2 should accept either spelling."),
    "northeastern": ("Northeastern University", UNI, "high",
                     "USCIS FY2023: NORTHEASTERN UNIVERSITY, Boston MA."),
    "bc": ("Trustees of Boston College", UNI, "high",
           "Corporate name of Boston College (general knowledge). USCIS FY2023 lists BOSTON COLLEGE, Chestnut Hill MA."),
    "brandeis": ("Brandeis University", UNI, "high",
                 "USCIS FY2023: BRANDEIS UNIVERSITY, Waltham MA."),
    "umb": ("University of Massachusetts (Boston campus)", UNI, "medium",
            "Public university. Not confirmed how the Boston campus is named on filings (likely 'University of Massachusetts Boston'); the partial USCIS FY2023 file shows only UMASS CHAN MEDICAL SCHOOL. Step 2 must find the name by Boston worksite address."),
    "dfci": ("Dana-Farber Cancer Institute, Inc.", AFF, "high",
             "USCIS FY2023: DANA FARBER CANCER INSTITUTE, Boston MA. Harvard Medical School teaching affiliate."),
    "mgh": ("The General Hospital Corporation", AFF, "high",
            "Legal name supplied by the owner (does business as Massachusetts General Hospital). USCIS FY2023 shows MASSACHUSETTS GENERAL HOSPITAL/MGPO with a Somerville MA address, which is Mass General Brigham's head office, so Step 2 should not expect a Boston employer address."),
    "bwh": ("The Brigham and Women's Hospital, Inc.", AFF, "high",
            "USCIS FY2023: BRIGHAM AND WOMEN S HOSPITAL, Somerville and Boston MA. Exact corporate spelling is from general knowledge."),
    "mee": ("Massachusetts Eye and Ear Infirmary", AFF, "high",
            "USCIS FY2023: MASSACHUSETTS EYE AND EAR INFIRMARY, Somerville MA. Includes Schepens Eye Research Institute."),
    "mclean": ("The McLean Hospital Corporation", AFF, "medium",
               "USCIS FY2023 lists MCLEAN HOSPITAL, Belmont MA. Corporate spelling from general knowledge, not confirmed."),
    "spaulding": ("The Spaulding Rehabilitation Hospital Corporation", AFF, "medium",
                  "USCIS FY2023 lists SPAULDING REHABILITATION HOSPITAL, Somerville MA. Corporate spelling from general knowledge, not confirmed."),
    "mgb": ("Mass General Brigham Incorporated", AFF, "medium",
            "USCIS FY2023: MASS GENERAL BRIGHAM INCORPORATED, Somerville MA. The parent system. Research labs normally hire through the member hospital, so this is a fallback name, not the expected filer."),
    "bidmc": ("Beth Israel Deaconess Medical Center, Inc.", AFF, "high",
              "USCIS FY2023: BETH ISRAEL DEACONESS MEDICAL CENTER INC, Boston MA."),
    "joslin": ("Joslin Diabetes Center, Inc.", AFF, "medium",
               "Corporate name from general knowledge. No row in the partial USCIS FY2023 file. Joslin joined Beth Israel Lahey Health in 2022, so newer filings may come from a different entity; Step 2 should check by the One Joslin Place address."),
    "hsl": ("Hebrew Rehabilitation Center", AFF, "medium",
            "USCIS FY2023: HEBREW REHABILITATION CTR, Roslindale MA, the address of the Marcus Institute. Hebrew SeniorLife, Inc. is the parent; which of the two files is not confirmed."),
    "ragon": ("The General Hospital Corporation", AFF, "medium",
              "The Ragon Institute's careers page says it 'is administratively managed through Mass General' and sends applicants to the Mass General careers site (read 2026-11-10). Step 2 found The General Hospital Corporation filing LCAs for worksites at 600 Main Street and 400 Technology Square, Cambridge (the Ragon addresses), one with the job title 'Research Fellow, MGH Ragon Institute', and no employer named Ragon in the Massachusetts filings. No page states the employer of record outright, so this stays medium."),
    "forsyth": ("The Forsyth Institute", NRO, "medium",
                "USCIS FY2023: FORSYTH INSTITUTE, Cambridge MA. Renamed ADA Forsyth Institute in 2023, so newer filings may carry the new name."),
    "whitehead": ("Whitehead Institute for Biomedical Research", NRO, "high",
                  "USCIS FY2023: WHITEHEAD INSTITUTE FOR BIOMEDICAL RESEARCH, Cambridge MA. Independent nonprofit affiliated with MIT."),
    # Not listed as institutions in the lab list; they appear only as a second
    # affiliation on some labs.
    "broad": ("The Broad Institute, Inc.", NRO, "high",
              "Legal name supplied by the owner. USCIS FY2023: BROAD INSTITUTE, Cambridge MA. Not listed as an institution in the lab list."),
    "bch": ("The Children's Hospital Corporation", AFF, "high",
            "Legal name supplied by the owner (does business as Boston Children's Hospital). USCIS FY2023: CHILDRENS HOSPITAL CORPORATION, Boston MA. Not listed as an institution in the lab list."),
    "bmc": ("Boston Medical Center Corporation", AFF, "high",
            "USCIS FY2023: BOSTON MEDICAL CENTER CORPORATION, Boston MA. Teaching hospital of BU's medical school. Not listed as an institution in the lab list."),
    "hhmi": ("Howard Hughes Medical Institute", NRO, "high",
             "USCIS FY2023: HOWARD HUGHES MEDICAL INSTITUTE HHMI, Chevy Chase MD. HHMI Investigators are HHMI employees and some of their lab staff are too; the employer address is Maryland even when the lab is in Massachusetts."),
    "tuftsmc": ("Tufts Medical Center, Inc.", AFF, "medium",
                "USCIS FY2023 lists TUFTS MEDICAL CENTER, Boston MA. Corporate spelling from general knowledge."),
    "va": ("U.S. Department of Veterans Affairs (VA Boston Healthcare System)", GOV, "low",
           "Federal agency. VA research staff are often paid through a separate nonprofit (Boston VA Research Institute) or the affiliated university; which one applies to a given lab is not known. Federal jobs themselves usually require citizenship."),
    "usda": ("U.S. Department of Agriculture, Agricultural Research Service", GOV, "low",
             "Federal agency that funds the HNRCA at Tufts. Federal positions usually require citizenship; most HNRCA scientists are believed to be Tufts employees, not confirmed."),
    "ibm": ("International Business Machines Corporation", FP, "medium",
            "The MIT-IBM Watson AI Lab is a joint lab; IBM researchers in it are IBM employees. Cap-subject."),
    "emerson": ("Emerson Hospital", "unknown", "low",
                "One BU lab's PI uses an emersonhosp.org address. Legal name and any university affiliation not checked."),
}

DEFAULT_ENTITY = {
    "Boston University": "bu",
    "MIT": "mit",
    "Harvard": "harvard",
    "Harvard University": "harvard",
    "Rowland Institute at Harvard": "harvard",
    "Tufts University": "tufts",
    "Tufts University / USDA Agricultural Research Service": "tufts",
    "Northeastern University": "northeastern",
    "Boston College": "bc",
    "Brandeis University": "brandeis",
    "UMass Boston": "umb",
    "Dana-Farber Cancer Institute": "dfci",
    "Massachusetts General Hospital": "mgh",
    "Mass Eye and Ear": "mee",
    "Beth Israel Deaconess Medical Center": "bidmc",
    "Joslin Diabetes Center": "joslin",
    "Hebrew SeniorLife": "hsl",
    "Ragon Institute of Mass General Brigham, MIT and Harvard": "ragon",
    "Forsyth Institute": "forsyth",
    "Whitehead Institute for Biomedical Research": "whitehead",
    "Mass General Brigham": None,   # a system, not one employer: decided per lab
}

# ragon and mgh are the same legal entity today (by assumption); treat signals
# for one as agreeing with the other.
SAME_LEGAL = {"ragon": "mgh"}

EMAIL_SUFFIX = [  # checked in order; first match wins
    ("mgh.harvard.edu", "mgh"), ("bwh.harvard.edu", "bwh"),
    ("childrens.harvard.edu", "bch"), ("tch.harvard.edu", "bch"),
    ("dfci.harvard.edu", "dfci"), ("jimmy.harvard.edu", "dfci"),
    ("bidmc.harvard.edu", "bidmc"), ("hsl.harvard.edu", "hsl"),
    ("joslin.harvard.edu", "joslin"), ("meei.harvard.edu", "mee"),
    ("mclean.harvard.edu", "mclean"), ("broadinstitute.org", "broad"),
    ("wi.mit.edu", "whitehead"), ("partners.org", "mgb"), ("mgb.org", "mgb"),
    ("massgeneralbrigham.org", "mgb"), ("va.gov", "va"), ("bmc.org", "bmc"),
    ("forsyth.org", "forsyth"), ("emersonhosp.org", "emerson"),
    ("tuftsmedicalcenter.org", "tuftsmc"), ("tuftsmedicine.org", "tuftsmc"),
    ("ibm.com", "ibm"),
    ("harvard.edu", "harvard"), ("mit.edu", "mit"), ("bu.edu", "bu"),
    ("tufts.edu", "tufts"), ("northeastern.edu", "northeastern"),
    ("neu.edu", "northeastern"), ("bc.edu", "bc"), ("brandeis.edu", "brandeis"),
    ("umb.edu", "umb"),
]

SITE_SUFFIX = [
    ("mgh.harvard.edu", "mgh"), ("massgeneral.org", "mgh"), ("mghcteu.org", "mgh"),
    ("mghocd.org", "mgh"), ("mol.bio", "mgh"),
    ("bwh.harvard.edu", "bwh"), ("brighamandwomens.org", "bwh"),
    ("bwhneurosciences.org", "bwh"), ("spl.harvard.edu", "bwh"),
    ("eye.hms.harvard.edu", "mee"), ("masseyeandear.org", "mee"),
    ("mcleanhospital.org", "mclean"), ("spauldingrehab.org", "spaulding"),
    ("childrenshospital.org", "bch"), ("tch.harvard.edu", "bch"),
    ("dana-farber.org", "dfci"), ("dfci.harvard.edu", "dfci"),
    ("bidmc.org", "bidmc"), ("bidmc.harvard.edu", "bidmc"),
    ("joslin.org", "joslin"), ("ragoninstitute.org", "ragon"),
    ("broadinstitute.org", "broad"), ("wi.mit.edu", "whitehead"),
    ("bmc.org", "bmc"), ("tuftsmedicalcenter.org", "tuftsmc"),
]

# Searched in pi_title, lab_name, location and unit. Notes are used only for the
# scraper's own "Hospital (from page text): X" line, because free-text notes
# mention other institutions for unrelated reasons.
TEXT_PATTERNS = [
    ("mgh", r"Massachusetts General Hospital|Mass General Hospital|\bMGH\b|Mass General(?! Brigham)"),
    ("bwh", r"Brigham and Women|Brigham & Women|\bBWH\b"),
    ("mee", r"Mass(achusetts)? Eye and Ear|Schepens"),
    ("mclean", r"McLean Hospital"),
    ("spaulding", r"Spaulding"),
    ("bch", r"Boston Children'?s|Children'?s Hospital"),
    ("dfci", r"Dana-Farber"),
    ("bidmc", r"Beth Israel"),
    ("joslin", r"Joslin"),
    ("broad", r"Broad Institute"),
    ("whitehead", r"Whitehead Institute"),
    ("ragon", r"Ragon Institute"),
    ("bmc", r"Boston Medical Center"),
    ("va", r"\bVA Boston|Veterans Affairs"),
    ("tuftsmc", r"Tufts Medical Center"),
    ("harvard", r"Wyss Institute"),   # Wyss staff are Harvard employees
]
HHMI_TITLE = r"HHMI Investigator|Investigator[^;]{0,25}Howard Hughes|Howard Hughes Medical Institute Investigator|HHMI Freeman Hrabowski"
IBM_UNIT = r"MIT-IBM"

MGB_HOSPITALS = ["mgh", "bwh", "mee", "mclean", "spaulding"]

# Units where the unit itself is shared between two employers.
UNIT_CANDIDATES = {
    "Center for Regenerative Medicine (CReM)": (["bu", "bmc"], "CReM is a joint center of Boston University and Boston Medical Center."),
    "Jean Mayer USDA Human Nutrition Research Center on Aging (HNRCA)": (["tufts", "usda"], "HNRCA is a USDA Agricultural Research Service center operated at Tufts."),
    "MIT-IBM Watson AI Lab (MIT-IBM Computing Research Lab)": (["mit", "ibm"], "Joint MIT and IBM lab; a position may be on either payroll."),
}

RESOLVE = {
    "mgb-none": "Open the lab's own page or its Mass General Brigham research page and read which hospital it names; a PI email at mgh.harvard.edu or bwh.harvard.edu also settles it.",
    "hospital": "Check where the lab physically sits and which HR system posts its jobs (Harvard careers vs. the hospital's Mass General Brigham / Children's / Dana-Farber / BIDMC careers site). A PI email at the hospital usually means the hospital is the employer.",
    "hhmi": "Ask the lab or read a current job posting: HHMI-funded lab staff are posted on hhmi.org careers; other staff are posted by the host institution.",
    "broad": "Check whether the PI is a Broad core institute member (lab at the Broad, staff on Broad payroll) or an associate member (lab and payroll at the home institution). The Broad's people page says which.",
    "whitehead": "Whitehead members' labs sit at the Whitehead and staff are Whitehead employees; the same lab usually also appears in this list under the Whitehead Institute. Confirm on the lab's job postings.",
    "ragon": "Check the Ragon Institute's careers page for the employer named on postings, and where this PI's lab sits (Ragon building vs. the home department).",
    "bmc": "Check whether the lab's staff postings are on BU's or Boston Medical Center's careers site.",
    "va": "Ask the lab which payroll research staff are on: the university, the VA, or the VA's research nonprofit.",
    "unit": "Ask the unit's administrator which organization is the employer of record for research staff.",
    "other": "Check the lab's current job postings for the employer of record.",
}


def norm_key(k):
    return SAME_LEGAL.get(k, k)


def email_entity(email):
    e = (email or "").strip().lower()
    if "@" not in e:
        return None
    d = e.split("@")[-1]
    for suf, key in EMAIL_SUFFIX:
        if d == suf or d.endswith("." + suf):
            return key
    return None


def site_entity(url):
    if not url:
        return None
    h = urlparse(url).netloc.lower()
    if h.startswith("www."):
        h = h[4:]
    for suf, key in SITE_SUFFIX:
        if h == suf or h.endswith("." + suf):
            return key
    return None


def signals(row):
    """Return {entity_key: [evidence strings]} for one lab row."""
    out = collections.defaultdict(list)
    k = email_entity(row.get("pi_email"))
    if k:
        out[k].append("PI email " + row["pi_email"].split("@")[-1])
    k = site_entity(row.get("lab_website"))
    if k:
        out[k].append("lab site " + urlparse(row["lab_website"]).netloc)
    text = " | ".join(row.get(f) or "" for f in ("pi_title", "lab_name", "location", "unit"))
    for key, pat in TEXT_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            out[key].append('text "%s"' % m.group(0))
    m = re.search(r"Hospital \(from page text\):\s*([^.]+)", row.get("notes") or "")
    if m:
        named = m.group(1)
        for key, pat in TEXT_PATTERNS:
            if re.search(pat, named, re.I):
                out[key].append('page names "%s"' % named.strip())
    if re.search(HHMI_TITLE, row.get("pi_title") or "", re.I):
        out["hhmi"].append("PI title names HHMI")
    return out


def resolve_hint(cands):
    s = set(cands)
    if "hhmi" in s:
        return RESOLVE["hhmi"]
    if "broad" in s:
        return RESOLVE["broad"]
    if "whitehead" in s:
        return RESOLVE["whitehead"]
    if "ragon" in s:
        return RESOLVE["ragon"]
    if "va" in s:
        return RESOLVE["va"]
    if "bmc" in s and "bu" in s:
        return RESOLVE["bmc"]
    if s & {"mgh", "bwh", "bch", "dfci", "bidmc", "mee", "mclean", "spaulding", "joslin", "tuftsmc", "hsl"}:
        return RESOLVE["hospital"]
    return RESOLVE["other"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument("--labs", default=os.path.join(root, "data", "labs.csv"))
    ap.add_argument("--out", default=os.path.join(root, "sponsorship_research"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = list(csv.DictReader(open(a.labs, encoding="utf-8")))

    lab_map, ambiguous = [], []
    assigned_count = collections.Counter()        # (institution, entity) -> labs
    candidate_count = collections.Counter()       # entity -> labs where it is only a candidate
    unknown_inst = collections.Counter()

    for r in rows:
        inst, unit = r["institution"], r["unit"]
        if inst not in DEFAULT_ENTITY:
            unknown_inst[inst] += 1
        default = DEFAULT_ENTITY.get(inst)
        sig = signals(r)
        keys = {norm_key(k) for k in sig}
        ev = "; ".join("%s: %s" % (k, ", ".join(v)) for k, v in sorted(sig.items()))
        assigned, conf, cands, why, hint = "", "", [], "", ""

        if inst == "Mass General Brigham":
            specific = [k for k in MGB_HOSPITALS if k in keys]
            outside = keys - set(MGB_HOSPITALS) - {"mgb", "harvard"}
            if len(specific) == 1 and not outside:
                assigned, conf = specific[0], "medium"
                why = "Listed under the Mass General Brigham system; one hospital named (" + ev + ")."
            elif not specific and not outside:
                cands = ["mgh", "bwh", "mee", "mclean", "spaulding"]
                why = "Listed under the Mass General Brigham system with nothing in the row naming the hospital."
                hint = RESOLVE["mgb-none"]
            else:
                cands = (specific or ["mgh", "bwh"]) + sorted(outside)
                why = "Listed under the Mass General Brigham system; the row names more than one employer, or one outside the system (" + ev + ")."
                hint = resolve_hint(cands)
        else:
            dkey = norm_key(default) if default else None
            others = keys - {dkey} - ({"mgb"} if dkey in MGB_HOSPITALS else set())
            # an MGB-system email on a university lab means "some MGB hospital"
            unit_c = UNIT_CANDIDATES.get(unit)
            if unit_c:
                cands = list(unit_c[0])
                for k in sorted(others):
                    if k not in cands:
                        cands.append(k)
                why, hint = unit_c[1], RESOLVE["unit"]
            elif others:
                cands = [default] + sorted(others)
                why = "Listed under %s, but the row also names another employer (%s)." % (inst, ev)
                hint = resolve_hint(cands)
            else:
                assigned = default or ""
                conf = ENTITIES[default][2] if default else "low"
                why = "Listed institution; nothing in the row points elsewhere."

        if assigned:
            assigned_count[(inst, assigned)] += 1
        else:
            conf = "low"
            for k in cands:
                candidate_count[k] += 1
            ambiguous.append({
                "lab_id": r["id"], "institution_as_listed": inst, "unit": unit,
                "pi_name": r["pi_name"], "lab_name": r["lab_name"],
                "candidate_entities": " | ".join(ENTITIES[k][0] for k in cands),
                "why_ambiguous": why, "what_would_resolve_it": hint,
            })
        lab_map.append({
            "lab_id": r["id"], "institution_as_listed": inst, "unit": unit,
            "assigned_entity_key": assigned,
            "assigned_legal_entity_name": ENTITIES[assigned][0] if assigned else "",
            "confidence": conf,
            "candidate_entity_keys": " | ".join(cands),
            "evidence": ev,
        })

    # entities.csv
    ent_rows = []
    insts_for = collections.defaultdict(list)
    for (inst, key), n in assigned_count.items():
        insts_for[key].append((inst, n))
    for key, (name, etype, conf, src) in ENTITIES.items():
        listed = sorted(insts_for.get(key, []), key=lambda t: -t[1])
        amb = candidate_count.get(key, 0)
        if not listed and not amb:
            continue
        if listed:
            for inst, n in listed:
                extra = ""
                if inst == "Mass General Brigham":
                    extra = " Split out of the 'Mass General Brigham' listing by the hospital each lab's row names; confidence for these labs is medium."
                ent_rows.append({
                    "institution_as_listed": inst, "legal_entity_name": name,
                    "entity_type": etype, "lab_count": n,
                    "confidence": "medium" if (inst == "Mass General Brigham" and conf == "high") else conf,
                    "source_or_reasoning": src + extra,
                    "entity_key": key, "labs_where_only_a_candidate": amb,
                })
        else:
            ent_rows.append({
                "institution_as_listed": "(not a listed institution; appears as a second affiliation)",
                "legal_entity_name": name, "entity_type": etype, "lab_count": 0,
                "confidence": conf, "source_or_reasoning": src,
                "entity_key": key, "labs_where_only_a_candidate": amb,
            })
    ent_rows.sort(key=lambda d: (-d["lab_count"], -d["labs_where_only_a_candidate"]))

    def write(name, data, cols):
        p = os.path.join(a.out, name)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(data)
        return p

    write("entities.csv", ent_rows, ["institution_as_listed", "legal_entity_name", "entity_type", "lab_count", "confidence", "source_or_reasoning", "entity_key", "labs_where_only_a_candidate"])
    write("ambiguous_labs.csv", ambiguous, ["lab_id", "institution_as_listed", "unit", "pi_name", "lab_name", "candidate_entities", "why_ambiguous", "what_would_resolve_it"])
    write("lab_entity_map.csv", lab_map, ["lab_id", "institution_as_listed", "unit", "assigned_entity_key", "assigned_legal_entity_name", "confidence", "candidate_entity_keys", "evidence"])

    # console summary
    print("labs read:", len(rows), "| assigned:", sum(assigned_count.values()), "| ambiguous:", len(ambiguous))
    if unknown_inst:
        print("INSTITUTIONS WITH NO MAPPING:", dict(unknown_inst))
    legal = collections.Counter()
    for (inst, key), n in assigned_count.items():
        legal[ENTITIES[key][0]] += n
    print("\nassigned labs per legal entity:")
    for k, n in legal.most_common():
        print("  %5d  %s" % (n, k))
    print("\nambiguous labs by listed institution:")
    for k, n in collections.Counter(x["institution_as_listed"] for x in ambiguous).most_common():
        print("  %5d  %s" % (n, k))
    print("\nambiguous labs by candidate set:")
    for k, n in collections.Counter(x["candidate_entities"] for x in ambiguous).most_common(40):
        print("  %5d  %s" % (n, k))
    types = collections.Counter()
    seen = set()
    for d in ent_rows:
        if d["entity_key"] in seen:
            continue
        seen.add(d["entity_key"])
        types[d["entity_type"]] += 1
    legal_names = {d["legal_entity_name"] for d in ent_rows}
    print("\nentity keys: %d, distinct legal names: %d, by type: %s" % (len(seen), len(legal_names), dict(types)))


if __name__ == "__main__":
    main()
