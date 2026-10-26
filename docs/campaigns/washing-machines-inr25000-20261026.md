# TrustFolio Washing Machines ₹25,000 — verified live-price check 2026-10-26

- User-requested budget: **₹25,000**, mode **Budget**, category `washing-machines`.
- GitHub Actions run: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40259748018
- Diagnostic artifact: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40259748018/artifacts/12623492784
- Result: **failure** of strict live-price verification (not an error in the offline validation tests).
- Local Python source tests: **20 run, 19 passed, 1 skipped** (local-only master not available on GitHub runner).
- Exactly one `GET /api/products/top?category=washing-machines&budget=25000&limit=5` and one exact-five-ID `POST /api/live-prices` were used. No automatic retry.
- API check time: **2026-10-26T02:34:26Z** (rounded).
- **No verified-five-product receipt, no Google Flow prompt/image handoff, no final dynamic video, no social publishing or paid GPU.**

| Rank | Product (title shortened for report) | Platform | Live status | Verified live price |
| --- | --- | --- | --- | --- |
| 1 | IFB 8 kg Fully Automatic Top Load, heater, 5 Star | Flipkart | `ok` | ₹23,500 |
| 2 | IFB TL801MB1S 8 kg 5 Star Top Load, Midnight Black | Croma | `missing_live` | Not verified |
| 3 | Samsung 8 kg 5 Star Hygiene Steam Ecobubble Top Load | Amazon | `blocked` | Not verified |
| 4 | Voltas Beko 6.5 kg 5 Star Front Load | Flipkart | `ok` | ₹21,640 |
| 5 | Whirlpool 7.5 kg 5 Star Inverter Bloomwash Top Load | Amazon | `blocked` | Not verified |

Evidence: `data/price_diagnostic.json` in the linked Actions artifact. Products were **not** marked deleted in the returned five price rows; this **does not** independently guarantee current stock. `missing_live` is missing usable live result; `blocked` does not by itself identify why Amazon access failed.

Exact failure: `Price unavailable or catalog fallback; ad withheld`.

**Safety:** The source selection order remains unchanged. Any unknown/fallback price is **not** relabeled as live or assumed to be within budget. The one-shot workflow was made **manual-only** after its initial run (commit `51cbbca14b274941bc51530095d0904d58ce9ef9`) to prevent automatic repeat API charges. No modifications to the separate TrustFolio app repo, no RunPod GPU run, no social publishing.

**Follow-up engineering** (not executed): trace Croma live-price result mapping/endpoint, diagnose Amazon `blocked` reason, then request one fresh paid/API-cost-aware verification check after fixes. Refresh prices immediately before publication rather than treating this historical receipt as current.
