"""Fold the unit lists in data/discovery/*.csv into data/targets.csv.

Discovery files are what a crawl of each institution's own index pages found
(one row per school, department, center or lab, with homepage and people page).
Existing targets keep their id, priority and notes; blank URLs are filled and
unverified URLs are replaced by checked ones. New units are added.

Run from the repo root:  python3 scripts/merge_discovery.py
"""
import csv, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGETS = ROOT / "data" / "targets.csv"
FIELDS = ["id", "name", "category", "parent", "city", "start_url", "people_url", "careers_url",
          "url_from", "priority", "collect", "listed_in", "notes", "status"]
LABS = "PI-led labs: lab name, PI, email, lab admin, lab site, member count, join page"
STAFF = "research staff, fellows, program leads; careers/internships/RA page; faculty-led labs where present"
ALIASES = {"mit-broad": "broad", "mit-whitehead": "whitehead", "harvard-wyss": "wyss",
           "harvard-cfa": "harvard-smithsonian-cfa", "harvard-wcfia": "harvard-weatherhead",
           "harvard-hls-berkman-klein": "harvard-berkman-klein", "harvard-gsd-jchs": "harvard-jchs",
           "harvard-hbs-d3": "harvard-hbs-ai-institute"}
HUMANITIES = re.compile(r"\b(history|literature|philosoph|music|theater|languages|art,|arts|religio|divinity|"
                        r"writing|media studies|islamic|biblical|jewish|spiritual|shi'ism)", re.I)
SOCIAL = re.compile(r"\b(econom|politic|sociolog|anthropolog|law|policy|management|business|finance|"
                    r"marketing|strategy|leadership|urban|planning|education|social work|global studies|"
                    r"civic|governance|criminolog|real estate|entrepreneur)", re.I)
CITY = {"mit": "Cambridge", "harvard": "Cambridge", "bu": "Boston", "northeastern": "Boston",
        "tufts": "Medford/Boston", "brandeis": "Waltham", "bc": "Chestnut Hill", "umass-boston": "Boston"}
PARENT = {"mit": "MIT", "harvard": "Harvard University", "bu": "Boston University",
          "northeastern": "Northeastern University", "tufts": "Tufts University",
          "brandeis": "Brandeis University", "bc": "Boston College", "umass-boston": "UMass Boston"}


def prefix(i):
    for p in ("umass-boston", "northeastern", "harvard", "brandeis", "tufts", "mit", "bu", "bc"):
        if i.startswith(p + "-"):
            return p
    return ""


def priority(row):
    name, cat = row["name"], row["category"]
    if HUMANITIES.search(name):
        return "3"
    if cat in ("school",) or "policy" in cat or SOCIAL.search(name):
        return "2"
    return "1"


def main():
    rows = {r["id"]: r for r in csv.DictReader(open(TARGETS))}
    added = filled = 0
    for f in sorted((ROOT / "data" / "discovery").glob("*.csv")):
        for d in csv.DictReader(open(f)):
            if "start_url" not in d or not d.get("id"):
                continue
            i = ALIASES.get(d["id"], d["id"])
            if i in rows:
                r = rows[i]
                for k in ("start_url", "people_url", "careers_url"):
                    v = (d.get(k) or "").strip()
                    if v and (not r.get(k) or (k == "start_url" and r["url_from"] in ("", "unverified"))):
                        r[k] = v
                        filled += 1
                if r["url_from"] in ("", "unverified") and d.get("start_url"):
                    r["url_from"] = "checked"
                continue
            p = prefix(i)
            inst = d.get("institution") or PARENT.get(p, "")
            school = d.get("school") or ""
            r = {k: "" for k in FIELDS}
            r.update(id=i, name=d["name"], category=d.get("category") or "research-center",
                     parent=(inst + (" / " + school if school and school != inst else "")).strip(" /"),
                     city=CITY.get(p, "Boston"), start_url=d.get("start_url", ""),
                     people_url=d.get("people_url", ""), careers_url=d.get("careers_url", ""),
                     url_from="checked" if d.get("start_url") else "", listed_in=f.stem,
                     notes=d.get("notes", ""), status="todo")
            if r["category"] == "science-institute" or r["category"] == "hospital":
                r["category"] = r["category"]
            r["priority"] = priority(r)
            r["collect"] = LABS if r["priority"] == "1" else STAFF
            rows[i] = r
            added += 1
    out = sorted(rows.values(), key=lambda r: (int(r["priority"] or 9), r["id"]))
    with open(TARGETS, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"added {added}, filled {filled} URLs, total {len(out)}")


if __name__ == "__main__":
    main()
