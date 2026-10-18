# Read-only review of existing system

Repository: https://github.com/jayantjos/trustfolio-daily-ads
Reviewed on 2026-10-18. No files or workflows there were modified or triggered.

| Component | Observed behavior | New engine decision |
| --- | --- | --- |
| `automation/campaigns.json` | Three modes, 20 rotation entries, budget ladders and brand candidates | Preserve modes; use backend canonical category slugs |
| `site_top5_ads_v1.py` | Normalizes API ranks; separately requests live prices | Reuse contract understanding only; no redundant refresh request |
| `site_patches/LiveBudgetRecommendationService.js` | Refreshes candidates before selection, can retain catalog prices when live status is not ok | Aggregate refresh flag alone cannot approve all displayed prices |
| `automation/auto_campaign_v1.py` | Deterministic campaign IDs and category rotation; separate publication gate | New namespace and no publication operations |
| `automation/render_real_social_short_v1.py` | Four poster-derived zoom/fade scenes, 12 seconds, no soundtrack | Not treated as product-character cartoon renderer |
| `automation/meta_graph_publish_v1.py` (opening implementation) | Account checks, quota, campaign ledger, conservative uncertain-write behavior | Do not copy tokens, account workflows or existing ledger |
| `.github/workflows/auto-instagram-campaigns.yml` (configuration) | Existing cron slots and separate Meta/Metricool gates | No edits and no new cron |
| `.github/workflows/deploy-production.yml` | SSH secrets, pinned host key, allowlist, backup/rollback deployment | Do not invoke or reuse old deployment paths |

Public GET `/api/categories` returned 20 categories. Canonical differences from
old rotation aliases include `air-conditioners`, `air-coolers`, `geysers`,
`induction-cooktops`, `microwave-ovens`, `mixer-grinders`, `refrigerators`,
`vacuum-cleaners`, `washing-machines` and `water-purifiers`.
The old image automation is not changed to adopt these aliases.

This is a source/configuration review, not a full production-runtime audit.
VPS authentication, deployment history, current scheduled posts and account
tokens were not inspected. Existing repository secrets cannot be read or copied
by this session. No production service was restarted.
