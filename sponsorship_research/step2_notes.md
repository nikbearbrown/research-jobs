# Step 2 notes: the Department of Labor filing data

## Executive summary

**What was read.** Nine H-1B LCA disclosure files from the Department of Labor: fiscal 2024 (four quarters), fiscal 2025 (four quarters) and the fiscal 2026 third-quarter file. Together they hold decisions from 2023-10-02 to 2026-06-30, which is two and three-quarter years, not three.

**What came out.** 55,444 H-1B filings with a primary worksite in Massachusetts, of which 50,042 are Certified. 5,092 certified filings belong to the employers in `entities.csv`.

**The main finding.** Dana-Farber, Mass General, the Broad, Brigham and Women's, Beth Israel Deaconess and Boston Children's all file repeatedly for entry-level roles at wage Level I or II. Harvard and MIT file almost entirely for postdocs, fellows, research scientists and faculty. That matches what was expected, with two corrections: the Broad is fourth, not near the top, and its entry-level filings are mostly computational roles, not bench roles.

**Limits.** LCAs do not capture J-1 or O-1 hires. An LCA is not a hire. No filings in a role family does not prove an employer will not sponsor it.

## How the files were obtained

`dol.gov` refuses scripted requests (HTTP 403), so the files were downloaded through a browser from <https://www.dol.gov/agencies/eta/foreign-labor/performance> on 2026-11-10 and placed in `cache/dol-lca/`, which is not committed. They total about 1 GB.

| File | Decisions from | to | Massachusetts H-1B rows |
|---|---|---|---|
| FY2024 Q1 | 2023-10-02 | 2023-12-31 | 3,497 |
| FY2024 Q2 | 2024-01-01 | 2024-03-31 | 4,921 |
| FY2024 Q3 | 2024-04-01 | 2024-06-30 | 7,892 |
| FY2024 Q4 | 2024-07-01 | 2024-09-30 | 4,058 |
| FY2025 Q1 | 2024-10-01 | 2024-12-31 | 3,697 |
| FY2025 Q2 | 2025-01-01 | 2025-03-31 | 4,635 |
| FY2025 Q3 | 2025-04-01 | 2025-06-30 | 8,705 |
| FY2025 Q4 | 2025-07-01 | 2025-09-30 | 3,978 |
| FY2026 Q3 | 2025-10-01 | 2026-06-30 | 15,201 |

The fiscal 2026 file is cumulative (October through June); the others are one quarter each. Rows are de-duplicated by case number, so the overlap does no harm. The same 98 columns were present under the same names in all nine files.

## Data issues found

- **Case status.** Certified 50,042; Certified - Withdrawn 4,138; Withdrawn 907; Denied 357. Only plain Certified rows are counted. The 4,138 certified-then-withdrawn filings are excluded, which slightly understates filing activity.
- **Harvard does not file under its corporate name.** All 452 certified filings say "Harvard University", not "President and Fellows of Harvard College". Mass General files as "General Hospital Corporation" with Mass General Brigham's Somerville head-office address. Matching on employer city would have missed both.
- **Misspelled employer names.** "Danar-Farber Cancer Institute", "Dana-Farber Cancer Instittue", "TRUSTEES OF BSOTON UNIVERSITY", "Beth Israel Deaconness". These are accepted when the employer ID matches and the name is nearly identical.
- **The employer ID is not unique for public institutions.** UMass Boston shares one state employer ID with UMass Chan Medical School (242 filings), UMass Amherst (135), several state universities and two district attorneys' offices. Only filings named "University of Massachusetts Boston" (58) are counted. The rest are listed in `employer_matches.csv` as "check" and are not counted.
- **Related entities kept out.** Brigham and Women's Physicians Organization, Brigham and Women's Faulkner Hospital, Harvard Medical Faculty Physicians at BIDMC, Beth Israel Lahey Health Primary Care, the Tufts Medical Center physician groups and Lawrence General Hospital resemble an entity by name and are listed as near-misses, not counted.
- **Excel residue.** Some text cells arrive wrapped as `="Research Fellow"`. The wrapper is stripped before matching.
- **One LCA can cover many positions.** Dana-Farber's 37 certified technician filings cover 142 new-employment positions. Counts of filings and counts of positions are both reported; the labels in step 4 use positions.
- **Wage level is almost always present.** Every Harvard, Broad and Mass General filing gives a Level I to IV. MIT leaves it blank on 33 filings; Dana-Farber uses a survey on 24; Boston University uses a union agreement on 15.
- **The wage-source field does not flag academic wages.** The owner's open question was whether the prevailing-wage source marks the academic (ACWIA) wage tables. It does not: nearly every filing just reports an OES level, so the field is not a cap-exempt signal.
- **Primary worksite only.** The filter uses the primary worksite state in the main file. Additional worksites are in a separate DOL file that was not downloaded.

## The Ragon Institute

No employer named Ragon files in Massachusetts. The General Hospital Corporation files for worksites at 600 Main Street and 400 Technology Square in Cambridge, which are the Ragon addresses (about 26 certified filings), including one whose worksite line reads "MGH RAGON INSTITUTE, 600 MAIN ST" and one titled "Research Fellow, MGH Ragon Institute". Together with the institute's own careers page, this supports treating Mass General as Ragon's employer of record. Step 1's confidence was raised from low to medium on this evidence.

## Role families

Titles are sorted by keyword, then by occupation code, into ten families. One family was added to the nine requested: "clinical (physician, nurse, clinical staff)", because hospitals file hundreds of clinical fellow, resident and nurse positions that would otherwise swamp "administrative / other".

Two cautions are attached to rows, not hidden:

- **Research Associate at a university.** Flagged as "usually an academic appointment, not entry-level staff". Harvard has 104 certified Research Associate filings (median wage $82,323); none is counted as entry-level evidence. At the Broad the same words mean an entry-level bench job (Research Associate II, median $63,788), and those are counted.
- **Senior wording or a Level III or IV wage** in an entry-level family is flagged and not counted as entry-level evidence.

616 certified filings carry a flag and 211 fell into "administrative / other". Both sets are in `unclassified_titles.csv`. Known weak spots: a few IT and business analysts filed under a statistics occupation code land in "computational", and "Statistician" at Dana-Farber is counted as entry-level because it is filed at Level I or II.

## Which employers file for entry-level roles

"Entry-level evidence" below means new-employment positions in the technician, research assistant or associate, computational, or software families, at Level I or II, with no caution flag.

| Employer | Entry-level evidence | Fiscal years | What the roles are | Median entry wage |
|---|---|---|---|---|
| Dana-Farber | 125 | 3 | Research Technician (76), Statistician and Computational Biologist (43), software (5) | $48,000 |
| Mass General | 47 | 3 | Data Analyst and Data Scientist (28), Research Technologist (11), software (5), Research Specialist (3) | $65,520 |
| Broad Institute | 35 | 3 | Computational Associate and Computational Scientist (25), Research Associate II (6), software (4) | $82,400 |
| Brigham and Women's | 27 | 3 | Data and biostatistics roles (15), Research Specialist and Research Assistant (8), software (4) | $72,946 |
| Beth Israel Deaconess | 17 | 3 | Biostatistician and Bioinformatician (10), Research Assistant (7) | $58,843 |
| Boston Children's | 16 | 3 | Research Technologist (6), computational (5), research software (5) | $81,500 |
| Whitehead | 9 | 3 | Technical Assistant I (9) | $47,500 |
| Boston Medical Center | 8 | 3 | | |
| Tufts Medical Center | 8 | 3 | | |
| Boston University | 7 | 3 | Statistical Programmer, software | |
| Boston College | 7 | 2 | | |
| Harvard | 1 | 1 | one Software Developer II | |
| MIT | 0 | 0 | | |

**Where the data disagrees with expectations.**

- **The Broad is real but smaller than expected.** Its entry-level filings are mainly computational. Bench Research Associate filings are few: 12 certified in the whole period, 6 counted positions.
- **Mass General and the Brigham outrank the Broad** on entry-level filings, and Beth Israel Deaconess and Boston Children's also file every year.
- **Dana-Farber is far ahead of everyone,** and its technician filings sit at a median of about $52,000.
- **Harvard and MIT are as expected.** MIT's certified filings are postdoctoral (145), research scientist and engineer (174) and faculty (54). Harvard's are postdoctoral and research fellows (207), faculty (119) and Research Associate (104).

IBM appears in the table of employers only because the MIT-IBM lab names it. Its 264 certified Massachusetts filings are the company's as a whole and say nothing about the lab.
