# Brief for reading priority 2 and 3 targets (centers, think tanks, departments, schools)

Used by the main session to brief subagents. For these targets the "lab" is
the organization or program itself, so each target is read by eye from a few
cached pages and written up as one source file. Subagents only write their
own output files; they never run git, `scripts/build.py` or
`scripts/check_center_sources.py`, and never edit anything under `data/` or
`scripts/`.

## Input

A worklist JSON made by `scripts/prep_targets.py`: a list of targets. Each
item is the `targets.csv` row (`id`, `name`, `category`, `parent`,
`start_url`, `collect`, `notes`, ...) plus `pages`: a list of
`{role, url, status, text, found_by}` where `text` is a path, relative to the
repo root, of the page's cached text (null if the page could not be fetched).
The cached text ends with two reference lists: the page's `mailto:` links and
its other links (`'label' -> url`).

Roles: `start` (home page), `people` (staff / team / faculty page), `about`,
`careers` (jobs / internships / fellowships page), `list` (a page of centers
or labs named in the target's notes).

If a page you need was not gathered (for example the people link found was
the wrong one, or the roster is on a second page), you may fetch up to 3 more
pages per target with `python3 scripts/fetch.py <url>` from the repo root (add
`--render` once if the text comes back empty). Fetch only addresses that a
cached page links to. Never use WebFetch, curl or a search engine. If
`fetch.py` reports a robots.txt block or a failure, say so in `notes` and move
on.

## Output

One JSON file per target, written to `<out-dir>/<target-id>.json`:

    {"id": "<target id>",
     "listing_urls": ["<every page you actually read for this target>"],
     "labs": [ { ...entry... } ],
     "non_lab_people": [],
     "notes": "<what could not be read and why; anything the next reader should know>"}

Every entry in `labs` has ALL of these keys (null when the pages do not show it):

`id`, `kind` (always `"research-lab"`), `lab_name`, `pi_name`, `pi_title`,
`pi_email`, `accepting_grad_students` (null unless a page states it),
`lab_website`, `location`, `phone`, `admin_name`, `admin_email`,
`research_summary` (one sentence, your own words), `member_count`,
`member_breakdown`, `members_page_url`, `join_page_url`, `join_notes`,
`profile_url`, `notes`.

Entry `id` is `<target-id>-<lead-first-last>` in lower kebab-case
(`bc-chrij-daniel-kanstroom`). When no lead is shown use `<target-id>-org`;
for a named lab or program inside the target with no lead shown use
`<target-id>-<short-lab-name>`.

## What to record, by `category`

### `research-center`, `university-policy-center`, `policy-think-tank`, `ai-research`

Exactly one entry for the organization itself:

- `lab_name`: the organization's name as its site gives it.
- `pi_name`, `pi_title`: the person who leads it, as shown (faculty director,
  director, executive director, president). Put the role in `pi_title`. If
  two people share the lead, record the first named and name the other in
  `notes`.
- `pi_email`: only if a page shows an address that is clearly that person's.
- `admin_name` / `admin_email`: the general contact the site gives
  (`info@...`, a program coordinator). A shared inbox goes in `admin_email`,
  never in `pi_email`.
- `lab_website`: the target's `start_url`.
- `location`, `phone`: as shown.
- `member_count`: the number of CURRENT core people on the people page,
  including the lead: directors, staff, resident researchers and fellows,
  postdocs, research assistants. Leave OUT advisory boards, affiliated or
  associated faculty whose home is another unit, visiting or non-resident
  fellows, student fellows listed as a cohort, alumni and former staff. Count
  only when the page makes the current core group clear; otherwise null, and
  say in `notes` what the page lists. Never record a partial count (a roster
  cut off by "Load more" or a pager must be followed or left null).
- `member_breakdown`: for example "1 director, 2 associate directors, 4 staff, 3 research fellows".
- `members_page_url`: the page the count came from.
- `join_page_url`: the careers / jobs / research-assistant / internship /
  fellowship page you read, if the site has one. `join_notes`: in your own
  words, what it says about how to apply and whom to contact (and, if it
  says so, that there are no openings now).
- `profile_url`: the lead's own profile page, if a page links it.

Add further entries only for distinct labs, programs or projects INSIDE the
organization that its pages present with their own name and their own lead
or their own website (for example a "Growth Lab" inside a center). Record
what the pages show for each; do not go and read their sites. If there are
more than about ten, record the ten the pages present first and name the
rest in the file's `notes`.

### `university-department`

One entry for the department as an organization: `lab_name` the department's
name, `pi_name` the chair or head if shown (role in `pi_title`),
`admin_email` the department's general address, `lab_website` the
`start_url`, `join_page_url` / `join_notes` for any research-assistant,
pre-doctoral or jobs page the site has. `member_count` stays null (a
department is not a lab; say so in `notes`).

Then one entry for each lab, center or research group that the department's
own pages list as run by its faculty (look for "Labs", "Centers", "Research
groups", "Research" in the menus and on the cached pages): `lab_name`, the
lead if shown, `lab_website` as linked, a one-sentence summary if the page
gives a blurb. Do NOT add an entry for every faculty member.

### `school`

A school is an umbrella; its departments are separate targets. Record no
entry for the school itself. Read the `list` page(s) (the school's page of
centers, institutes, labs or research groups) and add one entry for each
lab, center or group listed there: `lab_name`, `lab_website` (the link the
list gives), `pi_name` / `pi_title` only if the list shows a lead,
`research_summary` only if the list gives a blurb, everything else null.
`notes` on each entry: "Listed on <school>'s <page name> page; not read
further." If the list is long, record them all (one page of links is quick);
if it runs over several pages, follow the pager within your fetch budget and
say in the file's `notes` how far you got. If there is no such list page, or
it could not be read, write `"labs": []` and say why in `notes`.

## Rules that matter most

- Record only what a page shows. Never guess a name, an email, a count or an
  address. Unknown is null; say why in `notes`.
- Every address you write (`lab_website`, `members_page_url`,
  `join_page_url`, `profile_url`, `listing_urls`) must be one you read or one
  a cached page links to, copied exactly. Never construct an address.
- Every email you write must appear on a page you read.
- Use straight, plain sentences in `research_summary`, `join_notes` and
  `notes`. Do not copy sentences from the site.
- One output file per worklist item, even when nothing could be read (then
  `"labs": []` with the reason in `notes`).

When done, report: how many targets you wrote, how many entries in total, how
many got a member count, how many have a join page, which targets you could
not read and why, and anything you were unsure about (target id + one line).
