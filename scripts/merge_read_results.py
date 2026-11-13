#!/usr/bin/env python3
"""Check reader results against their worklists and write one results file.

    python3 scripts/merge_read_results.py OUT.json --pairs WORK1.json:RES1.json [WORK2.json:RES2.json ...]
                                          [--null-count LAB_ID=REASON ...]

Readers (see depth_read_brief.md) each get a slice of a prep-sizes worklist and
write a results list. Before `depth_pass.py apply` this:
  - reports worklist items with no result, duplicate or unknown results;
  - checks that every `members_page_url` / `join_page_url` is an address that
    was really read: one of the worklist's own addresses, or a page in the
    fetch cache whose recorded address matches. An address that fails is
    dropped (a count then falls back to the worklist's people page);
  - turns the readers' `HUB:` / `DEAD:` / `NOT-A-LAB:` triage tags into plain sentences;
  - --null-count drops a count the main session decided not to keep, with the
    reason put in the note (the note keeps the number the page lists).
It prints the HUB and DEAD items so they can be reviewed by eye.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch as F  # noqa: E402


def norm(u):
    return (u or "").rstrip("/")


def really_fetched(url):
    try:
        html_path, meta_path = F._cache_paths(url)
        return html_path.exists() and meta_path.exists() and norm(json.loads(meta_path.read_text()).get("url")) == norm(url)
    except Exception:
        return False


def main():
    args = sys.argv[1:]
    out = args[0]
    pairs = [a for a in args[args.index("--pairs") + 1:] if ":" in a and not a.startswith("--") and "=" not in a]
    nullc = dict(a.split("=", 1) for a in (args[args.index("--null-count") + 1:] if "--null-count" in args else []) if "=" in a)
    work, res = [], []
    for pair in pairs:
        w, r = pair.split(":", 1)
        work += json.loads(Path(w).read_text())
        res += json.loads(Path(r).read_text())
    wk = {(w["source"], w["lab_id"]): w for w in work}
    seen = collections.Counter((r["source"], r["lab_id"]) for r in res)
    print(f"{len(res)} results for {len(work)} items; missing {[k[1] for k in wk if k not in seen]}, "
          f"duplicates {[k[1] for k, v in seen.items() if v > 1]}, unknown {[k[1] for k in seen if k not in wk]}")
    tally, keep, flagged = collections.Counter(), [], []
    for r in res:
        key = (r["source"], r["lab_id"])
        if key not in wk:
            continue
        w, f = wk[key], (r.get("fields") or {})
        r["fields"] = f
        note = (r.get("note") or "").strip()
        if not note:
            print("NO NOTE", r["lab_id"])
        for k in ("members_page_url", "join_page_url"):
            u = f.get(k)
            if not u or norm(u) in {norm(w.get("lab_website")), norm(w.get("people_url")), norm(w.get("join_url"))} or really_fetched(u):
                continue
            print(f"UNVERIFIED {k} {r['lab_id']} {u}")
            f[k] = (w.get("people_url") or w.get("lab_website")) if k == "members_page_url" and f.get("member_count") is not None else None
        count = f.get("member_count")
        if count is not None and (not isinstance(count, int) or not f.get("members_page_url")):
            print("BAD COUNT", r["lab_id"], count)
        if f.get("kind"):
            print("KIND", r["lab_id"], f["kind"], "|", note[:150])
        m = re.match(r"^(HUB|DEAD|NOT-A-LAB):\s*", note)
        tag = m.group(1) if m else ("count" if count is not None else "null")
        if m:
            note = note[m.end():]
            if not re.match(r"\S*[._/]\S", note):  # leave an address or field name at the start as written
                note = note[:1].upper() + note[1:]
            if count is not None:
                print("TAGGED BUT COUNTED", r["lab_id"])
            if tag == "DEAD" and re.search(r"access denied|403|request.blocked", note, re.I):
                note += " The site refuses the project's fetcher; not worked around."
            lead_in = {"HUB": "Not sized, the site is not this unit's own: ", "DEAD": "Not sized, the site could not be read: ",
                       "NOT-A-LAB": "Not sized, this is not a research group: "}[tag]
            note = lead_in + note
            flagged.append(f"  {tag} {r['lab_id']} | {w.get('lab_website')} | {note[:150]}")
        if r["lab_id"] in nullc:
            f["member_count"] = f["member_breakdown"] = None
            note = f"{nullc[r['lab_id']]} (the page lists {count}). {note}"
            tag = "null"
        tally[tag] += 1
        r["note"] = note
        keep.append(r)
    Path(out).write_text(json.dumps(keep, indent=2, ensure_ascii=False) + "\n")
    print(dict(tally), "->", out)
    print("\n".join(flagged))


if __name__ == "__main__":
    main()
