# Verified leads — human-vetted sample

The lead-discovery tool surfaced **126 candidate contacts from 16 searches**
(see `sample-output.md`). This file is the **human-vetting step**: the 12
strongest signals were checked against public sources, and the 5 below were
confirmed as genuine emerging fund managers who publicly announced a raise.

This is the growth mechanism in miniature — **discover (tool) → vet (human) →
qualified lead.**

## The 5 verified leads

| # | Name | Fund | Role | The raise (verified) |
|---|------|------|------|----------------------|
| 1 | Joseph Alalou | Daring Ventures | Co-founder & GP — a first-time fund manager | raising the firm's debut fund |
| 2 | Nader Amiri | Homegrown Ventures (UAE) | Co-founder | closed debut Fund I at **$22.8M**, beating its $20M target |
| 3 | Saum Vahdat | Bridgewest Ventures (NZ) | CEO | Fund I — **$55.3M first close**, ahead of target |
| 4 | Avijeet Alagathi, CFA | Veda VC (India) | Co-founder | first close of a **$30M** fund (₹150 Cr committed) |
| 5 | Rabeel Warraich | Sarmayacar (Pakistan) | Founder & CEO | first close of the firm's debut **$30M** fund |

## The evidence — profile + the signal post that surfaced each

**1. Joseph Alalou** — Daring Ventures
- Profile: https://www.linkedin.com/in/josephalalou
- Signal post — *"we've been raising our first fund, and here's…"*
  https://www.linkedin.com/posts/josephalalou_weve-been-raising-our-first-fund-and-heres-activity-7432802876587962370-S2mh

**2. Nader Amiri** — Homegrown Ventures
- Profile: https://www.linkedin.com/in/nader-amiri-cpg
- Signal post — *"we just closed our first fund, and this…"*
  https://www.linkedin.com/posts/nader-amiri-cpg_we-just-closed-our-first-fund-and-this-activity-7449682880777322497-JXBp

**3. Saum Vahdat** — Bridgewest Ventures
- Profile: https://www.linkedin.com/in/saum-vahdat
- Signal post — *"proud to be launching our fund alongside…"*
  https://www.linkedin.com/posts/saum-vahdat_proud-to-be-launching-our-fund-alongside-activity-7355422613873049600-fJ3L

**4. Avijeet Alagathi, CFA** — Veda VC
- Profile: https://www.linkedin.com/in/avialagathi
- Signal post — *"Veda VC announces first close of [its] $30M fund"*
  https://www.linkedin.com/posts/avialagathi_veda-funding-veda-vc-announces-first-close-activity-7099321760772210688-ZPCB

**5. Rabeel Warraich** — Sarmayacar
- Profile: https://www.linkedin.com/in/rabeel-warraich-572a5714
- Signal post — *"excited to announce the first close of Sarmayacar…"*
  https://www.linkedin.com/posts/rabeel-warraich-572a5714_excited-to-announce-the-first-close-of-sarmayacar-activity-6466593368318275584-bMM1

## Honest notes

- **Vetting pass rate:** of 12 strong signals checked, **5 confirmed**. The other
  7 were excluded — fund *employees / directors* who posted about a close but
  are not the founding GP (e.g. an investment director at an established firm),
  or a name mismatch (a wealth-management advisor, not a VC). Catching these is
  exactly the job of the human-vetting step.
- **Recency:** the tool surfaces posts of any age. Leads 1–3 are recent / active
  raises; leads 4–5 are older first closes. A production run would add a
  post-date filter — a small, easy enhancement.
- **Scale:** this used 16 searches on SerpAPI's free tier. The full 126-row
  candidate list is in `sample-output.md`.
