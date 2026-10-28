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

## Coverage (2026-10-27)

165 labs so far, 87 with a PI email.

| Source | Labs | Small (≤10) | Medium (11–20) | Large (>20) | Size unknown |
|---|---|---|---|---|---|
| Harvard Chemistry and Chemical Biology (faculty + lecturers) | 25 + 1 core facility | 5 | 2 | 5 | 13 |
| Harvard Molecular and Cellular Biology | 36 | 18 | 10 | 6 | 2 |
| MIT Chemistry (faculty list only; profiles not yet read) | 42 | 0 | 0 | 0 | 42 |
| Whitehead Institute (Members, Fellows, AI Fellow) | 25 | 0 | 0 | 0 | 25 |
| Rowland Institute (Fellows) | 8 | 8 | 0 | 0 | 0 |
| Ragon Institute | 28 | 9 | 7 | 4 | 8 |

Harvard MCB sizes come from the department directory filtered by lab (it includes shared lab administrators), not the labs' own sites.
Rowland Fellows run independent groups of one to three people; their counts come from the institute directory and may undercount. Most "unknown" sizes are labs whose own websites could not be read yet (see `notes` on each lab).

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
