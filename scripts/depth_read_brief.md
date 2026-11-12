# Brief for reading lab people pages (depth pass)

Used by the main session to brief subagents that read the pages fetched by
`scripts/depth_pass.py prep-sizes`. Subagents only write the results file;
they never run git or scripts/build.py.

Input: a worklist JSON (list of items with `source`, `lab_id`, `pi_name`,
`lab_website`, `people_url`, `join_url`, `home_text`, `people_text`; text
paths are relative to the repo root and already cached).

For each item:
1. Read `people_text` if present, else `home_text`. If the cached text clearly
   isn't the lab's roster (navigation-only, a department page, an SPA shell)
   and the home page links a roster you can see in the link list, fetch it
   with `.venv/bin/python scripts/fetch.py <url>` (add `--render` once if the
   plain text is empty). At most 2 extra fetches per lab.
2. Count CURRENT members including the PI. Stop at Alumni / Former / Past
   headings. Count people, not headings. If the page lists names with no
   roles, count names. If you can't tell who is current, leave it null.
3. Record only what the page shows. Never guess an email, a count or a URL.
4. If `lab_website` is a center, institute, initiative or department site
   (a hub the PI directs or belongs to), do NOT reclassify: leave the count
   null and say so in `note`. Don't use a whole center's roster as one PI's
   group size. Set `"kind": "faculty-no-lab"` (inside `fields`) only when the
   person clearly runs no research group at all, e.g. a teaching-only or
   clinical-only faculty member whose own page mentions no lab, and say why.
   Use only what the pages show, not outside knowledge.

Output: a JSON list, one object per item, written to the path you're given:

    {"source": "<item.source>", "lab_id": "<item.lab_id>",
     "fields": {"member_count": 7,
                "member_breakdown": "1 PI, 2 postdocs, 3 grad students, 1 lab manager",
                "members_page_url": "<url the count came from>",
                "join_page_url": "<url or null>",
                "join_notes": "<how to apply / whom to email, own words, or null>",
                "admin_name": null, "admin_email": null,
                "pi_email": "<only if shown on the lab site and clearly the PI's, else null>",
                "accepting_grad_students": null},
     "note": "one short sentence: where the count came from, or why it's null"}

If the item's `pi_name` is null (labs found through a search tile that
linked straight to the lab's site), also record `pi_name` and `pi_title`
when the site clearly names who runs the lab, plus `pi_email` if shown.

Leave a field out or null when not shown. `note` is always present.

## Extra rules (added 2026-11-10, after reading about 750 lab sites)

- This checkout may have no `.venv`: use `python3 scripts/fetch.py <url>` then.
  Fetch pages only with `scripts/fetch.py` (it honours robots.txt and the rate
  limit), one request at a time. If it reports a robots.txt block or a
  failure, say so in `note` and move on.
- `members_page_url` must be the address of the page the count was really read
  from: the worklist's `people_url` or `lab_website`, or a page you fetched.
  Never construct or infer an address.
- If the PI is not on the roster but the site is clearly theirs, add 1 and say
  so in `note`.
- If the roster is cut off by a "More", "See more", "Load more", "View all"
  control or a pager, follow that link (it counts toward the 2 extra fetches)
  and count the full list. If the full roster still cannot be seen, leave the
  count null and say what was visible. Never record a partial count.
- If `lab_website` is not one PI's own lab or group site (a center, institute,
  program, shared multi-PI group, project site, department page, or just the
  person's profile page), leave the count null and start `note` with `HUB:`
  followed by what the site is. Same for a lab co-led by two or more PIs.
- If the site did not load, redirects to something unrelated, or is a
  placeholder, leave the count null and start `note` with `DEAD:`.
- If a roster looks old (newest date several years back), still count it and
  say so in `note`.
- Every worklist item gets exactly one result object, with `source` and
  `lab_id` copied unchanged.

The main session then runs `scripts/merge_read_results.py`, which checks every
result against the worklist and the page cache, turns the `HUB:` / `DEAD:`
tags into plain sentences, and writes the file `depth_pass.py apply` reads.

When done, report: how many items got a count, how many were left null
(grouped by reason in a few words), and any item you were unsure about.
