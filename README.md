# research-jobs

A directory of research labs in the Boston and Cambridge area: who runs each lab, how big it is, who to contact, and whether it says how to join. The aim is to find **small labs** (10 people or fewer) and a real contact for each, department by department and institute by institute.

## What is here

Agents: start with `CLAUDE.md`.

| Path | What |
|---|---|
| `data/sources/<source-id>.json` | One file per department or institute: the listing pages read, the date, every lab found, and people who were checked but are not labs |
| `data/labs.json`, `data/labs.csv` | All labs from every source, merged (generated, do not edit) |
| `data/targets.csv` | The scrape target list: 638 think tanks, policy centers, science institutes, AI groups, hospitals and departments, with start URL, priority and what to collect |
| `data/discovery/*.csv` | Raw unit lists found by crawling each institution's own index pages (Harvard, MIT, BU/Northeastern/Tufts, Brandeis/BC/UMass Boston/hospitals) |
| `data/raw/` | Raw scraper output, kept as read, before it is folded into `data/sources/` |
| `data/to-read.txt` | Lab sites and profiles still to read (the next scrape pass) |
| `scripts/merge_discovery.py` | Folds the discovery lists into `targets.csv` |
| `scripts/build.py` | Rebuilds `labs.json` and `labs.csv` from the source files |
| `CONVENTIONS.md` | Naming and data rules |

## Coverage (2026-10-28)

`data/to-read.txt` is empty. `data/targets.csv` priority-1 work has covered all of Harvard, all of MIT, and all of Boston University (254 targets total): 3,951 labs so far, 1,069 with a PI email.

| Source | Labs | Small (≤10) | Medium (11–20) | Large (>20) | Size unknown |
|---|---|---|---|---|---|
| Harvard Chemistry and Chemical Biology (faculty + lecturers) | 25 + 1 core facility | 5 | 6 | 11 | 3 |
| Harvard Molecular and Cellular Biology | 36 | 18 | 10 | 7 | 1 |
| MIT Chemistry | 42 | 11 | 17 | 9 | 5 |
| Whitehead Institute (Members, Fellows, AI Fellow) | 24 | 4 | 5 | 3 | 12 |
| Rowland Institute (Fellows) | 8 | 8 | 0 | 0 | 0 |
| Ragon Institute | 28 | 10 | 10 | 4 | 4 |
| 76 Harvard `targets.csv` rows (breadth pass: Univ./FAS, HMS, HSPH, HSDM, SEAS sub-areas, MRSEC, Smithsonian CfA) | 872 | 0 | 0 | 1 | 870 (+1 core facility) |
| 124 MIT `targets.csv` rows (departments, institutes/centers, all 23 Media Lab groups, all 13 DUSP/Architecture small labs) | 1,355 | 28 | 30 | 17 | 1,270 (+10 non-research entries) |
| 54 Boston University `targets.csv` rows (Chobanian & Avedisian SOM, CAS, College of Engineering, SPH, University-wide centers) | 1,602 | 0 | 0 | 0 | 1,600 (+2 non-research entries) |

Harvard Chemistry, Harvard MCB and MIT Chemistry now have a PI email for every lab (from each department's own directory/profile pages); Ragon's are mostly Cloudflare-obfuscated on the institute's lab pages, so only 5 of 28 are confirmed (see `notes` for unverified decoded guesses). Whitehead's Gerald Fink is listed under `non_lab_people` (retired, no active group) rather than as a lab. The Harvard and MIT rows are breadth passes from each site's own directory — HMS departments have especially strong coverage (most labs have both a PI email and lab site, via a reusable parser for HMS's shared Drupal people-directory template, `scripts/parse_hms_people.py`) — but for department-wide directories, member counts and join info are a later per-PI pass. The ~35 single-lab/single-group MIT targets (every Media Lab group, every DUSP small lab, AgeLab, Deshpande, d-Lab, Sea Grant, and similar) got the full `to-read.txt`-style depth pass instead, since each was just one site to read anyway — most of those already have a member count and join page. Cross-cutting hubs (Harvard's CMSA/HDSI/Salata/MRSEC/SEAS-sub-areas; MIT's CBMM, CEHS, SCSB, and several Sloan/interdepartmental centers) list PIs who are already recorded under their home department's source file, so those were deliberately recorded thin (an org-level entry, a cross-reference note, or just the hub's own core staff) rather than duplicated — see each file's `notes`.

Remaining "unknown" sizes are each explained in that lab's `notes`. The big one on the Harvard side: an Akamai "Access Denied" block first seen on `arp.harvard.edu` turned out to hit a much wider, and apparently shifting, set of `harvard.edu` subdomains from this network — including some official department sites that worked in earlier sessions (`chemistry.harvard.edu` itself now fails) and all of `hsdm.harvard.edu`. HMS (`*.hms.harvard.edu`), HSPH (`hsph.harvard.edu`), and most of SEAS/MRSEC were *not* affected. On the MIT side, a cluster of sites use JS-filterable or infinite-scroll directories that didn't fully render even with Playwright (`energy.mit.edu`/MITEI, `nse.mit.edu`, `psfc.mit.edu`, `space.mit.edu`/Kavli, `ki.mit.edu`/Koch Institute, `lids.mit.edu`); `rle.mit.edu/people` and `lfe.mit.edu` are robots.txt-blocked; `smart.mit.edu` is unreachable (known redirect loop). The Smithsonian Center for Astrophysics' people page has the same JS "Load More" issue. `wi.mit.edu`-hosted Whitehead lab sites that return a robot-challenge screen, dead/placeholder pages, and a couple of JS roster carousels whose roles couldn't be mapped to names account for the rest. Rowland Fellows run independent groups of one to three people; their counts come from the institute directory and may undercount.

BU's department directories mostly don't show a PI email on the listing page itself (would need an individual profile-page visit, a later pass), which is why the BU row's `with_email` count is low — this isn't a site-blocking problem, just a template property. BU's own `scripts/parse_bu_people.py` and `scripts/build_bu_source.py` handle its shared "Name, degree → profile page" directory template (BU College of Engineering: BME/ECE/ME/MSE/SE each have genuinely department-filtered directories, re-verified after an initial pass wrongly assumed they were unfiltered and under-covered ME/MSE — see CLAUDE.md). A handful of BU targets (Cancer Center, CBR, CSN, Evans Center, Hariri Institute and its AIR initiative, Dept. of Medicine, Pathology) are `partial`: cross-cutting hubs recorded thin, umbrella departments whose real per-Section pages weren't found, or pages that rendered empty/navigation-only.

`data/targets.csv` priority 1: 196 `done`, 63 `partial`, 133 `todo` (of 392). Next: Northeastern, Tufts, Brandeis, BC, UMass Boston, hospitals.

`data/targets.csv` priority 1: 150 `done`, 55 `partial`, 187 `todo` (of 392). Broad/Wyss/Koch/McGovern/Picower are already covered (Wyss, Koch and McGovern were scraped as part of the Harvard/MIT institution passes above). Next: BU, Northeastern, Tufts, Brandeis, BC, UMass Boston, hospitals.

`data/targets.csv` priority 1: 47 `done`, 35 `partial`, 310 `todo` (of 392). Next: MIT, then Broad/Wyss/Koch/McGovern/Picower, BU, Northeastern, Tufts, Brandeis, BC, UMass Boston, hospitals.

`data/targets.csv`: 43 of 392 priority-1 rows attempted so far (14 `done`, 29 `partial` — 6 of those pre-dating this round). 349 still `todo`: the rest of Harvard (HSPH's many departments, SEAS's 7 sub-areas, Smithsonian CfA, MRSEC, and HMS's real per-department pages once found), then MIT, Broad/Wyss/Koch/McGovern/Picower, BU, Northeastern, Tufts, Brandeis, BC, UMass Boston and hospitals.

## How a lab is classified

- **kind**: `research-lab` (a PI-led group), `core-facility` (an instrument or service centre). Teaching-only lecturers and staff go in the source file's `non_lab_people` list.
- **size** comes from counting current members on the lab's own people page (alumni excluded): `small` ≤10, `medium` 11–20, `large` >20, `unknown` when the page could not be read.
- **contact**: the PI email from the department profile, plus the lab administrator and any join/positions instructions found on the lab site.

## Update

```bash
python3 scripts/build.py
```

Sizes marked `unknown` are labs whose own websites could not be read in the first pass. They are the next thing to fill in.

## Target list (`data/targets.csv`)

638 targets (2026-10-27): Harvard (all schools), MIT (all schools, interdepartmental labs, every Media Lab group), Boston University, Northeastern, Tufts, Brandeis, Boston College, UMass Boston, Mass General Brigham, Boston Children's, BIDMC, Dana-Farber, Joslin, Hebrew SeniorLife, Forsyth, plus Boston/Cambridge think tanks, policy centers and Kendall Square / Longwood institutes. 392 are priority 1 (science and AI units with PI-led labs); 378 have a people/faculty directory URL. The independent think tanks and institutes come from the October 2026 snapshot `Think Tanks and Research Institutes in Boston & Cambridge`.

| Column | Meaning |
|---|---|
| `category` | `science-institute`, `ai-research`, `research-center`, `university-department`, `school`, `hospital`, `university-policy-center`, `policy-think-tank`, `policy-adjacent` |
| `start_url` | Homepage where a scraper starts |
| `people_url` | Faculty / people / staff directory, when found |
| `careers_url` | Jobs, RA, fellowship or join page, when found |
| `url_from` | `checked` (loaded or linked from an official page), `snapshot-source` (cited in the snapshot), `unverified` (from memory; confirm on first fetch), blank (still to find) |
| `priority` | 1 = science departments and institutes with many small PI-led labs (main target); 2 = social science, business, law, education, design and policy centers; 3 = small standalone think tanks, advocacy groups, humanities |
| `collect` | What to record for that target |
| `listed_in` | `snapshot`, `snapshot-dagger` (snapshot entry marked not source-checked), `earlier-queue`, `harvard-index` |
| `status` | `todo`, `partial`, `done` |

Think tanks and policy centers do not have labs, so for them the unit is the organization or one of its programs, and the contact is a research lead or the careers page.

Still to resolve: people pages for many centers (blank `people_url`), BU's full 132-entry centers directory (only page 1 read), Northeastern's institutes beyond the first 87, Fletcher and UMass Boston McCormack centers, and sites that loop between http and https (CSAIL, McGovern, MIT CIS, RLE).
