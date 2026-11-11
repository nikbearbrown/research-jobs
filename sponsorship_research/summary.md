# Sponsorship research: summary

## Executive summary

**What this is.** Each lab in `data/labs.csv` now carries 13 columns saying which legal employer it most likely hires through, whether that employer is exempt from the H-1B lottery, and what public evidence says about the kinds of positions it sponsors. Written 2026-11-10.

**The short answer.** Of 6380 labs, 5904 are assigned to an employer and 476 are left unassigned because the row does not settle who the employer is. Almost every employer here is a cap-exempt type. The ones with repeated entry-level filings (Tier A) are mostly the hospitals and institutes, led by Dana-Farber; the big universities with a written policy (Harvard, MIT, Boston University) sponsor academic and senior research appointments only (Tier B).

**How far to trust it.** The tiers are evidence labels, not promises. A Tier A employer has filed for entry-level roles before; that does not mean a given lab will. A Tier C employer may sponsor freely and simply file little. Read the limits section before using a tier to advise anyone.

## Tier counts

| Tier | Meaning | Legal employers | Labs |
|---|---|---|---|
| A | Sponsors entry-level staff (policy allows it, or repeated entry-level filings) | 7 | 858 |
| B | Academic or senior research appointments only | 9 | 4720 |
| C | Cap-exempt type, too little evidence to tell | 11 | 326 |
| D | For-profit, cap-subject: the lottery applies | 1 | 0 |
| unknown | Employer type not established | 1 | 0 |
| | Hiring entity not settled (employer fields blank) | | 476 |

The Ragon Institute is counted under Mass General's legal entity. Employers with zero labs are ones that appear only as a second affiliation on ambiguous labs.

**Tier A line.** At least 10 new-employment positions in entry-level role families (technician, research assistant or associate, computational, software), at prevailing-wage Level I or II, with a confidently classified title, seen in at least 2 fiscal years. **Tier B line.** At least 20 new-employment positions, at least 60% of them postdoc, fellow, scientist or faculty titles, and no more than 15% in entry-level families. A written policy overrides both.

## Employers by entry-level sponsorship evidence

New-employment positions are the ones relevant to someone coming off OPT. Period: decisions 2023-10-02 to 2026-06-30.

| Employer | Tier | Entry-level new positions, Level I-II | Fiscal years | All new positions | Median entry wage | Labs assigned | Entry-level roles |
|---|---|---|---|---|---|---|---|
| Dana-Farber Cancer Institute, Inc. | A | 125 | 3 | 548 | $48,000 | 187 | technician: frequent (142); research assistant/associate: occasional (4) [most of these titles may not be entry-level here]; computational/data: frequent (47); software/ML: occasional (6) [most of these titles may not be entry-level here] |
| The General Hospital Corporation | A | 47 | 3 | 377 | $65,520 | 331 | technician: frequent (18); research assistant/associate: occasional (3); computational/data: frequent (33); software/ML: occasional (5) [most of these titles may not be entry-level here] |
| The Broad Institute, Inc. | A | 35 | 3 | 94 | $82,400 | 0 | technician: none seen; research assistant/associate: occasional (7); computational/data: frequent (29); software/ML: occasional (7) [most of these titles may not be entry-level here] |
| The Brigham and Women's Hospital, Inc. | A | 27 | 3 | 256 | $72,946 | 134 | technician: occasional (4) [most of these titles may not be entry-level here]; research assistant/associate: frequent (12); computational/data: frequent (18); software/ML: occasional (5) |
| Beth Israel Deaconess Medical Center, Inc. | A | 17 | 3 | 146 | $58,843 | 75 | technician: none seen; research assistant/associate: frequent (11); computational/data: frequent (15); software/ML: none seen |
| The Children's Hospital Corporation | A | 16 | 3 | 264 | $81,500 | 0 | technician: occasional (7); research assistant/associate: none seen; computational/data: frequent (12); software/ML: occasional (7) |
| Whitehead Institute for Biomedical Research | C | 9 | 3 | 22 | $47,500 | 17 | technician: occasional (9); research assistant/associate: none seen; computational/data: none seen; software/ML: none seen |
| Boston Medical Center Corporation | C | 8 | 3 | 61 | $82,706 | 0 | technician: none seen; research assistant/associate: none seen; computational/data: frequent (12) [most of these titles may not be entry-level here]; software/ML: none seen [most of these titles may not be entry-level here] |
| Tufts Medical Center, Inc. | C | 8 | 3 | 20 | $79,393 | 0 | technician: none seen; research assistant/associate: occasional (7); computational/data: occasional (5); software/ML: none seen |
| Trustees of Boston University | B | 7 | 3 | 136 | $82,014 | 1575 | technician: none seen; research assistant/associate: none seen; computational/data: occasional (7); software/ML: occasional (2) [most of these titles may not be entry-level here] |
| Trustees of Boston College | C | 7 | 2 | 64 | $101,000 | 203 | technician: none seen; research assistant/associate: occasional (5) [most of these titles may not be entry-level here]; computational/data: occasional (2); software/ML: occasional (9) [most of these titles may not be entry-level here] |
| Massachusetts Eye and Ear Infirmary | B | 4 | 2 | 45 | $73,091 | 11 | technician: occasional (1) [most of these titles may not be entry-level here]; research assistant/associate: occasional (1); computational/data: occasional (3); software/ML: none seen [most of these titles may not be entry-level here] |
| Hebrew Rehabilitation Center | C | 3 | 1 | 25 | $86,424 | 33 | technician: none seen; research assistant/associate: none seen; computational/data: occasional (3); software/ML: none seen |
| Brandeis University | A | 2 | 1 | 24 | $81,557 | 131 | technician: none seen; research assistant/associate: none seen [most of these titles may not be entry-level here]; computational/data: occasional (1); software/ML: occasional (1) |
| Howard Hughes Medical Institute | B | 2 | 1 | 25 | $94,000 | 0 | technician: none seen; research assistant/associate: occasional (2) [most of these titles may not be entry-level here]; computational/data: occasional (1); software/ML: none seen |
| Northeastern University | B | 2 | 1 | 53 | $105,234 | 408 | technician: none seen; research assistant/associate: occasional (1) [most of these titles may not be entry-level here]; computational/data: occasional (2) [most of these titles may not be entry-level here]; software/ML: none seen [most of these titles may not be entry-level here] |
| Trustees of Tufts College | B | 2 | 2 | 79 | $70,199 | 464 | technician: occasional (2); research assistant/associate: occasional (3) [most of these titles may not be entry-level here]; computational/data: occasional (1); software/ML: none seen |
| The Spaulding Rehabilitation Hospital Corporation | C | 2 | 1 | 11 | $55,569 | 4 | technician: occasional (2); research assistant/associate: none seen; computational/data: none seen; software/ML: none seen |
| President and Fellows of Harvard College | B | 1 | 1 | 294 | $103,000 | 759 | technician: none seen; research assistant/associate: frequent (53) [most of these titles may not be entry-level here]; computational/data: none seen; software/ML: occasional (1) |
| Massachusetts Institute of Technology | B | 0 | 0 | 206 |  | 1312 | technician: none seen; research assistant/associate: occasional (4) [most of these titles may not be entry-level here]; computational/data: none seen; software/ML: none seen |
| The McLean Hospital Corporation | B | 0 | 0 | 23 |  | 0 | technician: none seen; research assistant/associate: occasional (2); computational/data: none seen; software/ML: none seen |
| University of Massachusetts (Boston campus) | B | 0 | 0 | 33 |  | 191 | technician: none seen; research assistant/associate: none seen; computational/data: none seen; software/ML: none seen |
| Joslin Diabetes Center, Inc. | C | 0 | 0 | 10 |  | 44 | technician: none seen; research assistant/associate: none seen; computational/data: none seen; software/ML: none seen |
| Mass General Brigham Incorporated | C | 0 | 0 | 111 |  | 0 | technician: none seen; research assistant/associate: none seen [most of these titles may not be entry-level here]; computational/data: none seen; software/ML: none seen [most of these titles may not be entry-level here] |
| The Forsyth Institute | C | 0 | 0 | 3 |  | 25 | technician: none seen; research assistant/associate: none seen; computational/data: none seen; software/ML: none seen |

## Where written policy and filings disagree

- **Brandeis University.** Written policy allows staff positions but filings show only 2 entry-level new-employment positions at Level I-II (of 24 new-employment positions in all). Policy decides: Tier A.

## What the evidence says, employer by employer

**Dana-Farber: confirmed, clearly first.** 125 entry-level new-employment positions at Level I or II across all three fiscal years: Research Technician (76), Statistician and Computational Biologist (43), software (5). Its written policy could not be read, so the tier rests on filings alone.

**The Broad: confirmed as Tier A, but fourth, not near the top.** 35 positions, mostly computational (Computational Associate II, Computational Scientist). Bench Research Associate filings are few: 6 counted positions in the period. The Broad's own careers page says only that these roles accept OPT; it does not mention H-1B. The Broad is not listed as an institution in the lab list, so no lab is assigned to it; it appears as a candidate on 18 ambiguous labs.

**Mass General (47) and Brigham and Women's (27) rank with or above the Broad.** Beth Israel Deaconess (17) and Boston Children's (16) also clear the line in all three years. Boston Children's, like the Broad, has no labs assigned because it is not a listed institution.

**Harvard and MIT: as expected, Tier B on written policy, and the filings agree.** Harvard's 104 certified Research Associate filings are academic appointments, not entry-level staff. MIT has no entry-level filings at all.

**Boston University: Tier B on written policy.** Its filings agree (7 entry-level positions, all computational or IT).

**Tufts University: Tier B on filings.** Its policy allows "certain research staff", which is not enough to decide, and its filings show 2 entry-level positions against 57 faculty, postdoctoral and scientist ones.

**Brandeis: Tier A on written policy, against thin filings.** The policy names Research Technician, Research Associate and Research Specialist as staff roles that may be sponsored, and adds that Brandeis expects OPT and STEM OPT to be used up first. Filings show only 2 entry-level positions. The policy decides, as instructed, but this is the least proven Tier A.

**Whitehead: Tier C, one position short of Tier A.** 9 Technical Assistant positions at about $47,500, in every one of the three years. Worth a direct question to the institute.

**Northeastern, UMass Boston, Mass Eye and Ear: Tier B on filings alone.** No readable policy; filings are almost all faculty and postdoctoral.

**Boston College, Joslin, Hebrew SeniorLife, Forsyth, Spaulding: Tier C.** Too few filings to say anything.

## Things that are not what the column names suggest

- **`new_employment_filings_3yr` counts positions, over two and three-quarter years.** It is the sum of new-employment positions on certified LCAs with decisions from 2023-10-02 to 2026-06-30.
- **`median_entry_wage` is weighted by new-employment positions** and covers only entry-level families at Level I or II. It is blank where an employer has none.
- **`sponsorship_notes`, not `notes`.** The lab list already had a `notes` column, so the new one was renamed to avoid overwriting it.
- **`confidence` is about the lab-to-employer link,** not about the tier. High means the lab is listed under one institution and nothing in its row points elsewhere.
- **The ten `faculty-no-lab` entries in `labs.json`** are not in `labs.csv` and carry empty sponsorship fields.

## Labs left unassigned

476 labs have blank employer fields and `confidence` = low, with the candidate employers listed in `sponsorship_notes`. The three largest groups:

- **161 labs listed under "Mass General Brigham"** with nothing in the row saying which hospital. All candidates are cap-exempt; Mass General and the Brigham are both Tier A.
- **About 150 Harvard-listed labs whose row names a hospital** (Dana-Farber 42, Boston Children's 34, the Brigham 32, Mass General 28, Beth Israel Deaconess 11). This matters most: Harvard is Tier B and those hospitals are Tier A, so the answer changes the advice.
- **36 labs led by HHMI Investigators,** where staff may be on the host's payroll or HHMI's.

## Limits of this evidence

- **J-1 and O-1 hires are invisible.** An employer that puts research staff on J-1 files no LCA for them, so low counts can understate real hiring of international staff, and say nothing about H-1B willingness.
- **An LCA is not a hire.** It is a filing made before a petition. One LCA can cover several positions, and some certified LCAs are never used.
- **Absence is not refusal.** No filings in a role family does not prove an employer will not sponsor that role.
- **Written policies change,** and most of the hospitals keep theirs behind a login. Only 5 of 28 employers had a policy that could be read in full.
- **A pending federal rule may change cap exemption.** The H-1B reform rule under review (RIN 1615-AD00) is reported to revisit the definitions of affiliated nonprofits and research organizations. `cap_exempt_likely` reflects the rules as they stood on 2026-11-10.
- **Primary worksite only.** The filter uses the primary worksite state in the main LCA file. Positions listed only in DOL's separate worksites file are not counted.
- **Titles are classified by keyword and occupation code.** 211 certified filings fell into 'administrative / other' and 616 carry a caution flag; both are listed in `unclassified_titles.csv`.
- **The lab-to-employer step is the weakest link.** A lab is assigned to its listed institution unless the row names another employer. Many rows have no PI email, so some hospital-based labs are still counted under Harvard or Boston University.

## How to rerun, here or for another city

```bash
python3 scripts/sponsorship_step1_entities.py                 # lab list -> entities, ambiguous labs, lab map
python3 scripts/sponsorship_step2_lca.py extract --state MA   # slow; once per new LCA file
python3 scripts/sponsorship_step2_lca.py profile --state MA
python3 scripts/sponsorship_step3_policies.py                 # merge policy rows
python3 scripts/sponsorship_step4_tiers.py                    # tiers, lab_sponsorship.csv, this file
python3 scripts/build.py                                      # merges the columns into data/labs.csv and labs.json
```

- **New LCA quarter:** download the file in a browser from the DOL performance-data page (the site refuses scripted requests), put it in `cache/dol-lca/`, and run from the `extract` line down.
- **Another state:** change `--state`. The extract keeps every H-1B row for that state, so nothing else in step 2's first stage changes.
- **Another lab list:** pass `--labs` to step 1 with the same column names, then add the new institutions to `ENTITIES`, `DEFAULT_ENTITY` and the signal tables in step 1, and to `ENTITY_MATCH` in step 2. Those three tables are the only Boston-specific code.
- **Policies** are read by a person or an agent, never inferred: add rows to `policy_parts/`, add a line to `policy_reading.csv`, and rerun steps 3 and 4.
- **Removing the columns:** delete `sponsorship_research/lab_sponsorship.csv` and run `scripts/build.py`. The 25 original columns are produced exactly as before.
