#!/usr/bin/env python3
"""find_leads.py - the lead-discovery engine.

Searches Google (via SerpAPI) for LinkedIn posts where emerging fund managers
publicly signal they are raising a fund, identifies the post AUTHOR as a
potential contact, scores and ranks them, and writes a ranked contact list.

It searches Google's index only - it never opens or scrapes linkedin.com - so
there is no LinkedIn Terms-of-Service or account-ban risk.

Usage:
    python find_leads.py --dry-run                  # print queries, 0 API calls
    python find_leads.py                            # demo run (~6 searches)
    python find_leads.py --full --max-searches 60   # the full sweep
"""

import argparse
import csv
import os
import re
import sys
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SERPAPI_URL = "https://serpapi.com/search"
SITE_PREFIX = "site:linkedin.com/posts "


def load_env(path):
    """Minimal .env loader - avoids a python-dotenv dependency."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


def load_config():
    with open(os.path.join(HERE, "queries.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def serpapi_search(query, api_key):
    """One SerpAPI call. Returns the list of organic results."""
    import requests  # imported lazily so --dry-run needs no network library

    resp = requests.get(
        SERPAPI_URL,
        params={"engine": "google", "q": query, "api_key": api_key, "num": 10},
        timeout=30,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("organic_results", [])


# A trailing slug token that is LinkedIn's profile ID (alphanumeric, has a
# digit, 6+ chars) — e.g. "a013a34" in "scott-farden-a013a34".
ID_TOKEN = re.compile(r"^(?=.*\d)[0-9a-z]{6,}$", re.I)

# A slug that looks like an organisation, not a person.
ORG_SUFFIX = re.compile(
    r"(ventures?|capital|partners?|equity|advisors?|management|"
    r"holdings?|group|news|media|fund)$",
    re.I,
)


def clean_name_from_slug(slug):
    """Turn a LinkedIn slug into a display name, dropping the trailing ID."""
    tokens = [t for t in slug.split("-") if t]
    if len(tokens) > 1 and ID_TOKEN.match(tokens[-1]):
        tokens = tokens[:-1]
    return " ".join(t.capitalize() for t in tokens) or slug


def parse_post(url, title):
    """Extract (slug, name, profile_url, is_company) from a post result.

    Returns None if the URL is not a /posts/ URL.
    """
    m = re.search(r"linkedin\.com/posts/([^_/?#]+)_", url)
    if not m:
        return None
    slug = m.group(1)
    # Prefer the author name from the result title when it is clearly there.
    name = None
    for sep in (" on LinkedIn", "'s Post", "'s post"):
        if title and sep in title:
            cand = title.split(sep)[0].strip()
            if cand and len(cand) <= 60:
                name = cand
            break
    if not name:
        name = clean_name_from_slug(slug)
    profile = "https://www.linkedin.com/in/" + slug
    is_company = bool(ORG_SUFFIX.search(slug.replace("-", "")))
    return slug, name, profile, is_company


def score_text(text, signal_kws, noise_kws):
    """Signal phrases add 2 each; noise phrases subtract 1 each."""
    t = text.lower()
    score = 2 * sum(1 for k in signal_kws if k in t)
    score -= sum(1 for k in noise_kws if k in t)
    return score


def write_outputs(ranked, md_path, mode, searches_used):
    """Write the ranked contact list as markdown + CSV."""
    lines = [
        "# Lead-discovery - ranked contact list",
        "",
        "_{} run - {} searches - {} unique contacts._".format(
            mode, searches_used, len(ranked)
        ),
        "",
        "These are **candidates** surfaced from public LinkedIn posts indexed by "
        "Google. Each should be confirmed as an emerging fund manager before "
        "outreach - the search snippet does not carry a reliable job title.",
        "",
        "| # | Name | Type | Profile | Signal score | Posts | Evidence (signal post) |",
        "|---|------|------|---------|--------------|-------|------------------------|",
    ]
    for i, c in enumerate(ranked, 1):
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} |".format(
                i, c["name"], "org?" if c["is_company"] else "person",
                c["profile"], c["score"], c["posts_found"], c["post"]
            )
        )
    lines.append("")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    csv_path = os.path.splitext(md_path)[0] + ".csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["rank", "name", "type", "profile", "score", "posts_found",
             "evidence_post", "snippet"]
        )
        for i, c in enumerate(ranked, 1):
            w.writerow([i, c["name"], "org?" if c["is_company"] else "person",
                        c["profile"], c["score"], c["posts_found"],
                        c["post"], c["snippet"]])


def main():
    ap = argparse.ArgumentParser(
        description="Lead-discovery engine - finds emerging fund managers raising a fund."
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="print the queries and exit - no API calls")
    ap.add_argument("--full", action="store_true",
                    help="run the full query sweep (uses more quota)")
    ap.add_argument("--max-searches", type=int, default=8,
                    help="hard cap on API calls (default 8)")
    ap.add_argument("--out", default=os.path.join(HERE, "sample-output.md"),
                    help="output markdown file")
    args = ap.parse_args()

    load_env(os.path.join(HERE, ".env"))
    cfg = load_config()

    query_set = cfg["full"] if args.full else cfg["demo"]
    queries = [SITE_PREFIX + q for q in query_set]
    signal_kws = [k.lower() for k in cfg["signal_keywords"]]
    noise_kws = [k.lower() for k in cfg["noise_keywords"]]

    mode = "FULL" if args.full else "DEMO"
    print("Lead-discovery engine - {} mode, {} queries".format(mode, len(queries)))

    if args.dry_run:
        print("\n--dry-run - queries that WOULD be searched (0 API calls):\n")
        for q in queries:
            print("  " + q)
        return 0

    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("ERROR: SERPAPI_KEY not set. Copy .env.example to .env and add your key.")
        return 1

    contacts = {}  # slug -> contact dict
    searches_used = 0

    for q in queries:
        if searches_used >= args.max_searches:
            print("\n[stopped] hit the --max-searches cap ({}).".format(args.max_searches))
            break
        print("  searching: " + q)
        try:
            results = serpapi_search(q, api_key)
        except RuntimeError as e:
            print("  SerpAPI error: {} - stopping.".format(e))
            break
        searches_used += 1
        for r in results:
            parsed = parse_post(r.get("link", ""), r.get("title", ""))
            if not parsed:
                continue
            slug, name, profile, is_company = parsed
            snippet = r.get("snippet", "")
            s = score_text(r.get("title", "") + " " + snippet, signal_kws, noise_kws)
            existing = contacts.get(slug)
            if existing is None:
                contacts[slug] = {"name": name, "profile": profile, "score": s,
                                  "post": r.get("link", ""), "snippet": snippet,
                                  "posts_found": 1, "is_company": is_company}
            else:
                existing["posts_found"] += 1
                if s > existing["score"]:
                    existing.update(score=s, post=r.get("link", ""), snippet=snippet)
        time.sleep(1)  # be gentle between calls

    # Persons rank above flagged organisations; then by score, then by
    # how many signal posts the contact appeared in.
    ranked = sorted(contacts.values(),
                    key=lambda c: (not c["is_company"], c["score"],
                                   c["posts_found"]),
                    reverse=True)
    write_outputs(ranked, args.out, mode, searches_used)

    print("\nDone. {} searches used - {} unique contacts found.".format(
        searches_used, len(ranked)))
    print("Output: {} and {}".format(args.out, os.path.splitext(args.out)[0] + ".csv"))
    print("NOTE: these are candidates - confirm each is an emerging fund "
          "manager before outreach.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
