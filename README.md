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

## Coverage (2026-10-29)

`data/to-read.txt` is empty, and every priority-1 `targets.csv` row has been attempted (296 `done`, 96 `partial`, 0 `todo`, of 392): 5,843 labs so far, 1,685 with a PI email, 439 with a known size. Priority 2 and 3 (policy centers, business/law/education/design, small think tanks) are still untouched — 246 rows.

**Lab-site discovery (2026-11-10): Tufts, Boston College and UMass Boston.** These three had almost no lab websites recorded, so the depth pass could not size them. `scripts/depth_pass.py sites` now reads each lab's profile page for a link the page itself labels as the lab, group or research website (a "Personal Website" link counts only when its address names a lab or its own menu links a people page), and `scripts/umb_profiles.py` first fills UMass Boston's missing profile links from the department listing pages. 230 lab websites found (Tufts 133 of 465 labs now have one, up from 2; BC 42 of 203, up from 1; UMass Boston 58 of 191, up from 0) and 114 UMass Boston emails (186 of 191, up from 72). The 232 lab sites were then read for member counts: 163 sized (Tufts 86 sized, 68 small; BC 33 sized, 21 small; UMass Boston 49 sized, 37 small). The other 69 are dead links, personal pages with no roster, institutes rather than one PI's group, or rosters too stale to tell who is current; each lab's `notes` says which. Labs whose profile page links no lab site at all (332 at Tufts, 161 at BC, 133 at UMass Boston) are still unsized. Totals: 6,381 labs, 3,421 with a PI email, 1,485 with a lab website, 1,128 with a known size, 641 small (344 of those with an email).

**Lab-site discovery, the other institutions (2026-11-10).** The same step was then run on Boston University, MIT, Harvard, Northeastern, Mass General Brigham, BIDMC and the smaller institutes (about 2,400 profile pages). It recorded 582 more lab websites, and 15 of those were cleared again when reading showed the linked site was a center, journal, program or personal page. Reading the new sites sized 418 more labs.

| Institution | Labs | With a lab website (before) | Sized (before) | Small (before) |
|---|---|---|---|---|
| Boston University | 1,602 | 254 (109) | 169 (57) | 95 (38) |
| MIT | 1,353 | 344 (128) | 254 (89) | 90 (31) |
| Harvard | 790 | 346 (231) | 206 (123) | 78 (51) |
| Northeastern | 409 | 128 (104) | 150 (138) | 140 (134) |
| BIDMC | 75 | 60 (0) | 42 (0) | 31 (0) |
| Forsyth Institute | 25 | 6 (0) | 4 (0) | 4 (0) |
| Mass General Brigham | 547 | 326 (326) | 228 (228) | 132 (132) |

Mass General Brigham's own lab pages link no separate lab website, so nothing changed there. On research.bidmc.org the "profile" page is the lab's own site, so its address is recorded as the lab website. Sites that could not be sized are dead or refuse the project's fetcher (several Harvard-hosted lab sites return "Access Denied"; not worked around), are a shared or multi-PI group, or show no readable roster; each lab's `notes` says which. Labs whose profile page links no lab site are still unsized (BU 566, MIT 450, Harvard 340, Tufts 287, Mass General Brigham 221, BC 158, UMass Boston 127, Northeastern 116). Two older data problems were found and left as they are for the owner to decide: about 55 Northeastern (Bouvé) and Brandeis labs carry the next person's `profile_url`, and 122 Northeastern College of Science labs are recorded as one person because the college's listing page names only the PI. Totals: 6,380 labs, 3,442 with a PI email, 2,051 with a lab website, 1,546 with a known size, 825 small (492 of those with an email).

**Depth pass in progress** (per the project owner, started 2026-10-29, institution by institution): for every lab with a known website but no member count, visit its people page and fill in size and join info; for every lab with no email but a department profile page, check that page for one; reclassify anything that's clearly not an independent research group as `kind: "faculty-no-lab"` (recorded in `labs.json` for completeness, left out of `labs.csv` so it stays a list of real labs); capture the ~555-lab Mass General Brigham institutes/centers search still outstanding from the first pass. **MIT is done** (2026-11-02, via the reusable `scripts/depth_pass.py`: `emails` matches a profile page's addresses to the PI's name, `prep-sizes` fetches each lab site's people page for reading, `apply` merges the read results, with every change noted in the lab's `notes`): 1,344 labs, 842 with an email (up from 558), 88 with a known size (up from 75), 31 small, 1 reclassified. Most MIT size gaps are hub entries (CBMM, CCSE, J-WAFS, Deshpande and similar) whose `lab_website` is the center's site, not the PI's group — left null, the PI's own lab is under their home department. **Hospitals and research institutes are done** (2026-11-03): 532 hospital lab sites read for member counts, join info and (for MGB search tiles that link straight to a lab's own site) PI names. MGB search: 547 labs, 141 with an email, 228 with a known size, 132 small. Dana-Farber: 194 labs, 33 with an email (up from 0), 140 sized (up from 0), 45 small. MGH: 31 sized (up from 0), 16 small, 1 reclassified (a business-development director with no lab). Ragon 26 sized, Whitehead 13. `labs.dana-farber.org` lab sites turned out to be readable after all: guessed paths like `/people` serve the home page, but the roster path each lab's own menu links to works. **Mass General Brigham search crawled** (2026-11-02): the MGB-wide institutes/centers/labs search (610 results, 559 labs) is now in `mgh-lab-search.json` via `scripts/crawl_mgb_labs.py` + `scripts/build_mgb_source.py`: 547 new labs (12 already recorded elsewhere were skipped), 67 with an email, 64 with a known size, 45 small. Labs on MGB's own pages get the PI, member count and roles from the page's Research Team grid; about 330 tiles link straight to a lab's own site and are name + website only until read. Hospital emails from profile pages: MGH 27 (up from 13), BIDMC 24 (up from 0), Forsyth 7 (up from 0), Ragon 22 (up from 5, Cloudflare-obfuscated addresses confirmed by rendering), Whitehead 22 (up from 19). Dana-Farber's profile pages show no email. **UMass Boston** had nothing for this pass: none of its 191 labs has a profile URL or lab website recorded (72 have an email), so it needs a lab-site discovery pass first. **Brandeis is done** (2026-11-02): 133 labs, all with an email (unchanged), 48 with a known size (up from 0), 21 small. Many Brandeis PIs appear under both Biology and Neuroscience, so the same lab is sized in both files. **Boston College is done** (2026-11-02): 203 labs, 198 with an email (up from 179), 1 with a known size (BC's breadth pass recorded no lab websites), 3 reclassified (two chemistry faculty filed under the department's In Memoriam folder, one parsing artifact named "Staff"). **Tufts is done** (2026-11-02): 465 labs, 415 with an email (up from 92), 3 with a known size (unchanged: only 2 Tufts labs have a recorded lab website, both centers; Tufts sizes need a lab-site discovery pass first). **Northeastern is done** (2026-11-02): 408 labs, 105 with an email (up from 34; Bouvé profiles only show email once rendered, College of Science "lab details" pages never do), 137 with a known size (up from 133), 134 small. **BU is done** (2026-11-02): 1,600 labs, 698 with an email (up from 10; BU profile pages almost all show one), 57 with a known size (up from 0), 38 small. One PI name corrected from the lab's own site (Herriges). **Harvard is done**: 934 labs, 529 with an email (up from ~470), 182 with a known size (up from near-zero), 4 reclassified. New gotchas found: `labs.dana-farber.org`-hosted lab sites are SPA-routed and broken for direct fetches on every sub-path (9+ labs affected, platform-wide); `hsph.harvard.edu/profile/*` pages never show an email (confirmed on 160+ profiles, a genuine absence); some sites (Wyss) only reveal email when rendered with Playwright. See CLAUDE.md's Known gotchas for details.

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
| 54 Boston University `targets.csv` rows (Chobanian & Avedisian SOM, CAS, College of Engineering, SPH, University-wide centers) | 1,602 | 95 | 59 | 15 | 1,431 (+2 non-research entries) |
| 37 Northeastern `targets.csv` rows (College of Science, College of Engineering, Bouvé, university-wide institutes) | 409 | 140 | 7 | 2 | 259 (+1 non-research entry) |
| 36 Tufts `targets.csv` rows (CAS, School of Engineering, School of Medicine, Friedman School, Cummings Vet School) | 494 | 68 | 14 | 4 | 408 |
| 12 Boston College `targets.csv` rows (all CAS science departments, ISR, Schiller, Weston Observatory, TIMSS&PIRLS) | 206 | 21 | 11 | 1 | 173 |
| 12 Brandeis `targets.csv` rows | 133 | 0 | 0 | 0 | 133 |
| 13 UMass Boston `targets.csv` rows | 191 | 37 | 12 | 0 | 142 |
| 23 Broad/Forsyth/Dana-Farber/hospital `targets.csv` rows | 459 | 0 | 0 | 0 | 459 |

Harvard Chemistry, Harvard MCB and MIT Chemistry now have a PI email for every lab (from each department's own directory/profile pages); Ragon's are mostly Cloudflare-obfuscated on the institute's lab pages, so only 5 of 28 are confirmed (see `notes` for unverified decoded guesses). Whitehead's Gerald Fink is listed under `non_lab_people` (retired, no active group) rather than as a lab. The Harvard and MIT rows are breadth passes from each site's own directory — HMS departments have especially strong coverage (most labs have both a PI email and lab site, via a reusable parser for HMS's shared Drupal people-directory template, `scripts/parse_hms_people.py`) — but for department-wide directories, member counts and join info are a later per-PI pass. The ~35 single-lab/single-group MIT targets (every Media Lab group, every DUSP small lab, AgeLab, Deshpande, d-Lab, Sea Grant, and similar) got the full `to-read.txt`-style depth pass instead, since each was just one site to read anyway — most of those already have a member count and join page. Cross-cutting hubs (Harvard's CMSA/HDSI/Salata/MRSEC/SEAS-sub-areas; MIT's CBMM, CEHS, SCSB, and several Sloan/interdepartmental centers) list PIs who are already recorded under their home department's source file, so those were deliberately recorded thin (an org-level entry, a cross-reference note, or just the hub's own core staff) rather than duplicated — see each file's `notes`.

Remaining "unknown" sizes are each explained in that lab's `notes`. The big one on the Harvard side: an Akamai "Access Denied" block first seen on `arp.harvard.edu` turned out to hit a much wider, and apparently shifting, set of `harvard.edu` subdomains from this network — including some official department sites that worked in earlier sessions (`chemistry.harvard.edu` itself now fails) and all of `hsdm.harvard.edu`. HMS (`*.hms.harvard.edu`), HSPH (`hsph.harvard.edu`), and most of SEAS/MRSEC were *not* affected. On the MIT side, a cluster of sites use JS-filterable or infinite-scroll directories that didn't fully render even with Playwright (`energy.mit.edu`/MITEI, `nse.mit.edu`, `psfc.mit.edu`, `space.mit.edu`/Kavli, `ki.mit.edu`/Koch Institute, `lids.mit.edu`); `rle.mit.edu/people` and `lfe.mit.edu` are robots.txt-blocked; `smart.mit.edu` is unreachable (known redirect loop). The Smithsonian Center for Astrophysics' people page has the same JS "Load More" issue. `wi.mit.edu`-hosted Whitehead lab sites that return a robot-challenge screen, dead/placeholder pages, and a couple of JS roster carousels whose roles couldn't be mapped to names account for the rest. Rowland Fellows run independent groups of one to three people; their counts come from the institute directory and may undercount.

BU's department directories mostly don't show a PI email on the listing page itself (would need an individual profile-page visit, a later pass), which is why the BU row's `with_email` count is low — this isn't a site-blocking problem, just a template property. BU's own `scripts/parse_bu_people.py` and `scripts/build_bu_source.py` handle its shared "Name, degree → profile page" directory template (BU College of Engineering: BME/ECE/ME/MSE/SE each have genuinely department-filtered directories, re-verified after an initial pass wrongly assumed they were unfiltered and under-covered ME/MSE — see CLAUDE.md). A handful of BU targets (Cancer Center, CBR, CSN, Evans Center, Hariri Institute and its AIR initiative, Dept. of Medicine, Pathology) are `partial`: cross-cutting hubs recorded thin, umbrella departments whose real per-Section pages weren't found, or pages that rendered empty/navigation-only.

Northeastern University (37 targets: College of Science, College of Engineering, Bouvé College of Health Sciences, University-wide institutes) is also now attempted. College of Science's own people-search tool is broken (a client-side JS search that never renders any names); instead its labs came from `cos.northeastern.edu/research/faculty-labs-research/`, a 14-page listing of every named PI-led lab with a research summary and a "Lab details" page giving the PI, an external lab website, and often a small member roster — none of them have a PI email (not shown on these pages), and `northeastern-math` ended up with 0 labs (its research-group pages name no individual faculty). College of Engineering's shared `coe.northeastern.edu/faculty-staff-directory/` times out even with Playwright — bioe/cee/che/ece/mie/seis are all `partial` for this reason (and `northeastern-robotics` has the same JS-app problem on its own pages); the rest of Engineering (IFM, INSI, NanoSI) and most of Bouvé and the university-wide institutes (Cyber, ICBH, NetSI, QMSI, SSEHRI, and Bouvé's Applied Psych/CDD/CSD/Nursing/Pharm Sci/PT/Public Health) came through cleanly via each one's own dedicated people page, several with a reusable parser (`scripts/parse_bouve_people.py` for Bouvé's shared directory template). `northeastern-gri` is unreachable from this network entirely; `northeastern-kostas`/`northeastern-roux` are contract-research/applied-education institutes with no public PI roster.

Tufts (36 targets, all that are priority 1) came through cleanly: department breadth passes (Biology 34, Math 36, Physics 28, PHCM 50, DMCB 24, and more) and a properly-bucketed School of Engineering directory — targets.csv gives each engineering department (BME/CBE/CEE/CS/ECE/ME) a different `field_department_tid` filter param that turns out NOT to filter (confirmed byte-identical across two tid values), so rather than repeat BU's earlier mistake, one full 8-page/374-person crawl was bucketed by each person's own department tag. A few cross-cutting centers (Allen Discovery Center, CellAG, ICDO) were recorded thin since their PIs are already captured elsewhere; `tufts-ai` and `tufts-food-is-medicine`'s pages are effectively blank/under-construction, `tufts-terc` 404s, and `tufts-ctsi` only yielded two leadership names from a large institute.

Boston College (12 targets) used a new shared-template parser, `scripts/parse_bc_people.py` + `scripts/build_bc_source.py` — BC's department pages are structurally inconsistent (some repeat a section header before every sub-list, others cluster headers once at the top), so classification is title-based (regex for "Professor" vs. emeritus/visiting/adjunct/postdoc/staff) rather than section-based. `bc-timss-pirls` (a large educational-assessment center) only got its Executive Director; the rest is `done`.

**Brandeis** initially blocked this project's identifying User-Agent entirely (403 on every page, confirmed UA-based — a standard browser UA got 200 OK on the same pages). Raised with the project owner, who decided to use a generic browser User-Agent for `brandeis.edu` specifically (`scripts/fetch.py`'s `UA_OVERRIDE_HOSTS`, every other host keeps the honest project UA). All 12 targets then came through cleanly via a new shared-template parser, `scripts/parse_brandeis_people.py` (133 labs). Cross-cutting centers (MRSEC, Rosenstiel, Swartz, Volen) recorded thin since their PIs are already in the department files.

UMass Boston (13 targets) and Broad/Forsyth/Dana-Farber/the remaining hospitals (23 targets) are also attempted. Dana-Farber's institute-wide "Our Researchers" page is a broken JS search, but its curated "Lab Websites" list (`dana-farber-labs`, 130 labs) and 3 of its department pages came through cleanly with external lab-site links. Four hospital targets (`bwh-research`, `mgh-lab-search`, `mgh-research-institute`, `meei-research`) all route to the *same* Mass General Brigham-wide institutes/centers search tool — confirmed it holds 555 labs across the whole MGB system (JS-only, Playwright-required, no hospital-level filter found) but wasn't crawled this round; that's a high-value target for a future pass. `bch-research`'s own researcher search and Broad Institute's `/people` page are both broken JS widgets with no server-rendered fallback found.

`data/targets.csv`: **all 392 priority-1 rows have now been attempted** (296 `done`, 96 `partial`, 0 `todo`). Broad/Wyss/Koch/McGovern/Picower/Kempner are all covered. Remaining `partial` targets and their reasons are documented in each source file's `notes` and in CLAUDE.md's Known gotchas. Next: priority 2 (policy centers, business, law, education, design) and priority 3 (small think tanks, advocacy groups, humanities) — 246 rows, untouched.

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

## H-1B sponsorship columns

`data/labs.csv` and `data/labs.json` carry 13 extra columns per lab: `legal_entity_name`, `entity_type`, `cap_exempt_likely`, `sponsorship_tier`, `entry_level_roles_sponsored`, `senior_roles_sponsored`, `new_employment_filings_3yr`, `median_entry_wage`, `policy_summary`, `policy_url`, `evidence_as_of`, `confidence`, `sponsorship_notes`.

They say which legal employer a lab most likely hires through and what public records show about the positions that employer sponsors for H-1B. They are evidence labels, not promises, and not legal advice. Read `sponsorship_research/summary.md` first; it gives the tiers, the limits and how to rerun the pipeline.

The columns come from `sponsorship_research/lab_sponsorship.csv`, which `scripts/build.py` merges in by lab id. Delete that file and rebuild to drop them.
