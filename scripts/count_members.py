#!/usr/bin/env python3
"""Heuristic assistant for counting current lab members on a people/team page.

This does NOT write to any source file. It prints a best-guess breakdown so
a human (or agent) can spot-check it against the rendered page before typing
member_count / member_breakdown into a data/sources/*.json file.

Usage: python3 scripts/count_members.py <url> [--render]
"""
import re
import sys

from fetch import fetch

STOP_HEADINGS = re.compile(r"\b(alumni|former|past members|lab history|in memoriam)\b", re.I)
START_HEADINGS = re.compile(r"\b(current members|our team|team members|members|people|group members|lab members)\b", re.I)
ROLE_WORDS = re.compile(
    r"\b(postdoc|post-doc|graduate student|grad student|ph\.?d\. student|phd student|"
    r"undergrad|research scientist|research assistant|research associate|lab manager|"
    r"lab administrator|technician|staff scientist|visiting scholar|research fellow|"
    r"program manager|project manager)\b",
    re.I,
)


def guess_breakdown(text):
    lines = text.splitlines()
    counts = {}
    total = 0
    in_current = True  # default on until a "current members" heading narrows it
    started = False
    for line in lines:
        if STOP_HEADINGS.search(line):
            break
        if START_HEADINGS.search(line) and len(line) < 60:
            started = True
            continue
        m = ROLE_WORDS.search(line)
        if m:
            role = m.group(1).lower()
            counts[role] = counts.get(role, 0) + 1
            total += 1
    return total, counts, started


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    url = args[0]
    render = "--render" in args
    result = fetch(url, render=render)
    if not result["text"]:
        print(f"Could not fetch: {result['status']}", file=sys.stderr)
        sys.exit(1)
    total, counts, started_heading_seen = guess_breakdown(result["text"])
    print(f"# {url}")
    print(f"# saw a 'current members'-style heading: {started_heading_seen}")
    print(f"guessed role mentions (NOT a verified count, spot-check against the page): {total}")
    for role, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {role}")
    print("\n--- rendered text follows, read it yourself to confirm ---\n")
    print(result["text"])


if __name__ == "__main__":
    main()
