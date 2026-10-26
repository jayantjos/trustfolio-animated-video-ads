# TrustFolio ₹20,000 Washing Machine live check — 2026-10-26

- Category: `washing-machines`
- Budget: **₹20,000**
- Mode: `budget` (no brand restriction)
- One-time GitHub Actions run: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40258681195
- Run ID: `40258681195`
- Commit that initiated run: `78d4dffc186812b3925340c56f00b1ea4ee257e1`
- Status: **COMPLETED / FAILURE**, source data policy blocked production
- Exact log error: `cli.py: error: Price unavailable or catalog fallback; ad withheld`
- Tests: **20 tests run; 19 passed; 1 skipped** (`local-only integration master`)
- This implies at least one of the five source products had absent/non-`ok` current price status. The log did not identify which product/platform. It does NOT prove all five products are OOS, that Croma specifically failed, or that no budget-eligible products exist.
- Receipt: **NOT PRODUCED**. There is no validated five-product price receipt, five reference-image pack or product-specific Google Flow prompt pack from this run.
- The only allowed sequence is `GET /api/products/top?category=washing-machines&budget=20000&limit=5`, then a **single** `POST /api/live-prices` with exactly those five product IDs. Source: `trustfolio_flow.live.fetch_live`.
- The current strict policy blocks any product with price status other than `ok`, including catalog-only fallback; it does not silently substitute, rerank, use stored/catalog price as live or invent specs.
- No RunPod GPU/Paid inference, no social publishing, no edits to TrustFolio app repo.
- Future attempts: one-time workflow `.github/workflows/google-flow-washing-20000-one-shot.yml` is now **manual-only**; it will not automatically retry and incur more live-price API calls. A fresh request/selection is required before a new run.
- Original approved 40-second **360p visual master is unchanged**. No AI-edited Flow video or publish-ready composite exists for the ₹20,000 selection.
- For safety, any campaign generation should stop until the backend returns five verified live prices and in-budget, available products. If the business elects to use a separate explicitly labeled catalog-price campaign, it needs a distinct verified policy and wording, not the current live-price ad.

**Next safe action:** Investigate live-status reasons in the backend price pipeline (especially missing endpoint, price worker failure, or catalog fallback) without replacing values or rerunning price refresh unnecessarily; request a fresh five-ID live receipt once fixed, then edit approved scenes 04/05/07/08/09/10 with exact real product reference images.
