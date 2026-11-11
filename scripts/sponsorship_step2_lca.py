#!/usr/bin/env python3
"""Sponsorship research, step 2: each employer's H-1B filing profile from the
Department of Labor's LCA disclosure files.

Two stages, so the slow one runs once:

  extract   stream every LCA_Disclosure_Data_*.xlsx in cache/dol-lca/, keep
            VISA_CLASS = H-1B rows whose primary worksite is in --state, and
            write a slim CSV per file to cache/dol-lca/filtered/
  profile   read the slim CSVs, match employers to sponsorship_research/
            entities.csv, classify job titles, and write
              sponsorship_research/employer_matches.csv
              sponsorship_research/entity_role_profile.csv
              sponsorship_research/unclassified_titles.csv
              sponsorship_research/step2_numbers.json   (facts for the notes)

The LCA files are not fetched here. dol.gov refuses scripted requests, so they
are downloaded in a browser from
https://www.dol.gov/agencies/eta/foreign-labor/performance and placed in
cache/dol-lca/ (gitignored) under their original names.

    python3 scripts/sponsorship_step2_lca.py extract --state MA
    python3 scripts/sponsorship_step2_lca.py profile --state MA

Rerun for another state: change --state. The employer patterns in ENTITY_MATCH
are for the Boston entities; add patterns for the new city's employers.
"""
import argparse
import collections
import csv
import datetime
import difflib
import glob
import json
import multiprocessing
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "cache", "dol-lca")
FILTERED = os.path.join(RAW, "filtered")
OUT = os.path.join(ROOT, "sponsorship_research")

KEEP = [
    "CASE_NUMBER", "CASE_STATUS", "RECEIVED_DATE", "DECISION_DATE", "VISA_CLASS",
    "JOB_TITLE", "SOC_CODE", "SOC_TITLE", "FULL_TIME_POSITION",
    "TOTAL_WORKER_POSITIONS", "NEW_EMPLOYMENT", "CONTINUED_EMPLOYMENT",
    "CHANGE_PREVIOUS_EMPLOYMENT", "NEW_CONCURRENT_EMPLOYMENT", "CHANGE_EMPLOYER",
    "AMENDED_PETITION", "EMPLOYER_NAME", "TRADE_NAME_DBA", "EMPLOYER_ADDRESS1",
    "EMPLOYER_CITY", "EMPLOYER_STATE", "EMPLOYER_POSTAL_CODE", "EMPLOYER_FEIN",
    "NAICS_CODE", "SECONDARY_ENTITY", "SECONDARY_ENTITY_BUSINESS_NAME",
    "WORKSITE_ADDRESS1", "WORKSITE_CITY", "WORKSITE_STATE", "WORKSITE_POSTAL_CODE",
    "WAGE_RATE_OF_PAY_FROM", "WAGE_RATE_OF_PAY_TO", "WAGE_UNIT_OF_PAY",
    "PREVAILING_WAGE", "PW_UNIT_OF_PAY", "PW_WAGE_LEVEL", "PW_OES_YEAR",
    "PW_OTHER_SOURCE", "PW_SURVEY_NAME", "H_1B_DEPENDENT",
]
# Column names that changed between releases: canonical -> accepted spellings.
ALIASES = {
    "CHANGE_PREVIOUS_EMPLOYMENT": ["CHANGE_PREVIOUS_EMPLOYMENT", "CHANGE_PREVIOUS_EMPLOYER"],
    "EMPLOYER_FEIN": ["EMPLOYER_FEIN", "FEIN"],
    "SECONDARY_ENTITY_BUSINESS_NAME": ["SECONDARY_ENTITY_BUSINESS_NAME", "SECONDARY_ENTITY_BUSINESS"],
    "PW_OTHER_SOURCE": ["PW_OTHER_SOURCE", "PW_NON-OES_SOURCE", "PW_OTHER_SOURCE_1"],
    "H_1B_DEPENDENT": ["H_1B_DEPENDENT", "H-1B_DEPENDENT"],
    "WORKSITE_STATE": ["WORKSITE_STATE", "WORKSITE_STATE_1"],
    "WORKSITE_CITY": ["WORKSITE_CITY", "WORKSITE_CITY_1"],
    "WORKSITE_ADDRESS1": ["WORKSITE_ADDRESS1", "WORKSITE_ADDRESS1_1"],
    "WORKSITE_POSTAL_CODE": ["WORKSITE_POSTAL_CODE", "WORKSITE_POSTAL_CODE_1"],
}


# ----------------------------------------------------------------- extract

def extract_one(args):
    path, state = args
    import openpyxl
    stem = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(FILTERED, "%s__%s.csv" % (stem, state))
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h).strip() if h is not None else "" for h in next(it)]
    pos = {h: i for i, h in enumerate(hdr)}
    idx, missing = {}, []
    for col in KEEP:
        for name in ALIASES.get(col, [col]):
            if name in pos:
                idx[col] = pos[name]
                break
        else:
            missing.append(col)
    i_visa, i_state = idx.get("VISA_CLASS"), idx.get("WORKSITE_STATE")
    total = kept = 0
    dmin = dmax = None
    i_dec = idx.get("DECISION_DATE")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(KEEP + ["SOURCE_FILE"])
        for row in it:
            total += 1
            d = row[i_dec] if i_dec is not None else None
            if isinstance(d, datetime.datetime):
                dmin = d if dmin is None or d < dmin else dmin
                dmax = d if dmax is None or d > dmax else dmax
            if row[i_visa] != "H-1B" or (row[i_state] or "").strip().upper() != state:
                continue
            kept += 1
            vals = []
            for col in KEEP:
                v = row[idx[col]] if col in idx else ""
                if isinstance(v, datetime.datetime):
                    v = v.date().isoformat()
                vals.append("" if v is None else v)
            w.writerow(vals + [stem])
    return {"file": stem, "rows": total, "kept": kept, "missing_columns": missing,
            "decision_min": dmin.date().isoformat() if dmin else None,
            "decision_max": dmax.date().isoformat() if dmax else None}


def cmd_extract(a):
    os.makedirs(FILTERED, exist_ok=True)
    files = sorted(glob.glob(os.path.join(RAW, "LCA_Disclosure_Data_*.xlsx")))
    todo = []
    for p in files:
        stem = os.path.splitext(os.path.basename(p))[0]
        if a.only and not any(o in stem for o in a.only):
            continue
        if not a.force and os.path.exists(os.path.join(FILTERED, "%s__%s.csv" % (stem, a.state))):
            print("already extracted:", stem)
            continue
        todo.append((p, a.state))
    with multiprocessing.Pool(min(a.jobs, max(1, len(todo)))) as pool:
        for res in pool.imap_unordered(extract_one, todo):
            print(json.dumps(res), flush=True)
            with open(os.path.join(FILTERED, "extract_log.jsonl"), "a") as f:
                f.write(json.dumps(dict(res, state=a.state)) + "\n")


# ----------------------------------------------------------------- matching

def clean(v):
    """Strip the ="..." wrapper some DOL releases leave around text cells."""
    v = (v or "").strip()
    if v.startswith('="') and v.endswith('"'):
        v = v[2:-1]
    return v.strip()


def norm_name(s):
    s = clean(s).upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_suffix(s):
    return re.sub(r"\s+", " ", re.sub(r"\b(THE|INC|INCORPORATED|LLC|CORP|CORPORATION|CO)\b", " ", s)).strip()


# entity_key -> (tight regex = accept, loose regex = show as near-miss)
# Order matters: the first tight match wins.
ENTITY_MATCH = collections.OrderedDict([
    ("tuftsmc", (r"^TUFTS MEDICAL CENTER( INC)?$", r"TUFTS MEDICAL|TUFTS MEDICINE")),
    ("hhmi", (r"HOWARD HUGHES MEDICAL", r"HOWARD HUGHES")),
    ("broad", (r"BROAD INSTITUTE", r"\bBROAD\b")),
    ("whitehead", (r"WHITEHEAD INST", r"WHITEHEAD")),
    ("dfci", (r"DANA FARBER CANCER INST", r"DANA FARBER")),
    ("bch", (r"CHILDREN S HOSPITAL CORPORATION|CHILDRENS HOSPITAL CORPORATION|^BOSTON CHILDREN S HOSPITAL", r"CHILDREN S HOSPITAL|CHILDRENS HOSPITAL|BOSTON CHILDREN")),
    ("bmc", (r"^BOSTON MEDICAL CENTER", r"BOSTON MEDICAL CENTER")),
    ("bidmc", (r"^BETH ISRAEL DEACONESS MEDICAL CENTER", r"BETH ISRAEL")),
    ("mee", (r"MASSACHUSETTS EYE AND EAR INFIRMARY", r"EYE AND EAR|SCHEPENS")),
    ("mclean", (r"MCLEAN HOSPITAL", r"MCLEAN")),
    ("spaulding", (r"SPAULDING REHABILITATION HOSPITAL", r"SPAULDING")),
    ("bwh", (r"^(THE )?BRIGHAM AND WOMEN S HOSPITAL", r"BRIGHAM")),
    ("mgh", (r"^(THE )?GENERAL HOSPITAL CORP(ORATION)?\b|^(THE )?MASSACHUSETTS GENERAL HOSPITAL", r"GENERAL HOSPITAL|MASS GENERAL(?! BRIGHAM)")),
    ("mgb", (r"^MASS GENERAL BRIGHAM( INCORPORATED| INC)?$|^PARTNERS HEALTHCARE SYSTEM", r"MASS GENERAL BRIGHAM|PARTNERS HEALTHCARE")),
    ("ragon", (r"RAGON INSTITUTE", r"RAGON")),
    ("joslin", (r"JOSLIN DIABETES", r"JOSLIN")),
    ("hsl", (r"HEBREW REHABILITATION|HEBREW SENIORLIFE|HEBREW SENIOR LIFE", r"HEBREW")),
    ("forsyth", (r"FORSYTH INSTITUTE|FORSYTH DENTAL", r"FORSYTH")),
    ("harvard", (r"PRESIDENT AND FELLOWS OF HARVARD COLLEGE|^HARVARD UNIVERSITY", r"HARVARD")),
    ("mit", (r"^MASSACHUSETTS INSTITUTE OF TECHNOLOGY", r"MASSACHUSETTS INSTITUTE|\bMIT\b")),
    ("bu", (r"TRUSTEES OF BOSTON UNIVERSITY|^BOSTON UNIVERSITY$", r"BOSTON UNIVERSITY")),
    ("tufts", (r"TRUSTEES OF TUFTS COLLEGE|^TUFTS UNIVERSITY", r"TUFTS")),
    ("northeastern", (r"^NORTHEASTERN UNIVERSITY", r"NORTHEASTERN")),
    ("bc", (r"TRUSTEES OF BOSTON COLLEGE|^BOSTON COLLEGE$", r"BOSTON COLLEGE")),
    ("brandeis", (r"^BRANDEIS UNIVERSITY", r"BRANDEIS")),
    ("umb", (r"UNIVERSITY OF MASSACHUSETTS BOSTON|UMASS BOSTON", r"UNIVERSITY OF MASSACHUSETTS|UMASS")),
    ("va", (r"BOSTON VA RESEARCH INSTITUTE|VETERANS AFFAIRS", r"VETERANS|\bVA\b")),
    ("usda", (r"DEPARTMENT OF AGRICULTURE|AGRICULTURAL RESEARCH SERVICE", None)),
    ("ibm", (r"^INTERNATIONAL BUSINESS MACHINES|^IBM( CORP| CORPORATION)?$", r"\bIBM\b")),
    ("emerson", (r"^EMERSON HOSPITAL", None)),
])


def match_entity(name_norm, row):
    """Return (entity_key, match_type) or (None, None); also loose hits."""
    for key, (tight, loose) in ENTITY_MATCH.items():
        if re.search(tight, name_norm):
            return key, "name"
    # University of Massachusetts files under one system name for several
    # campuses; accept for the Boston campus only on an address match.
    if re.search(r"UNIVERSITY OF MASSACHUSETTS", name_norm):
        addr = " ".join([row.get("EMPLOYER_ADDRESS1", ""), row.get("WORKSITE_ADDRESS1", "")]).upper()
        if "MORRISSEY" in addr or (row.get("WORKSITE_POSTAL_CODE", "") or "").startswith("02125"):
            return "umb", "name+address"
    return None, None


def loose_entity(name_norm):
    for key, (tight, loose) in ENTITY_MATCH.items():
        if loose and re.search(loose, name_norm):
            return key
    return None


# ----------------------------------------------------------------- roles

FAMILIES = [
    "research technician / lab technician",
    "research assistant / research associate (entry-level)",
    "computational / bioinformatics / data analyst",
    "software or ML engineer",
    "clinical research coordinator",
    "postdoc / research fellow",
    "scientist / staff scientist",
    "faculty / instructor",
    "clinical (physician, nurse, clinical staff)",
    "administrative / other",
]
ENTRY_FAMILIES = FAMILIES[:4]
T, RA, COMP, SW, CRC, PD, SCI, FAC, CLIN, OTH = FAMILIES

SENIOR = r"\b(SENIOR|SR|PRINCIPAL|LEAD|DIRECTOR|MANAGER|HEAD|CHIEF|STAFF|III|IV|V)\b"


def classify(title, soc, annual_wage, level, entity_type):
    """Return (family, flag). flag is '' when confident."""
    t = norm_name(title)
    soc2 = (soc or "")[:2]
    soc7 = (soc or "")[:7]
    flag = ""

    def has(p):
        return re.search(p, t) is not None

    if has(r"POSTDOC|POST DOC|RESEARCH FELLOW|RESEARCH SCHOLAR|VISITING SCHOLAR") and not has(r"CLINICAL FELLOW"):
        fam = PD
    elif has(r"CLINICAL RESEARCH|RESEARCH COORDINATOR|STUDY COORDINATOR|CLINICAL TRIAL|REGULATORY (AFFAIRS|COORDINATOR|SPECIALIST)|RESEARCH NURSE"):
        fam = CRC
    elif has(r"CLINICAL FELLOW|\bRESIDENT\b|RESIDENCY|PHYSICIAN|HOSPITALIST|SURGEON|\bNURSE\b|PHARMACIST|THERAPIST|DENTIST|PSYCHIATRIST|PSYCHOLOGIST|RADIOLOGIST|ANESTHESIOLOGIST|PATHOLOGIST|CARDIOLOGIST|NEUROLOGIST|PEDIATRICIAN|ONCOLOGIST|INTENSIVIST|MEDICAL TECHNOLOGIST|PHYSICIST|DOSIMETRIST|GENETIC COUNSELOR|SOCIAL WORKER|CLINICIAN|VETERINARIAN|OPTOMETRIST|AUDIOLOGIST|DIETITIAN|PHYSICIAN ASSISTANT"):
        fam = CLIN
        if has(r"PHYSICIST") and not has(r"MEDICAL PHYSICIST"):
            fam = SCI
    elif has(r"POSTDOC|POST DOC|RESEARCH FELLOW|\bFELLOW\b|RESEARCH SCHOLAR|VISITING SCHOLAR"):
        fam = PD
    elif has(r"PROFESSOR|LECTURER|\bINSTRUCTOR\b|FACULTY|PRECEPTOR|TEACHING") or soc2 == "25" and soc7.startswith("25-1"):
        fam = FAC
        if not has(r"PROFESSOR|LECTURER|INSTRUCTOR|FACULTY|PRECEPTOR|TEACHING"):
            # SOC says postsecondary teacher but the title does not: many
            # universities file research titles under teacher codes.
            if has(r"RESEARCH (ASSOCIATE|ASSISTANT)"):
                fam, flag = RA, "filed under a postsecondary-teacher SOC code; likely an academic appointment, not entry-level staff"
            elif has(r"SCIENTIST|RESEARCHER|ENGINEER"):
                fam = SCI
            else:
                flag = "classified by SOC code only (postsecondary teacher)"
    elif has(r"TECHNICIAN|RESEARCH TECHNOLOGIST|LAB(ORATORY)? TECH|RESEARCH TECH|RESEARCH LAB TECH|TECHNICAL ASSISTANT|TECHNICAL ASSOCIATE|ANIMAL CARE"):
        fam = T
    elif has(r"TECHNOLOGIST") and (soc2 == "29" or has(r"CYTO|DIAGNOSTIC|RADIOLOG|NUCLEAR|HISTO|SURGICAL|CARDIO|MRI|ULTRASOUND")):
        fam = CLIN
    elif has(r"COMPUTATIONAL|BIOINFORMATIC|DATA ANALYST|DATA SCIENTIST|STATISTIC|BIOSTATISTIC|RESEARCH ANALYST|DATA MANAGER|INFORMATICS") and not has(r"SOFTWARE|BUSINESS|FINANC|BUDGET|SYSTEMS ANALYST|PAYROLL|\bSAP\b|\bHR|TELECOM|ADMISSION|ENROLLMENT|MARKETING"):
        fam = COMP
    elif has(r"\bANALYST\b") and soc7.startswith("15-2"):
        fam = COMP
    elif has(r"SOFTWARE|DEVELOPER|MACHINE LEARNING|\bML\b|\bAI\b|DEVOPS|DATA ENGINEER|PROGRAMMER|SYSTEMS? ENGINEER|CLOUD|FULL STACK|WEB |APPLICATIONS? (ENGINEER|ARCHITECT)|SYSTEMS ANALYST|SYSTEMS ADMINISTRATOR|DATABASE|SECURITY ENGINEER|RESEARCH COMPUTING") or soc7 in ("15-1252", "15-1251", "15-1253", "15-1254", "15-1244", "15-1242", "15-1243", "15-1241", "15-1211", "15-1212"):
        fam = SW
    elif has(r"RESEARCH (ASSOCIATE|ASSISTANT)|\bASSOCIATE (SCIENTIST|RESEARCHER)|LAB(ORATORY)? (ASSOCIATE|ASSISTANT|MANAGER)|RESEARCH SPECIALIST|RESEARCH AIDE"):
        fam = RA
    elif has(r"SCIENTIST|INVESTIGATOR|RESEARCHER|ENGINEER|CHEMIST|BIOLOGIST|PHYSICIST|ASTRONOMER|ECONOMIST|EPIDEMIOLOGIST|GENETICIST|RESEARCH STAFF") or soc2 in ("19", "17") or soc7.startswith("15-2"):
        fam = SCI
        if not has(r"SCIENTIST|INVESTIGATOR|RESEARCHER|ENGINEER|CHEMIST|BIOLOGIST|PHYSICIST|ASTRONOMER|ECONOMIST|EPIDEMIOLOGIST|GENETICIST|RESEARCH STAFF"):
            flag = "classified by SOC code only (science or engineering occupation)"
    elif soc2 == "29":
        fam, flag = CLIN, "classified by SOC code only (healthcare practitioner)"
    else:
        fam = OTH

    # Titles that do not mean the same thing everywhere.
    if fam == RA and not flag:
        if entity_type == "university":
            flag = "at a university this title is usually an academic appointment, not entry-level staff"
        elif level in ("III", "IV") or (annual_wage and annual_wage >= 85000) or has(SENIOR):
            flag = "senior wording, wage or wage level; may not be entry-level"
    elif fam in (T, COMP, SW) and not flag:
        if level in ("III", "IV") or has(r"\b(SENIOR|SR|PRINCIPAL|LEAD|DIRECTOR|MANAGER|HEAD|CHIEF)\b"):
            flag = "senior wording or wage level; not entry-level"
    return fam, flag


UNIT_MULT = {"YEAR": 1, "MONTH": 12, "BI-WEEKLY": 26, "WEEK": 52, "HOUR": 2080}


def annualize(amount, unit):
    try:
        x = float(str(amount).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None
    m = UNIT_MULT.get((unit or "").strip().upper())
    return x * m if m else None


def fiscal_year(iso):
    try:
        d = datetime.date.fromisoformat(iso[:10])
    except (TypeError, ValueError):
        return None
    return d.year + 1 if d.month >= 10 else d.year


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


# ----------------------------------------------------------------- profile

def cmd_profile(a):
    ents = {}
    for r in csv.DictReader(open(os.path.join(OUT, "entities.csv"), encoding="utf-8")):
        ents.setdefault(r["entity_key"], r)

    files = sorted(glob.glob(os.path.join(FILTERED, "LCA_Disclosure_Data_*__%s.csv" % a.state)))
    rows, per_file = {}, {}
    for p in files:
        n = 0
        for r in csv.DictReader(open(p, encoding="utf-8")):
            n += 1
            for col in ("JOB_TITLE", "EMPLOYER_NAME", "SOC_CODE", "PW_WAGE_LEVEL", "CASE_STATUS", "WORKSITE_CITY", "WORKSITE_ADDRESS1"):
                r[col] = clean(r.get(col))
            rows[clean(r["CASE_NUMBER"])] = r   # later files overwrite earlier ones
        per_file[os.path.basename(p)] = n
    rows = list(rows.values())
    status = collections.Counter(r["CASE_STATUS"] for r in rows)

    # --- employer matching
    emp = {}   # (norm name, fein) -> aggregate
    for r in rows:
        nn = norm_name(r["EMPLOYER_NAME"])
        k = (nn, r["EMPLOYER_FEIN"])
        e = emp.setdefault(k, {"name": r["EMPLOYER_NAME"], "norm": nn, "fein": r["EMPLOYER_FEIN"],
                               "cities": collections.Counter(), "addr": collections.Counter(),
                               "certified": 0, "all": 0, "sample": r})
        e["all"] += 1
        e["certified"] += r["CASE_STATUS"] == "Certified"
        e["cities"]["%s %s" % (r["EMPLOYER_CITY"], r["EMPLOYER_STATE"])] += 1
        e["addr"][r["EMPLOYER_ADDRESS1"]] += 1

    key_of, how = {}, {}
    for k, e in emp.items():
        ent, mtype = match_entity(e["norm"], e["sample"])
        if ent:
            key_of[k], how[k] = ent, mtype
    # FEINs that belong to an accepted name
    fein_ent = collections.defaultdict(collections.Counter)
    for k, ent in key_of.items():
        if k[1]:
            fein_ent[k[1]][ent] += emp[k]["certified"]
    match_rows = []
    late_accept = []
    for k, e in list(emp.items()):
        ent, mtype, accepted, note = key_of.get(k), how.get(k, ""), "no", ""
        if ent:
            accepted = "yes"
            feins = fein_ent.get(k[1])
            if feins and len(feins) > 1:
                note = "This FEIN is also used under a name matched to: " + ", ".join(x for x in feins if x != ent)
        else:
            same_fein = fein_ent.get(k[1])
            if same_fein:
                ent = same_fein.most_common(1)[0][0]
                accepted_names = [kk[0] for kk, vv in key_of.items() if vv == ent and kk[1] == k[1]]
                close = max((difflib.SequenceMatcher(None, e["norm"], n).ratio() for n in accepted_names), default=0)
                if close >= 0.9:
                    mtype, accepted = "same FEIN, misspelled name", "yes"
                    note = "Same employer ID and a near-identical name (likely a typo on the filing). Counted."
                    late_accept.append((k, ent))
                else:
                    mtype, accepted = "same FEIN, different name", "check"
                    note = "Shares an employer ID with accepted filings for this entity but the name is different (public institutions can share one state employer ID). Not counted."
            else:
                ent = loose_entity(e["norm"])
                if not ent:
                    continue
                mtype, note = "near-miss on name", "Name resembles this entity but is probably a different organization. Not counted."
        match_rows.append({
            "entity_key": ent, "legal_entity_name": ents.get(ent, {}).get("legal_entity_name", ""),
            "lca_employer_name": e["name"], "employer_fein": e["fein"],
            "employer_city_state": e["cities"].most_common(1)[0][0],
            "employer_address1": e["addr"].most_common(1)[0][0],
            "certified_filings": e["certified"], "all_filings": e["all"],
            "match_type": mtype, "accepted": accepted, "note": note,
        })
    for k, ent in late_accept:
        key_of[k] = ent
    match_rows.sort(key=lambda d: (d["entity_key"], {"yes": 0, "check": 1, "no": 2}[d["accepted"]], -d["certified_filings"]))
    with open(os.path.join(OUT, "employer_matches.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(match_rows[0].keys()))
        w.writeheader()
        w.writerows(match_rows)

    # --- role profile on certified, matched rows
    agg = {}
    unclassified = collections.Counter()
    flagged_titles = collections.Counter()
    matched_certified = 0
    ragon_check = collections.Counter()
    pw_source = collections.defaultdict(collections.Counter)
    es = {}   # entity-level totals for step 4
    for r in rows:
        k = (norm_name(r["EMPLOYER_NAME"]), r["EMPLOYER_FEIN"])
        ent = key_of.get(k)
        if not ent or r["CASE_STATUS"] != "Certified":
            continue
        matched_certified += 1
        etype = ents.get(ent, {}).get("entity_type", "")
        wage = annualize(r["WAGE_RATE_OF_PAY_FROM"], r["WAGE_UNIT_OF_PAY"])
        level = (r["PW_WAGE_LEVEL"] or "").strip().upper()
        if level not in ("I", "II", "III", "IV"):
            level = "none"
        fam, flag = classify(r["JOB_TITLE"], r["SOC_CODE"], wage, level, etype)
        new = to_int(r["NEW_EMPLOYMENT"])
        fy = fiscal_year(r["DECISION_DATE"])
        g = agg.setdefault((ent, fam), {"filings": 0, "new": 0, "new_l12": 0, "new_l12_clean": 0, "new_clean_fys": set(), "positions": 0,
                                        "levels": collections.Counter(), "wages": [], "fys": set(),
                                        "flagged": 0, "titles": collections.Counter(),
                                        "new_by_fy": collections.Counter()})
        g["filings"] += 1
        g["new"] += new
        g["positions"] += to_int(r["TOTAL_WORKER_POSITIONS"])
        g["levels"][level] += 1
        if level in ("I", "II"):
            g["new_l12"] += new
            if not flag and new:
                g["new_l12_clean"] += new
                if fy:
                    g["new_clean_fys"].add(fy)
        if wage:
            g["wages"].append(wage)
        if fy:
            g["fys"].add(fy)
            g["new_by_fy"][fy] += new
        g["flagged"] += bool(flag)
        g["titles"][r["JOB_TITLE"].strip().title()] += 1
        s_ = es.setdefault(ent, {"certified": 0, "new": 0, "entry_new": 0, "entry_new_conf": 0,
                                 "entry_fys": set(), "senior_new": 0, "entry_wages": [], "fys": set()})
        s_["certified"] += 1
        s_["new"] += new
        if fy:
            s_["fys"].add(fy)
        if fam in ENTRY_FAMILIES:
            s_["entry_new"] += new
            if level in ("I", "II") and not flag:
                s_["entry_new_conf"] += new
                if new and fy:
                    s_["entry_fys"].add(fy)
                if wage and new:
                    # weight by new-employment positions: one LCA can cover several
                    s_["entry_wages"].extend([wage] * new)
        elif fam in (PD, SCI, FAC):
            s_["senior_new"] += new
        if fam == OTH:
            unclassified[(ents[ent]["legal_entity_name"], r["JOB_TITLE"].strip().title(), r["SOC_CODE"])] += 1
        if flag:
            flagged_titles[(ents[ent]["legal_entity_name"], r["JOB_TITLE"].strip().title(), fam, flag)] += 1
        if ent == "mgh" and r["WORKSITE_CITY"].strip().upper() == "CAMBRIDGE":
            ragon_check[r["WORKSITE_ADDRESS1"].strip().upper()] += 1
        src = (r["PW_OTHER_SOURCE"] or "").strip() or ("OES level " + level if level != "none" else "blank")
        pw_source[ent][src if not src.startswith("OES level") else "OES/OEWS (level given)"] += 1

    prof = []
    for (ent, fam), g in agg.items():
        e = ents[ent]
        prof.append({
            "entity_key": ent, "legal_entity_name": e["legal_entity_name"], "entity_type": e["entity_type"],
            "role_family": fam, "entry_level_family": "yes" if fam in ENTRY_FAMILIES else "no",
            "certified_filings": g["filings"],
            "new_employment_positions": g["new"],
            "new_employment_positions_level_I_II": g["new_l12"],
            "new_employment_level_I_II_confident": g["new_l12_clean"],
            "fiscal_years_with_confident_entry_filings": len(g["new_clean_fys"]),
            "total_worker_positions": g["positions"],
            "pw_level_I": g["levels"]["I"], "pw_level_II": g["levels"]["II"],
            "pw_level_III": g["levels"]["III"], "pw_level_IV": g["levels"]["IV"],
            "pw_level_not_given": g["levels"]["none"],
            "median_annual_wage": round(statistics.median(g["wages"])) if g["wages"] else "",
            "fiscal_years_present": " ".join("FY%d" % y for y in sorted(g["fys"])),
            "new_employment_by_fiscal_year": " ".join("FY%d:%d" % (y, n) for y, n in sorted(g["new_by_fy"].items())),
            "filings_with_uncertain_classification": g["flagged"],
            "most_common_titles": "; ".join("%s (%d)" % t for t in g["titles"].most_common(5)),
        })
    order = {f: i for i, f in enumerate(FAMILIES)}
    prof.sort(key=lambda d: (d["legal_entity_name"], order[d["role_family"]]))
    with open(os.path.join(OUT, "entity_role_profile.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(prof[0].keys()))
        w.writeheader()
        w.writerows(prof)

    with open(os.path.join(OUT, "entity_filing_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entity_key", "legal_entity_name", "certified_filings", "new_employment_positions",
                    "entry_family_new_positions", "entry_new_positions_level_I_II_confident",
                    "fiscal_years_with_confident_entry_filings", "senior_family_new_positions",
                    "median_entry_wage_level_I_II_confident", "fiscal_years_present"])
        for ent, s_ in sorted(es.items(), key=lambda kv: -kv[1]["new"]):
            w.writerow([ent, ents[ent]["legal_entity_name"], s_["certified"], s_["new"], s_["entry_new"],
                        s_["entry_new_conf"], len(s_["entry_fys"]), s_["senior_new"],
                        round(statistics.median(s_["entry_wages"])) if s_["entry_wages"] else "",
                        " ".join("FY%d" % y for y in sorted(s_["fys"]))])

    with open(os.path.join(OUT, "unclassified_titles.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["legal_entity_name", "job_title", "role_family_assigned", "why_uncertain", "soc_code", "certified_filings"])
        for (name, title, soc), n in unclassified.most_common():
            w.writerow([name, title, OTH, "no keyword or SOC rule matched", soc, n])
        for (name, title, fam, flag), n in flagged_titles.most_common():
            w.writerow([name, title, fam, flag, "", n])

    numbers = {
        "state": a.state, "files": per_file, "rows_after_dedup": len(rows),
        "case_status": dict(status), "matched_certified_rows": matched_certified,
        "entities_with_filings": sorted({k[0] for k in agg}),
        "entities_without_filings": sorted(set(ents) - {k[0] for k in agg}),
        "mgh_filings_with_cambridge_worksite": dict(ragon_check.most_common(10)),
        "pw_source_by_entity": {k: dict(v.most_common(6)) for k, v in pw_source.items()},
        "unclassified_certified_rows": sum(unclassified.values()),
        "flagged_certified_rows": sum(flagged_titles.values()),
    }
    json.dump(numbers, open(os.path.join(OUT, "step2_numbers.json"), "w"), indent=1)
    print(json.dumps({k: numbers[k] for k in ("files", "rows_after_dedup", "case_status", "matched_certified_rows", "entities_without_filings", "unclassified_certified_rows", "flagged_certified_rows")}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--state", default="MA")
    e.add_argument("--jobs", type=int, default=3)
    e.add_argument("--force", action="store_true")
    e.add_argument("--only", nargs="*")
    p = sub.add_parser("profile")
    p.add_argument("--state", default="MA")
    a = ap.parse_args()
    {"extract": cmd_extract, "profile": cmd_profile}[a.cmd](a)


if __name__ == "__main__":
    main()
