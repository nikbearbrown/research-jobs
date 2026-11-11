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
