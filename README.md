# Lead-Discovery Engine

Finds emerging fund managers who are publicly signalling — on LinkedIn —
that they are raising a fund, and turns them into a ranked list of
potential contacts. **No LinkedIn account, no LinkedIn API, no scraping.**

Built for capq.ai's Task 3 growth mechanism (Renn Labs Marketing
Challenge).

---

## Why this exists

Capq.ai's product is for emerging fund managers raising a fund.
The **highest-intent** lead is therefore not "a fund manager" but "a
fund manager who is **actively raising right now**." Cold outbound to a
generic list of GPs is low-yield; outbound to someone whose latest
LinkedIn post is "we just held our first close" is a different
conversation entirely.

Those people exist and signal publicly — usually on LinkedIn, in posts
about first closes, fund I/II launches, anchor LP commitments. The
problem is finding them at scale without breaking rules or paying for
the privilege:

| Path                                | Why it fails                                                  |
|-------------------------------------|---------------------------------------------------------------|
| LinkedIn Sales Navigator            | $99+/mo per seat; the right filter combination still requires manual review |
| LinkedIn official API (Marketing)   | Requires Sales Nav tier + partner approval; not built for prospecting use cases |
| Scrape linkedin.com directly        | Violates LinkedIn ToS; risks account ban; legally contested  |
| Buy a fund-manager list             | Generic, no intent signal, often outdated                     |
| Manually browse LinkedIn            | Doesn't scale past ~50 profiles                               |

This engine takes a fifth path: **search Google's public index** for
the LinkedIn posts where the signal already shows up, then extract the
post authors as contacts. Google indexes public LinkedIn posts; querying
Google is not a LinkedIn interaction.

The result: a $0, ToS-safe, repeatable way to build a fresh
intent-ranked contact list each time you run it.

---

## What you get

Two files (a Markdown table for humans, a CSV for tooling):

- `sample-output.md`
- `sample-output.csv`

Each row is one **deduped contact**, scored and ranked. Example, from a
16-query / 126-contact full run:

```
| # | Name           | Type   | Profile                                  | Score | Posts | Evidence                                                              |
|---|----------------|--------|------------------------------------------|-------|-------|-----------------------------------------------------------------------|
| 1 | Scott Farden   | person | linkedin.com/in/scott-farden-a013a34     | 6     | 1     | "Scott Farden, COO, Nonantum Capital — investment activity…"          |
| 4 | Arpon Ray      | person | linkedin.com/in/arponray                 | 6     | 1     | "We are excited to announce more than $500M…"                          |
| 7 | Max Pog        | person | linkedin.com/in/maxpog                   | 6     | 1     | "115 LPs…"                                                            |
| 19| Joseph Alalou  | person | linkedin.com/in/josephalalou             | 4     | 1     | "We've been raising our first fund and here's…"                       |
```

Score ≥4 = strong signal. **Each row is a candidate**, not a confirmed
lead — see [The output is candidates, not vetted leads](#the-output-is-candidates-not-vetted-leads)
and [`verified-leads.md`](verified-leads.md).

---

## How it works — the pipeline

```
  ┌────────────────┐
  │  queries.yml   │   precision-tuned + signal/noise word lists
  └────────┬───────┘
           │  for each query, prefix with: site:linkedin.com/posts
           ▼
  ┌────────────────┐
  │  SerpAPI ──► Google search       (1 API call per query)
  └────────┬───────┘
           │  organic_results[]: { title, snippet, link }
           ▼
  ┌────────────────┐
  │  Parse author  │   regex on the post URL → slug
  │                │   slug + title → person name + profile URL
  └────────┬───────┘
           │  ignores any result that isn't /posts/
           ▼
  ┌────────────────┐
  │  Score         │   (signal_phrase_hits × 2)  −  (noise_phrase_hits × 1)
  │                │   text scored = title + snippet, lowercased
  └────────┬───────┘
           │
           ▼
  ┌────────────────┐
  │  Dedupe        │   key = profile slug
  │                │   posts_found = count of matches per profile
  │                │   keep highest-scoring post as the "evidence"
  └────────┬───────┘
           │
           ▼
  ┌────────────────┐
  │  Rank          │   (person before flagged-org, score desc, posts_found desc)
  └────────┬───────┘
           ▼
  ranked contact list  →  sample-output.md  +  sample-output.csv
```

Runtime end-to-end on a `--full` run: ~30–60s + 1s sleep between
calls. SerpAPI free tier = 100 searches/month; one `--full` run uses
~16.

### Step 1 — Queries (`queries.yml`)

**What:** Two named query sets, plus the signal + noise word lists used
for scoring.

- `demo` — 6 queries, default for any plain run (quota-safe).
- `full` — 16 queries, used only with `--full`. Tier 1 = first-person
  announcements ("held our first close", "raising our first fund");
  tier 2/3 = identity + LP language ("emerging manager", "anchor LP").

Every query is prefixed by the code with `site:linkedin.com/posts ` so
results are scoped to public LinkedIn post pages only.

**Why precision queries instead of broad ones:** A query like
`"raising a fund"` floods Google with "how to raise a fund" guides,
webinar ads, and consultancy posts. The precision queries
(`"held our first close"`, `"first close" "emerging manager"`) catch
**first-person announcements** — the actual signal — at the cost of
recall. Recall is fine here: even 5 surfaced GPs/week is a useful
outbound shortlist.

**Why two named sets (demo / full):** the default run must be safe to
execute without thought — a careless `python find_leads.py` shouldn't
spend a quarter of your monthly quota.

### Step 2 — SerpAPI search (`serpapi_search`)

**What:** For each query, a single GET to `serpapi.com/search` with
`engine=google`, `q=<query>`, `num=10`. Returns Google's organic
results JSON. A 1-second sleep follows each call.

**Why SerpAPI, not Google directly:** Google's official Custom Search
JSON API is per-query priced and rate-limited; SerpAPI provides a free
tier (100/mo) that's enough for weekly outbound prep, and abstracts
Google's anti-scraping pushback.

**Why `num=10`:** the signal-bearing posts almost always rank in the
top 10 for these precision queries. Larger result sets dilute precision
and burn quota.

**Why the 1-second sleep:** a polite client, and well under any
plausible rate limit. Search latency dwarfs the sleep anyway.

### Step 3 — Parse author from the post URL (`parse_post`)

**What:** LinkedIn post URLs follow the pattern
`linkedin.com/posts/<slug>_<activity-id>`. Regex extracts the slug.

- Author name resolution:
  1. If the result title contains `" on LinkedIn"`, `"'s Post"`, or
     `"'s post"`, the substring before is the author's real name.
  2. Otherwise, derive the name from the slug:
     `scott-farden-a013a34` → drop the trailing alphanumeric ID token
     (regex: `^(?=.*\d)[0-9a-z]{6,}$`) → `Scott Farden`.

- Profile URL: `https://www.linkedin.com/in/<slug>`.

- `is_company` heuristic: regex on the slug for trailing words like
  `ventures`, `capital`, `partners`, `equity`, `advisors`, `management`,
  `holdings`, `group`, `news`, `media`, `fund`. If matched, the row is
  tagged `org?` and ranked **below** persons.

**Why the human is the lead, not the post:** outbound goes to a person.
The post is just the signal that the person is in-market right now.

**Why prefer the title for the name:** the slug-derived name loses
capitalization and may drop suffixes. The title carries the real name
when LinkedIn's snippet format includes it.

**Why drop the trailing ID token:** LinkedIn appends a profile-unique
ID suffix to most slugs (`-a013a34`). Without dropping it, names look
like "Scott Farden A013a34".

**Why flag organizations and demote them:** companies post too. CQ's
outbound goes to humans (GPs / IR leads), not the firm. Demoting (not
deleting) preserves the option to use them as a lookup later.

### Step 4 — Score (`score_text`)

**What:** Lowercase `title + " " + snippet`. Count substring matches
against the `signal_keywords` and `noise_keywords` lists in
`queries.yml`. Score = `(signal_hits × 2) − (noise_hits × 1)`.

Current word lists:

| Signal (+2 each) — 15 phrases       | Noise (−1 each) — 12 phrases    |
|-------------------------------------|---------------------------------|
| `first close`                       | `guide`                         |
| `raising our`                       | `tips`                          |
| `our first fund`                    | `how to`                        |
| `fund i`                            | `webinar`                       |
| `emerging manager`                  | `must-dos`                      |
| `first-time fund manager`           | `must do`                       |
| `solo gp`                           | `playbook`                      |
| `anchor lp`                         | `course`                        |
| `anchor investor`                   | `newsletter`                    |
| `lp commitments`                    | `hiring`                        |
| `soft commitments`                  | `fund iv`                       |
| `debut fund`                        | `fund v`                        |
| `launching our`                     | `fund vi`                       |
| `spinning out`                      |                                 |
| `now raising`                       |                                 |

**Why explicit phrase lists, not LLM scoring:** transparency. The user
can see, edit, and defend every signal. An LLM-scored leaderboard is
opaque ("why is this person ranked 1st?"). A score of 6 here means
"three signal phrases hit, zero noise" — defensible to a sales lead.

**Why signals weight 2× and noise weights 1×:** signals are explicit
("first close" is unambiguous). Noise phrases are softer
disqualifiers — a "guide to raising a fund" post is probably not a
GP, but the noise penalty being lighter than a signal hit lets a real
signal still surface a post that happens to use one noise word.

**Why score `title + snippet` and not the full post:** the engine
never opens LinkedIn — it only sees what Google indexed. Snippet +
title is the entire signal surface.

**Why exclude Fund IV–VI from "fund i" matches:** those are
established mid-sized firms, not emerging managers. Cheaper than
training the user on substring-matching nuances.

### Step 5 — Dedupe and rank

**What:** Aggregate by profile slug. For each profile, track
`posts_found` (how many of this run's results matched them) and keep
the **highest-scoring post** as the "evidence" row.

Sort key:

```
(not is_company, score, posts_found)   reverse=True
```

In English: persons before flagged organizations; then highest score;
then most posts_found as a tiebreaker.

**Why dedupe by profile, not by post URL:** one fund manager often has
3–5 posts matching across the queries. Without dedupe, the top of the
ranked list would be the same person five times.

**Why posts_found as a tiebreaker:** if two profiles tie on score, the
one that surfaced across multiple queries is more likely to be the
genuine signal (less likely to be a single-snippet coincidence).

**Why the `is_company` demote, not delete:** a fund's official page
sometimes posts a "we just closed" announcement; that post can be
useful context (which fund, which size) even if it isn't the outbound
contact.

### Step 6 — Write outputs (`write_outputs`)

Writes two files at the chosen `--out` path:

- `<out>.md` — human-readable ranked table with the disclaimer at the
  top (these are candidates, not vetted leads).
- `<out>.csv` — same data + the raw snippet, machine-readable.

---

## ToS-safe by design

The tool searches **Google's index only**, through SerpAPI. It never
opens, scrapes, or interacts with linkedin.com — so there is no
LinkedIn Terms-of-Service or account-ban risk.

Reading the *engagement* on a post (who commented, who reacted) would
require loading LinkedIn directly; that is the **designed next step**,
deliberately not built here. Doing it ToS-safely would require either a
seat on LinkedIn Sales Navigator + the Marketing API, or a
human-in-the-loop workflow where the user opens a post themselves.

---

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Get a free SerpAPI key at <https://serpapi.com/> — the free tier
   gives 100 searches/month.

3. Copy `.env.example` to `.env` and paste your key:

   ```
   SERPAPI_KEY=your_key_here
   ```

## Run it

| Command                                            | Effect                                          |
|----------------------------------------------------|-------------------------------------------------|
| `python find_leads.py --dry-run`                   | Print the queries that would run. 0 API calls.  |
| `python find_leads.py`                             | Demo run — 6 queries, capped at 8 calls.        |
| `python find_leads.py --full --max-searches 60`    | Full sweep — 16 queries, raised cap.            |
| `python find_leads.py --out path/to/leads.md`      | Custom output path (writes `.md` + `.csv`).     |

- The **default run is the small demo set** (~6 searches), so it
  cannot accidentally spend your monthly quota.
- `--max-searches N` is a hard cap (default 8). For the full sweep,
  raise it to ≥ the number of queries in the `full` set (currently 16).
- The script does not retry on API failures; it stops cleanly so you
  don't burn quota chasing a bad key.

## The output is candidates, not vetted leads

The tool finds *post authors* who used fund-raising language. Confirming
each one is genuinely an emerging fund manager who fits the ICP is a
**human step** — a search snippet does not carry a reliable job title.
Treat `sample-output` as a shortlist to review, not a finished lead
list.

## Verified leads — proof the mechanism works

[`verified-leads.md`](verified-leads.md) shows the human-vetting step
carried out on one run: from a 126-candidate full run, the top 12
strongest signals were checked against public sources and **5 were
confirmed** as genuine emerging fund managers actively raising:

| # | Name              | Fund                          | Verified raise                              |
|---|-------------------|-------------------------------|---------------------------------------------|
| 1 | Joseph Alalou     | Daring Ventures               | first-time GP raising debut fund            |
| 2 | Nader Amiri       | Homegrown Ventures (UAE)      | closed Fund I at **$22.8M** vs $20M target  |
| 3 | Saum Vahdat       | Bridgewest Ventures (NZ)      | **$55.3M first close**, ahead of target     |
| 4 | Avijeet Alagathi  | Veda VC (India)               | first close of **$30M** fund                |
| 5 | Rabeel Warraich   | Sarmayacar (Pakistan)         | first close of **$30M** debut fund          |

12 vetted → 5 confirmed (42% pass rate). The other 7 were excluded
mostly because they were fund employees (an investment director at an
established firm posting about a close), not the founding GP. Catching
those is precisely the job of the human-vetting step.

## Limits, and designed-next-steps

| Limit today                                                | Designed next step                                                  |
|------------------------------------------------------------|---------------------------------------------------------------------|
| No recency filter — surfaces posts of any age              | Add post-date filter via the `date` SerpAPI parameter (small change)|
| Only the post author is surfaced (not commenters)          | Load the post in a human-in-the-loop workflow (ToS-safely)          |
| Scoring is keyword-based, not semantic                     | Add an LLM second-pass to re-score the top N candidates             |
| Free tier ≈ 100 SerpAPI calls/month — caps weekly cadence  | Paid tier ($75/mo) for daily cadence; or rotate across free tiers   |
| Person-vs-company heuristic uses a small org-suffix regex  | Cross-check with a person-detection API or LLM                      |
