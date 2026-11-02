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
4. If the site clearly isn't an independent research group run by this PI
   (it's someone else's lab, a department/center page, a clinical practice),
   set `"kind": "faculty-no-lab"` only when that is unambiguous, and say why.

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

Leave a field out or null when not shown. `note` is always present.
