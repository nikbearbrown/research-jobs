#!/usr/bin/env python3
"""Depth pass over existing source files: fill pi_email from profile pages,
and gather lab people pages so member counts can be read.

Run with the project venv (Playwright lives there):

    .venv/bin/python scripts/depth_pass.py emails data/sources/mit-*.json [--render-fallback]

        For every research-lab with no pi_email but a profile_url: fetch the
        profile page and look for an address (mailto: link or plain text) whose
        local part matches the PI's name. Exactly one distinct match is written
        to pi_email; zero or several leave it null with a note. With
        --render-fallback, a page that shows no address at all is retried once
        with Playwright (some sites only reveal email after JS runs).

    .venv/bin/python scripts/depth_pass.py prep-sizes data/sources/mit-*.json --out data/raw/depth/mit-size-pages.json

        For every research-lab with a lab_website but no member_count: fetch
        the site, follow its people/team/members link if it has one, cache the
        text under cache/_text/ and write a worklist (lab id, people page url,
        text path) for reading. Counting is done by reading each page, not by
        this script.

    .venv/bin/python scripts/depth_pass.py apply data/raw/depth/mit-sizes.json

        Merge read results ({source, lab_id, fields: {...}, note}) into source
        files. Only fills fields that are currently null, except `kind`, which
        may be set to "faculty-no-lab". The note is appended to `notes`.

    .venv/bin/python scripts/depth_pass.py sites --institution "Tufts University" [--dry-run]

        Lab-site discovery. For every research-lab with no lab_website but a
        profile_url: fetch the profile page and look for a link the page itself
        labels as the lab/group/research website ("Research Website", "Lab
        Website", "Research Group Website"), or names after the PI ("Utz
        Group", "The Kaplan Lab"). Links repeated on three or more profile
        pages are site navigation and are ignored. Exactly one distinct link
        is written to lab_website; several leave it null with a note listing
        them. When the profile page is itself the lab's site (its menu links a
        people page under its own address, as on research.bidmc.org), the
        profile address is recorded as the lab website. --dry-run prints the decisions (and the most common unmatched
        link labels, for tuning) without touching the source files.

Every change appends a short "Depth pass <date>: ..." sentence to the lab's
notes so the source of each value stays traceable.
"""
import argparse
import warnings
import datetime
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import CACHE_DIR, _slug_for, fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

try:  # a few profile addresses serve XML feeds; parsing them as HTML is fine for link reading
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    pass
TODAY = datetime.date.today().isoformat()

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
GENERIC_LOCAL = re.compile(
    r"^(info|admin|contact|webmaster|web|office|help|support|media|news|press|events?|"
    r"dept|department|chair|grad|graduate|undergrad|admissions|hr|jobs|careers|lab|labs|"
    r"communications|comms|noreply|no-reply|donotreply|privacy|accessibility|feedback)\b",
    re.I,
)
PEOPLE_LINK_RE = re.compile(
    r"^\s*(people|our people|team|our team|the team|members|lab members|group members|"
    r"current members|the lab|the group|group|lab|personnel|who we are|meet the (lab|team|group))\s*$",
    re.I,
)
PEOPLE_HREF_RE = re.compile(r"/(people|team|members|group-members|lab-members|personnel|our-team|the-team|lab|group)(/|$|\.html?)", re.I)
JOIN_LINK_RE = re.compile(r"\b(join|joining|openings|positions|opportunities|prospective|apply|recruit)", re.I)


LAB_SITE_LABEL_RE = re.compile(
    r"\b(lab|labs|laboratory|group|research|project)\b.{0,30}\b(web\s?site|web\s?page|home\s?page|site|page)\b"
    r"|\b(web\s?site|web\s?page|home\s?page)\b.{0,20}\b(lab|laboratory|group|research)\b",
    re.I,
)
LAB_NAME_LABEL_RE = re.compile(r"\b(lab|laboratory|group)\b", re.I)  # only with the PI's last name in the label
NOT_A_LAB_SITE_RE = re.compile(
    r"(myworkdayjobs|scholar\.google|ncbi\.nlm\.nih|pubmed|orcid\.org|linkedin\.|twitter\.com|//x\.com|facebook\.|instagram\.|"
    r"youtube\.|youtu\.be|researchgate\.|doi\.org|facultyprofiles\.tufts\.edu|drive\.google|docs\.google|"
    r"wikipedia\.org|amazon\.|bsky\.app|mastodon|arxiv\.org|semanticscholar|academia\.edu|//github\.com|"
    r"news\.|now\.tufts\.edu|/news/|/story/|/stories/|/article|/events?/|/20\d\d/\d\d/)",
    re.I,
)
PERSONAL_SITE_LABEL_RE = re.compile(
    r"^\s*(personal|(personal|faculty|my)\s+(web\s?site|web\s?page|home\s?page|page|site)|web\s?site|home\s?page)\s*$", re.I)
LABISH_URL_RE = re.compile(r"(lab(s|oratory)?\b|[-_/.]lab|lab[-_/]|group)", re.I)
ROSTER_LINK_RE = re.compile(
    r"^\s*(people|our people|team|our team|the team|members|lab members|group members|current members|"
    r"personnel|meet the (lab|team|group)|lab|the lab|group|the group|research group)\s*$", re.I)
# a link to one section of something (a publication list, a directory listing) is not a lab website
NOT_A_SITE_LABEL_RE = re.compile(r"\b(publications?|papers|directory|news|events?|calendar|seminars?|videos?|photos?|gallery)\b", re.I)
DOC_HREF_RE = re.compile(r"\.(pdf|docx?|pptx?|xlsx?|jpe?g|png|zip)($|\?)", re.I)


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def name_parts(pi_name):
    name = re.sub(r"\([^)]*\)", " ", pi_name or "")
    name = re.sub(r",.*$", "", name)  # drop ", PhD" etc.
    toks = [t for t in re.split(r"[\s.]+", fold(name)) if t]
    toks = [re.sub(r"[^a-z-]", "", t) for t in toks]
    toks = [t for t in toks if t and t not in {"dr", "prof", "jr", "sr", "ii", "iii", "phd", "md"}]
    if not toks:
        return None, None, []
    first, last = toks[0], toks[-1]
    # hyphenated / compound last names: accept any piece of 4+ letters
    lasts = {last} | {p for p in last.split("-") if len(p) >= 4}
    if len(toks) >= 3 and len(toks[-2]) >= 3:
        lasts.add(toks[-2] + toks[-1])
        lasts.add(toks[-2])
    return first, last, sorted(lasts)


def _prefix_split(local, a, b, min_a):
    """True if local == (prefix of a, len >= min_a or all of a) + (prefix of b, possibly empty)."""
    for i in range(1, len(local) + 1):
        head, tail = local[:i], local[i:]
        if not a.startswith(head) or (len(head) < min_a and head != a):
            continue
        if tail == "" and head == a:
            return True
        if tail and b.startswith(tail):
            return True
    return False


def email_matches_pi(addr, pi_name):
    first, last, lasts = name_parts(pi_name)
    if not first:
        return False
    local = fold(addr.split("@")[0])
    local_letters = re.sub(r"[^a-z]", "", local)
    if GENERIC_LOCAL.match(local) or not local_letters:
        return False
    f, l = first.replace("-", ""), last.replace("-", "")
    for ln in lasts:
        ln_l = ln.replace("-", "")
        if len(ln_l) >= 3 and ln_l in local_letters:
            return True
        if len(ln_l) >= 5 and ln_l[:4] in local_letters:  # kenstow@ for Kenstowicz, ymarz@ for Marzouk
            return True
    if len(f) >= 4 and local_letters.startswith(f) and len(local_letters) <= len(f) + 2:
        return True
    # first-name prefix + last-name prefix (russt, benh, talco, stephd) or the reverse (liju)
    if _prefix_split(local_letters, f, l, 3) or _prefix_split(local_letters, l, f, 2):
        return True
    # initials, with an optional middle initial: jbt@, ddv@, ngk@
    if re.fullmatch(f"{f[0]}[a-z]?{l[0]}", local_letters):
        return True
    return False


ASSISTANT_LOCAL = re.compile(r"(admin|asst|assist|office|hours|lab|group)|aa$", re.I)


def addresses_on_page(result):
    found = []
    html = result.get("html") or ""
    for m in re.finditer(r'href=["\']mailto:([^"\'?]+)', html, re.I):
        found.append(urllib.parse.unquote(m.group(1)).strip())
    text = result.get("text") or ""
    body = text.split("\n--- other links found")[0]
    found += EMAIL_RE.findall(body)
    out = []
    for a in found:
        a = a.strip().strip(".'\"").lower() if a else a
        if a and EMAIL_RE.fullmatch(a) and a not in out:
            out.append(a)
    return out


def append_note(lab, sentence):
    prev = (lab.get("notes") or "").rstrip()
    lab["notes"] = (prev + " " if prev else "") + f"Depth pass {TODAY}: {sentence}"


def source_paths(args):
    """Explicit files, or every source file whose `institution` is one of --institution."""
    if args.sources:
        return [Path(p) for p in args.sources]
    wanted = set(args.institution or [])
    out = []
    for p in sorted((ROOT / "data" / "sources").glob("*.json")):
        if json.loads(p.read_text()).get("institution") in wanted:
            out.append(p)
    return out


def research_labs(paths):
    for path in paths:
        path = Path(path).resolve()
        data = json.loads(path.read_text())
        yield path, data


def save(path, data):
    """Write changed lab objects back in place, keeping each object's existing
    formatting (one-line or indented) so diffs show only real changes. Source
    files mix styles, so the file is never re-serialized as a whole."""
    text = path.read_text()
    old_labs = {l["id"]: l for l in json.loads(text)["labs"]}
    dec = json.JSONDecoder()
    for lab in data["labs"]:
        if old_labs.get(lab["id"]) == lab:
            continue
        # search after "labs": a single-lab target's lab id can equal the file's own id
        labs_at = text.find('"labs"')
        key = '"id": ' + json.dumps(lab["id"], ensure_ascii=False)
        pos = text.find(key, labs_at)
        if pos < 0:
            key = '"id":' + json.dumps(lab["id"], ensure_ascii=False)
            pos = text.find(key, labs_at)
        start = text.rfind("{", 0, pos)
        _, end = dec.raw_decode(text, start)
        span = text[start:end]
        if "\n" in span:
            line_start = text.rfind("\n", 0, start) + 1
            pad = text[line_start:start]
            inner = re.search(r"\n( +)\"", span)
            step = len(inner.group(1)) - len(pad) if inner else 2
            rendered = json.dumps(lab, indent=step, ensure_ascii=False).replace("\n", "\n" + pad)
        else:
            rendered = json.dumps(lab, ensure_ascii=False)
        text = text[:start] + rendered + text[end:]
    path.write_text(text)


def cmd_emails(args):
    filled = tried = blocked = 0
    for path, data in research_labs(source_paths(args)):
        changed = False
        for lab in data["labs"]:
            if lab.get("kind") != "research-lab" or lab.get("pi_email") or not lab.get("profile_url"):
                continue
            prior = re.search(r" ?Depth pass [0-9-]+: profile page shows (no address matching|several addresses)[^;]*?(; left null rather than guess|; pi_email left null)\.", lab.get("notes") or "")
            if args.recheck and args.render_fallback and not prior:
                # a plain-only "no email" result is worth one rendered retry
                prior = re.search(r" ?Depth pass [0-9-]+: profile page shows no email address\.", lab.get("notes") or "")
            if args.recheck and prior:
                lab["notes"] = lab["notes"].replace(prior.group(0), "")
            elif re.search(r"Depth pass [0-9-]+: (profile page|pi_email)", lab.get("notes") or ""):
                continue  # already checked in an earlier run
            tried += 1
            url = lab["profile_url"]
            res = fetch(url)
            if res["status"] == "blocked-by-robots":
                blocked += 1
                append_note(lab, "profile page is blocked by robots.txt; pi_email not checked.")
                changed = True
                continue
            addrs = addresses_on_page(res) if res["html"] else []
            rendered = False
            if args.render_fallback and res["html"] is not None and not addrs and res.get("method") != "playwright":
                res = fetch(url, render=True, force=True)
                addrs = addresses_on_page(res) if res["html"] else []
                rendered = True
            if res["html"] is None:
                append_note(lab, f"profile page failed to load ({str(res['status'])[:80]}); pi_email not checked.")
                changed = True
                continue
            matches = [a for a in addrs if email_matches_pi(a, lab.get("pi_name"))]
            if len(matches) > 1:
                # prefer an address on the institution's own domain when there is one
                host = urllib.parse.urlsplit(url).netloc.lower().split(":")[0]
                base = ".".join(host.split(".")[-2:])
                same = [a for a in matches if a.endswith(base)]
                if len(same) == 1:
                    matches = same
            if len(matches) > 1:
                # drop assistant/office look-alikes (desimoneadmin@, langeraa@, wood_officehours@)
                personal = [m for m in matches if not ASSISTANT_LOCAL.search(m.split("@")[0])]
                if len(personal) == 1:
                    matches = personal
            how = " (only after rendering with Playwright)" if rendered else ""
            if len(matches) == 1:
                lab["pi_email"] = matches[0]
                append_note(lab, f"pi_email read from the profile page{how}.")
                filled += 1
            elif len(matches) > 1:
                append_note(lab, f"profile page shows several addresses that could be the PI's ({', '.join(matches[:3])}); left null rather than guess.")
            elif addrs:
                append_note(lab, "profile page shows no address matching the PI's name (only shared/office addresses); pi_email left null.")
            else:
                append_note(lab, "profile page shows no email address" + (" (plain and rendered)." if rendered else "."))
            changed = True
            print(f"{'OK ' if len(matches) == 1 else '-- '}{lab['id']}\t{lab.get('pi_email') or ''}", flush=True)
        if changed:
            save(path, data)
    print(f"emails: tried {tried}, filled {filled}, robots-blocked {blocked}", file=sys.stderr)


def canon(url):
    """Address with scheme, www. and trailing slash dropped, for telling two spellings of one link apart."""
    return re.sub(r"^https?://(www\.)?", "", url.strip(), flags=re.I).rstrip("/").lower()


# a label naming a center / institute / program is a hub, not one PI's lab site
HUB_LABEL_RE = re.compile(r"\b(cent(er|re)|institute|consortium|program(me)?|initiative|network|department)\b", re.I)


def lab_site_candidates(res, pi_name):
    """(url, label, why) for every link on a profile page that the page itself
    presents as the person's lab / group / research website."""
    from bs4 import BeautifulSoup

    if not res.get("html"):
        return []
    _, _, lasts = name_parts(pi_name)
    soup = BeautifulSoup(res["html"], "lxml")
    here = res["url"].split("#")[0].rstrip("/")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absu = urllib.parse.urljoin(res["url"], href).split("#")[0].strip()
        if not absu.startswith("http") or absu.rstrip("/") == here:
            continue
        if NOT_A_LAB_SITE_RE.search(absu) or DOC_HREF_RE.search(urllib.parse.urlsplit(absu).path):
            continue
        label = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if not label and isinstance(a.next_sibling, str):
            # umb.edu profile pages write <a href="..." class="button-cta" />Website</a>:
            # the anchor is self-closed, so its label is the text right after it
            label = re.sub(r"\s+", " ", a.next_sibling).strip()
        if not label or len(label) > 80 or NOT_A_SITE_LABEL_RE.search(label):
            continue
        why = None
        has_pi_name = any(len(ln) >= 3 and re.search(rf"\b{re.escape(ln)}\b", fold(label)) for ln in lasts)
        if re.search(r"\w['\u2019]s\b", label) and not has_pi_name:
            continue  # "Susan Forsburg's Lab Page" on someone else's profile: another person's lab
        if HUB_LABEL_RE.search(label) and not has_pi_name:
            continue  # "Rehabilitation Research and Training Center Website": a center, not a lab
        if LAB_SITE_LABEL_RE.search(label):
            why = "labelled"
        elif PERSONAL_SITE_LABEL_RE.match(label):
            why = "personal"
        elif LAB_NAME_LABEL_RE.search(label) and has_pi_name:
            why = "named"
        elif canon(label) == canon(absu) and urllib.parse.urlsplit(absu).netloc != urllib.parse.urlsplit(res["url"]).netloc:
            # seas.harvard.edu lists a person's sites under "Websites" with the bare
            # address as the link text: a website link with no say on whether it is a lab's
            why = "personal"
        if why and canon(absu) not in seen:
            seen.add(canon(absu))
            out.append((absu, label, why))
    return out


def profile_is_about(res, pi_name):
    """True when the profile page on record is visibly this person's page: a
    last name is in the page address, its <title> or its first headings. Some
    breadth-pass files paired a name with the next person's profile link; a
    lab website read from such a page would belong to someone else."""
    from bs4 import BeautifulSoup

    _, _, lasts = name_parts(pi_name)
    if not lasts:
        return True  # no PI name on record (labs found by lab name): nothing to compare
    parts = urllib.parse.urlsplit(res["url"])
    hay = [fold(urllib.parse.unquote(parts.path + " " + parts.query))]
    if res.get("html"):
        soup = BeautifulSoup(res["html"], "lxml")
        if soup.title:
            hay.append(fold(soup.title.get_text(" ", strip=True)))
        hay += [fold(h.get_text(" ", strip=True)) for h in soup.find_all(["h1", "h2"])[:6]]
    words = set(re.findall(r"[a-z]+", " ".join(hay)))
    squashed = re.sub(r"[^a-z]", "", " ".join(hay))
    for ln in lasts:
        bare = re.sub(r"[^a-z]", "", ln)
        if bare and (bare in words or (len(bare) >= 4 and bare in squashed)):
            return True
    return False


def own_roster_link(res):
    """A people / lab-members link that sits under the profile page's own
    address (research.bidmc.org/<name>/lab-members): the sign that the
    "profile" is itself the lab's site. Department navigation never qualifies,
    because a department's People page is not under one person's page."""
    from bs4 import BeautifulSoup

    if not res.get("html"):
        return None
    parts = urllib.parse.urlsplit(res["url"])
    if not parts.path.strip("/"):
        return None  # a bare host: everything is "under" it
    here = f"{parts.scheme}://{parts.netloc}{parts.path}".rstrip("/")
    for a in BeautifulSoup(res["html"], "lxml").find_all("a", href=True):
        absu = urllib.parse.urljoin(res["url"], a["href"].strip()).split("#")[0]
        if absu.startswith(here + "/") and absu[len(here):].strip("/") and PEOPLE_LINK_RE.search(a.get_text(" ", strip=True) or ""):
            return absu
    return None


def cmd_sites(args):
    todo = []
    sources = list(research_labs(source_paths(args)))
    for path, data in sources:
        for lab in data["labs"]:
            if lab.get("kind") != "research-lab" or lab.get("lab_website") or not lab.get("profile_url"):
                continue
            if re.search(r"Depth pass [0-9-]+: lab_website", lab.get("notes") or ""):
                continue  # already checked in an earlier run
            todo.append((path, lab))
    # pass 1: read every profile page, collect candidates
    pages = {}
    for _, lab in todo:
        url = lab["profile_url"]
        if url not in pages:
            pages[url] = fetch(url)
    cands = {id(lab): lab_site_candidates(pages[lab["profile_url"]], lab.get("pi_name")) for _, lab in todo}
    # a link shown on 3+ different profile pages is navigation, not one PI's lab site
    seen_on = {}
    for _, lab in todo:
        for u, _, _ in cands[id(lab)]:
            seen_on.setdefault(canon(u), set()).add(lab["profile_url"])
    boiler = {u for u, ps in seen_on.items() if len(ps) >= 3}
    filled = several = none = failed = 0
    changed_paths = set()
    for path, lab in todo:
        res = pages[lab["profile_url"]]
        if res["html"] is None:
            failed += 1
            why = "is blocked by robots.txt" if res["status"] == "blocked-by-robots" else f"failed to load ({str(res['status'])[:80]})"
            append_note(lab, f"lab_website not checked: the profile page {why}.")
            changed_paths.add(path)
            print(f"!! {lab['id']}\t{why}", flush=True)
            continue
        if not profile_is_about(res, lab.get("pi_name")):
            failed += 1
            append_note(lab, "lab_website not checked: the profile page on record does not show this person's name in its "
                             "address, title or headings (it may be a lab or center page, or another person's page).")
            changed_paths.add(path)
            print(f"!! {lab['id']}\tprofile page is not visibly {lab.get('pi_name')}'s\t{lab['profile_url']}", flush=True)
            continue
        cs = [c for c in cands[id(lab)] if canon(c[0]) not in boiler]
        # a "website" link that also sits on another person's profile is not this person's site
        personal = [c for c in cs if c[2] == "personal" and len(seen_on[canon(c[0])]) == 1]
        cs = [c for c in cs if c[2] != "personal"]
        labelled = [c for c in cs if c[2] == "labelled"]
        if len(labelled) == 1:
            cs = labelled  # an explicit "website" label beats a link that merely names the lab
        own = own_roster_link(res) if not cs else None
        if own:
            lab["lab_website"] = lab["profile_url"]
            append_note(lab, f"lab_website set to the profile page, which is the lab's own site: its menu links a people page under the same address ({own}).")
            filled += 1
            changed_paths.add(path)
            print(f"OK {lab['id']}\t[profile page is the lab site]\t{own}", flush=True)
            continue
        if not cs and 1 <= len(personal) <= 4:
            # The profile only offers "Personal Website" / bare-address links. One is
            # recorded as the lab site only when it visibly is one: its address names a
            # lab or group, or its own menu links a people / team / lab page.
            passed = []
            for url, label, _ in personal:
                parts = urllib.parse.urlsplit(url)
                if LABISH_URL_RE.search(parts.netloc + parts.path):
                    passed.append((url, label, "its address names a lab or group"))
                    continue
                home = fetch(url)
                roster = find_link(home, ROSTER_LINK_RE) if home.get("html") else None
                if roster:
                    passed.append((url, label, f"its own menu links a people or lab page ({roster})"))
            if len(passed) == 1:
                url, label, basis = passed[0]
                lab["lab_website"] = url
                append_note(lab, f"lab_website read from the profile page's {label!r} link; taken as the lab site because {basis}.")
                filled += 1
                print(f"OK {lab['id']}\t{label!r}\t{url}\t[{basis[:40]}]", flush=True)
            elif len(passed) > 1:
                several += 1
                append_note(lab, "lab_website left null: the profile page links several websites that look like lab sites ("
                            + ", ".join(u for u, _, _ in passed[:3]) + "), rather than guess.")
                print(f"?? {lab['id']}\t" + " | ".join(u for u, _, _ in passed), flush=True)
            else:
                none += 1
                sites_ = ", ".join(u for u, _, _ in personal[:3])
                append_note(lab, f"lab_website left null: the profile page links a personal website ({sites_}) that shows no lab or people page.")
                print(f".. {lab['id']}\tpersonal site, no lab signs\t{sites_}", flush=True)
            changed_paths.add(path)
            continue
        if len(cs) == 1:
            url, label, _ = cs[0]
            lab["lab_website"] = url
            shared = len(seen_on[canon(url)]) > 1
            append_note(lab, f"lab_website read from the profile page (link labelled {label!r})"
                        + ("; the same link is on another PI's profile, so the site may be shared." if shared else "."))
            filled += 1
            print(f"OK {lab['id']}\t{label!r}\t{url}", flush=True)
        elif len(cs) > 1:
            several += 1
            append_note(lab, "lab_website left null: the profile page links several possible lab websites ("
                        + ", ".join(u for u, _, _ in cs[:3]) + "), rather than guess.")
            print(f"?? {lab['id']}\t" + " | ".join(f"{l!r} {u}" for u, l, _ in cs[:4]), flush=True)
        else:
            none += 1
            append_note(lab, "lab_website not found: the profile page links no lab or research-group website.")
        changed_paths.add(path)
    if args.dry_run:
        import collections

        labels = collections.Counter()
        for url, res in pages.items():
            if not res.get("html"):
                continue
            from bs4 import BeautifulSoup

            host = urllib.parse.urlsplit(url).netloc
            for a in BeautifulSoup(res["html"], "lxml").find_all("a", href=True):
                absu = urllib.parse.urljoin(url, a["href"])
                if absu.startswith("http") and urllib.parse.urlsplit(absu).netloc != host:
                    labels[re.sub(r"\s+", " ", a.get_text(" ", strip=True))[:50]] += 1
        print("most common off-site link labels:", file=sys.stderr)
        for lab_, n in labels.most_common(args.top):
            print(f"  {n:4} {lab_!r}", file=sys.stderr)
    else:
        for path, data in sources:
            if path in changed_paths:
                save(path, data)
    print(f"sites: checked {len(todo)}, filled {filled}, several {several}, none {none}, unreadable {failed}, "
          f"navigation links ignored {len(boiler)}" + (" (dry run, nothing written)" if args.dry_run else ""), file=sys.stderr)


def find_link(res, label_re, href_re=None):
    from bs4 import BeautifulSoup

    if not res.get("html"):
        return None
    soup = BeautifulSoup(res["html"], "lxml")
    base_host = urllib.parse.urlsplit(res["url"]).netloc.lower()
    best = None
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:")) or href == "#":
            continue
        absu = urllib.parse.urljoin(res["url"], href).split("#")[0]
        if urllib.parse.urlsplit(absu).netloc.lower() != base_host:
            continue
        if absu.rstrip("/") == res["url"].rstrip("/"):
            continue
        label = a.get_text(" ", strip=True)
        if label and label_re.search(label):
            return absu
        if best is None and href_re is not None and href_re.search(urllib.parse.urlsplit(absu).path):
            best = absu
    return best


def text_path_for(url):
    host = urllib.parse.urlsplit(url).netloc.lower()
    d = CACHE_DIR / "_text" / host
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{_slug_for(url)}.txt"


def cmd_prep_sizes(args):
    work = []
    for path, data in research_labs(source_paths(args)):
        for lab in data["labs"]:
            if lab.get("kind") != "research-lab" or lab.get("member_count") is not None or not lab.get("lab_website"):
                continue
            if args.site_found_on and f"Depth pass {args.site_found_on}: lab_website" not in (lab.get("notes") or ""):
                continue  # only the lab sites the `sites` step recorded on that date
            site = lab["lab_website"]
            item = {"source": str(path.relative_to(ROOT)), "lab_id": lab["id"], "pi_name": lab.get("pi_name"),
                    "lab_website": site, "home_status": None, "people_url": None, "join_url": None,
                    "home_text": None, "people_text": None}
            home = fetch(site)
            if home["html"] is not None and len(home["text"] or "") < 400 and home.get("method") != "playwright":
                home = fetch(site, render=True, force=True)
            item["home_status"] = str(home["status"])
            if home["text"]:
                tp = text_path_for(site)
                tp.write_text(home["text"], encoding="utf-8")
                item["home_text"] = str(tp.relative_to(ROOT))
                people = find_link(home, PEOPLE_LINK_RE, PEOPLE_HREF_RE)
                item["join_url"] = find_link(home, JOIN_LINK_RE)
                if people:
                    pres = fetch(people)
                    if pres["html"] is not None and len(pres["text"] or "") < 400 and pres.get("method") != "playwright":
                        pres = fetch(people, render=True, force=True)
                    item["people_url"] = people
                    if pres["text"]:
                        tp = text_path_for(people)
                        tp.write_text(pres["text"], encoding="utf-8")
                        item["people_text"] = str(tp.relative_to(ROOT))
                    else:
                        item["people_status"] = str(pres["status"])
            work.append(item)
            print(f"{item['lab_id']}\thome={item['home_status'][:30]}\tpeople={item['people_url']}", flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(work, indent=2, ensure_ascii=False) + "\n")
    print(f"prep-sizes: {len(work)} labs -> {out}", file=sys.stderr)


APPLY_FIELDS = {"member_count", "member_breakdown", "members_page_url", "join_page_url", "join_notes",
                "admin_name", "admin_email", "pi_email", "accepting_grad_students", "lab_name", "research_summary",
                "pi_name", "pi_title"}


def cmd_apply(args):
    results = json.loads(Path(args.results).read_text())
    by_source = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)
    applied = 0
    for src, rs in by_source.items():
        path = ROOT / src
        data = json.loads(path.read_text())
        labs = {l["id"]: l for l in data["labs"]}
        for r in rs:
            lab = labs.get(r["lab_id"])
            if lab is None:
                print(f"missing lab {r['lab_id']} in {src}", file=sys.stderr)
                continue
            for k, v in (r.get("fields") or {}).items():
                if k == "kind":
                    if v == "faculty-no-lab" and lab.get("kind") == "research-lab":
                        lab["kind"] = v
                    continue
                if k not in APPLY_FIELDS or v is None:
                    continue
                if lab.get(k) is None:
                    lab[k] = v
            if r.get("note"):
                append_note(lab, r["note"])
            applied += 1
        save(path, data)
    print(f"apply: {applied} results across {len(by_source)} files", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("emails")
    e.add_argument("sources", nargs="*")
    e.add_argument("--institution", action="append")
    e.add_argument("--render-fallback", action="store_true")
    e.add_argument("--recheck", action="store_true", help="retry labs an earlier run found no/several name matches for")
    s = sub.add_parser("prep-sizes")
    s.add_argument("sources", nargs="*")
    s.add_argument("--institution", action="append")
    s.add_argument("--out", required=True)
    s.add_argument("--site-found-on", metavar="YYYY-MM-DD",
                   help="only labs whose lab_website was recorded by the sites step on this date")
    w = sub.add_parser("sites")
    w.add_argument("sources", nargs="*")
    w.add_argument("--institution", action="append")
    w.add_argument("--dry-run", action="store_true")
    w.add_argument("--top", type=int, default=40, help="with --dry-run: how many unmatched link labels to list")
    a = sub.add_parser("apply")
    a.add_argument("results")
    args = ap.parse_args()
    {"emails": cmd_emails, "sites": cmd_sites, "prep-sizes": cmd_prep_sizes, "apply": cmd_apply}[args.cmd](args)


if __name__ == "__main__":
    main()
