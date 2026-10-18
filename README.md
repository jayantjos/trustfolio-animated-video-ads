# TrustFolio animated video ads

Status: **foundation implemented; production animation system incomplete**.
This private repository is isolated from `jayantjos/trustfolio-daily-ads`.
Publishing is hard-disabled. No schedules, deployment hooks, website writes,
MongoDB access, ranking changes, or existing social workflow changes exist here.

## Implemented

- Read-only authoritative `/api/products/top` client with response size limit,
  no redirects, bounded transient retries and source hashing.
- Exact five-product/rank/identity/category/budget/brand/availability checks.
- Fail-closed price freshness checks; never substitutes, reranks or performs a
  redundant `/live-prices` request when the backend already refreshed prices.
- Thirty-slot creative registry: 20 canonical backend categories, 10 disabled
  placeholders without invented backend slugs.
- Hinglish storyboard planning, three campaign modes, three durations, alternate
  template rotation, source-bound comparisons and removable character layers.
- Static, registry/storyboard and manual live-validation Actions workflows.
- Historical pilot evidence containing source IDs, observed prices and blockers.

## Run

Python 3.11+; standard library only for this foundation.

```sh
python -m unittest discover -s tests -v
python -m trustfolio_video.cli --category washing-machines --budget 35000 --mode budget --output output/washing
python -m trustfolio_video.cli --category smart-phones --budget 20000 --mode brand_budget --brand Samsung --output output/samsung
python -m trustfolio_video.cli --category headphones-earbuds --budget 3000 --mode comparison --output output/earbuds
```

Exit 2 means BLOCKED, with JSON reasons and the original response retained.
Exit 0 means data approval only, never video approval. `evidence/` contains
historical snapshots; do not use them as fresh rendering or publishing inputs.

## Current blocking evidence

On 2026-10-18 all three requested pilot queries returned five products and
`livePriceRefreshCompleted=true`. All 15 rows lacked `live_checked_at` and
`live_priced_at`. Six rows had catalog fallback with null or `no_price` status.
The aggregate flag alone does not prove that each displayed price is fresh.
No MP4s were produced using these unverified candidate sets.

The price timestamp fields are a **required future contract**, not fields
claimed to exist in the observed API. The strict policy is 15 minutes maximum
age, with 60 seconds clock-skew tolerance. Missing evidence blocks rendering.
Backend changes require separate authorization because this task forbids them.

## Not implemented / not approved

CPU animation composition, downloadable pilot MP4s, licensed brand asset
extraction, TTS, Hindi/English language packs, audio mixing, subtitle rendering,
visual frame inspection, model/license evaluation, video QA and publishing API
adapters are not completed. Style labels are planning metadata, not distinct
renderers. World hooks are original but full character dialogue still needs
creative development. No production-ready claim is made.

See `docs/STATUS.md`, `docs/EXISTING_SYSTEM_REVIEW.md` and
`docs/DEPLOYMENT_AND_ROLLBACK.md` for exact limitations and continuation steps.
