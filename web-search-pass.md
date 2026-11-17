# Web-search pass: instructions for the machine taking it over

Read `CLAUDE.md` first (the project rules), then this file. This file is the
whole job for one machine: find lab websites by web search for the labs that
have none, check each one against the site itself, and add it.

## Why this pass exists

The directory lists Boston / Cambridge research labs. The point is small labs
(10 people or fewer) with a real contact, so a lab needs a website before its
people page can be read for a size.

About 3,950 labs have a PI but no lab website and no size. Both sources on
the universities' own sites have been used up:

- the PI's profile page links no lab site (`scripts/depth_pass.py sites`);
- the department has no labs listing that names it (`scripts/find_lab_listings.py`).

On 2026-11-17 the project owner decided that a web search may be used to
**find** a candidate site for these labs. A candidate is still recorded only
when the site itself confirms it. A search result is never evidence on its
own.

## Setup (once)

```bash
git clone https://github.com/nikbearbrown/research-jobs.git
cd research-jobs
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/playwright install chromium
```

Run every script below with `.venv/bin/python` (or `python3` if the three
packages are installed system-wide). `cache/` and `.venv/` are gitignored, so
a new checkout fetches pages afresh.

Check that this machine can push: `git push --dry-run origin main`. If it
cannot, still do the work, commit locally after every batch, and say in your
report that nothing has been pushed.

## The routine, one batch at a time

A batch is 100 labs. Batches are numbered `batch-001`, `batch-002`, ...; look
in `data/raw/web-search/` for the last number used.

1. **Get up to date.** `git pull --rebase origin main`. If `data/labs.json`
   or `data/labs.csv` conflict, do not merge them by hand: take either side,
   finish the rebase, and run `scripts/build.py`, which regenerates both.

2. **Make the worklist.**

   ```bash
   .venv/bin/python scripts/web_search_pass.py worklist --out data/raw/web-search/batch-001-worklist.json --limit 100
   ```

   It picks research-labs with a PI, no `lab_website`, no `member_count` and
   no earlier web-search note. Labs that already have a PI email come first.
   Each item gives the PI, title, institution, unit, `profile_url` and two
   suggested queries. `--institution "MIT"` or `--source data/sources/<file>.json`
   narrows it.

3. **Search.** For each item, use your web search tool with the first
   suggested query (`"<PI name>" <institution> lab`); if nothing fits, try
   the second. Pick at most one candidate: the lab's or research group's own
   site (rules below). If no result is clearly that, the answer is null.
   Two results is not a reason to guess: prefer null.

4. **Write the results** to `data/raw/web-search/batch-001-results.json`, a
   JSON list with one object per worklist item:

   ```json
   {"source": "data/sources/bc-biology.json",
    "lab_id": "bc-biology-anthony-t-annunziato",
    "lab_website": "https://example-lab.org/",
    "query": "\"Anthony T. Annunziato\" Boston College lab",
    "note": null}
   ```

   `lab_website` is the candidate's address exactly as the search result
   gives it, or `null` when no lab site was found. `note` is optional, one
   plain sentence (for example "The PI is listed as emeritus.").

5. **Apply, dry run first.**

   ```bash
   .venv/bin/python scripts/web_search_pass.py apply data/raw/web-search/batch-001-results.json --dry-run
   .venv/bin/python scripts/web_search_pass.py apply data/raw/web-search/batch-001-results.json
   ```

   `apply` fetches each candidate (and its people page) with
   `scripts/fetch.py` and accepts it only if all four hold:

   1. it is not a profile, publication, social-media, news or directory page;
   2. the site names the PI (full name, or a title like "Doe Lab");
   3. the site is tied to the PI's institution (it is on the institution's
      domain, or its text names the institution or shows an address at it);
   4. it looks like a lab or group site (its address or title names a lab or
      group, or its menu has a people or team page).

   Accepted: `lab_website` is set and a note records the query and what was
   checked. Rejected: `lab_website` stays null and the note says why. Null:
   a note records that the search found nothing, so the lab is not searched
   again. Read the dry-run output before the real run; lines start with `OK`
   (accepted), `XX` (rejected, with the reason) or `..` (no candidate).

6. **Build, commit, push.**

   ```bash
   .venv/bin/python scripts/build.py
   git add data/sources data/labs.csv data/labs.json data/raw/web-search
   git commit -m "Web-search pass batch 001: N lab websites added (M searched)"
   git push origin main
   ```

   Never `git add -A`: the checkout may hold untracked folders that belong to
   other work. The commit message says what was added and the new totals
   (labs with a lab website, labs sized, small labs), as `CLAUDE.md` rule 6
   asks. `scripts/build.py` prints the totals.

7. **Every third batch, read the new sites for sizes.** A website is only
   useful once its people page has been read:

   ```bash
   .venv/bin/python scripts/depth_pass.py prep-sizes --only-note "found by web search" --out data/raw/depth/web-search-001-size-pages.json
   ```

   (add `--institution "<name>"` once per institution, or pass source files;
   the command needs one or the other). Then read each item as
   `scripts/depth_read_brief.md` describes, check the results with
   `scripts/merge_read_results.py`, and write them with
   `scripts/depth_pass.py apply`. Readers may be subagents; only the main
   session runs git, `build.py`, `merge_read_results.py` and `apply`.
   `prep-sizes` skips labs that already have a size, so each round picks up
   only the sites added since the last one.

## What counts as the lab's site

Take it as the candidate:

- a site on its own domain named for the lab or PI's group (`doelab.org`);
- a university-hosted lab or group site (`doelab.mit.edu`,
  `sites.bu.edu/doelab`, `scholar.harvard.edu/doe` when it has a people page);
- a Google Sites, GitHub Pages, Squarespace or Wix site titled as the lab.

Do not take:

- the PI's profile page on a department, school, hospital or institute site;
- Google Scholar, ORCID, PubMed, ResearchGate, LinkedIn, X, Bluesky, YouTube;
- news stories, press releases, Wikipedia, course pages, a CV;
- a center, institute or department the PI belongs to or directs;
- a lab of another person with the same surname;
- the PI's lab at a previous institution (the site must show the institution
  named in the worklist);
- a personal homepage with no group (the checker rejects these; a null
  result is better than making it try).

## Hard rules

- **Never record from the search result alone.** The title and snippet of a
  result are not a page of the lab's site. Only `apply` writes a website.
- **Never edit a source file by hand** and never change a value that is
  already there. This pass only fills `lab_website` where it is null, and
  appends notes.
- **Never guess or build an address.** A candidate is an address a search
  result linked to.
- **Use your web search tool for searching.** Do not fetch a search engine's
  results page with `scripts/fetch.py` or any other tool.
- **Do not work around a block.** If a site answers Access Denied, 403, a
  CAPTCHA, or robots.txt disallows it, the checker records that and moves
  on. Do not change the User-Agent, use another fetcher, or retry through a
  browser.
- **Be polite.** All page fetching goes through `scripts/fetch.py` (one
  request per second per host, robots.txt, the project's honest User-Agent).
- **Emails are not part of this pass.** Do not copy an email from a search
  result. If the lab's site shows the PI's address, the size-reading step
  records it.
- **Plain, exact notes.** Notes are written by the scripts. Your own `note`
  field is one factual sentence or null.

## The first batch is a pilot

Nobody knows yet how often a search finds a real lab site. After
`batch-001`:

1. Report: searched, candidates found, accepted, rejected (grouped by
   reason), none.
2. Open ten accepted sites yourself (their cached text is under
   `cache/_text/<host>/`) and confirm each is that PI's current lab at that
   institution. Report how many of the ten are right.
3. If more than one of the ten is wrong, stop. Do not run more batches;
   report what went wrong so the checker in `scripts/web_search_pass.py` can
   be tightened first.
4. If the ten hold up, carry on batch by batch. Repeat the ten-site check
   every fifth batch.

## Keeping the record current

After every batch that changes the totals, update the Status paragraph in
`CLAUDE.md` (one sentence: batches done, websites added, sizes added, new
totals) and the web-search paragraph under Coverage in `README.md`, and
commit them with the batch.

Stop and report when the worklist comes back empty, when the pilot check
fails, or when something in these instructions does not match what you find
in the repo.
