# Lead-Discovery Engine

Finds emerging fund managers who are publicly signalling — on LinkedIn — that
they are raising a fund, and turns them into a ranked list of potential
contacts.

Built for capq.ai's Task 3 growth mechanism (Renn Labs Marketing Challenge).

## What it does

```
  queries.yml ──► SerpAPI (Google search) ──► LinkedIn post results
                                                     │
        ranked contact list  ◄── score ◄── dedupe ◄── extract author
        (sample-output.md + .csv)
```

1. Reads precision-tuned `site:linkedin.com/posts` queries from `queries.yml`.
2. Runs them through Google, via the SerpAPI search API.
3. For each post result, extracts the **author** — the person — as a contact
   (name from the result title, profile from the post URL).
4. Dedupes by profile, and scores each contact by fund-raising-signal strength
   (signal phrases add points; noise phrases — "guide", "webinar", "Fund IV" —
   subtract them).
5. Writes a ranked contact list to `sample-output.md` and `sample-output.csv`.

## ToS-safe by design

The tool searches **Google's index only**, through SerpAPI. It never opens or
scrapes linkedin.com — so there is no LinkedIn Terms-of-Service or account-ban
risk. Reading the *engagement* on a post (who commented or reacted) would
require loading LinkedIn directly; that is the **designed next step**,
deliberately not built here.

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Get a free SerpAPI key at <https://serpapi.com/> — the free tier gives
   100 searches/month.

3. Copy `.env.example` to `.env` and paste your key:

   ```
   SERPAPI_KEY=your_key_here
   ```

## Run it

```
python find_leads.py --dry-run                  # print the queries — 0 API calls
python find_leads.py                            # demo run — ~6 searches, quota-safe
python find_leads.py --full --max-searches 60   # the full sweep
```

- The **default run is the small demo set** (~6 searches), so it cannot
  accidentally spend your monthly quota.
- `--max-searches N` is a hard cap (default 8). For the full sweep, raise it.
- Output: `sample-output.md` (ranked table) and `sample-output.csv`.

## The output is candidates, not vetted leads

The tool finds *post authors* who used fund-raising language. Confirming each
one is genuinely an emerging fund manager who fits the ICP is a human step —
a search snippet does not carry a reliable job title. Treat `sample-output` as
a shortlist to review, not a finished lead list.

`verified-leads.md` shows that vetting step carried out: from a 126-candidate
run, the 12 strongest signals were checked against public sources and 5 were
confirmed as genuine emerging fund managers — evidence that the candidates the
tool surfaces are real.
