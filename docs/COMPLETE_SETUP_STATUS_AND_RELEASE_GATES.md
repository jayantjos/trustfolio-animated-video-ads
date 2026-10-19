# TrustFolio animated advertising — setup inventory and release blockers

Updated: 2026-10-19. Branch: `feature/30-category-educational-story-engine-20261019`.
Scope: new private animated-video GitHub repository ONLY. No production SSH,
MongoDB, website/Android edits, image-ad schedule or social publication.

## Verifiably configured

| Module | Status | Evidence |
| --- | --- | --- |
| Private repo + foundation | Implemented, draft PR #1 | Existing data contracts, 20 world registry and 10 disabled future slots |
| Premium washing-machine video | Implemented as DEMO, PR #2 | Existing Remotion 30-second MP4 and experimental neural Hindi audio; still no human creative or voice approval |
| Thirty-slot category education registry | Implemented | `config/category_education_30.json` with 20 real backend slugs/IDs, 10 unsupported placeholders kept OFF |
| Educational facts | Implemented | `trustfolio_video/educational.py`, exact source specification field matching, no invented feature or ranking cause |
| Budget / Brand+Budget / Comparison | Implemented in storyboard | All 20 supported category configs × 3 modes covered by automated generated-story QA |
| Original 20-world visual atlas | Rendered as environment concepts only | `config/world_motion_20.json`, `premium/src/WorldAtlas.jsx`, original artwork paths, 20 PNG previews + 3 short moving parallax MP4s |
| Existing source contract | Preserved | Strict per-product live-price freshness, budget, brand and ranking validation unchanged |
| Historical demo contract | Preserved | Signed snapshot hash, original ranked IDs, watermark, publication OFF |
| Natural Hindi voice evaluator | Partial | Kokoro-82M Hindi speech and synchronized subtitles, but human clarity/timing signoff missing |
| Safe narration handling | Implemented | Audio never clipped; long voice lines are re-synthesized more concisely and visual subtitles updated to match |
| Safety readiness report | Implemented | `trustfolio_video/readiness.py`, source/media/licenses/voice/OAuth checks and publish OFF |
| 3 source-ranked storyboard exports | Completed | washing-machine Budget, Samsung Brand+Budget and Earbuds Comparison; 15 authentic historical source products |
| Automated CI | Successful | 60 tests; 180 earlier storyboard combinations; 60 new educational combinations; visual atlas and source identity validations |
| 20 real production-approved category videos | **NOT COMPLETE** | World previews are independent scenic prototypes, not complete product videos |
| All 30 active categories | **NOT POSSIBLE** | Backend supports 20, future 10 disabled until verified categories exist |
| Production publishing | **OFF** | No provider OAuth authorization, publication ledger or approved publish adapter in this repo |

## Source truth versus creative story

**The VPS remains the authority.** Rank, price, name, retailer, image and
specification facts must come directly from verified TrustFolio data and
preserve product-ID attribution. The master configuration defines *which*
attributes matter for a category, never supplies actual values, performance
benchmarks, proprietary recommendation scores or guaranteed suitability.

The environment and characters can be fictional, but real products must not
be cosmetically altered to become misidentified models or make new technical
claims. Comedy, dialogue and rank reveals are editorial; all factual statements
must cite a source field.

In a 30s ad, five separate rank moments only leave about 3–5 seconds each.
A full explanation of all five products requires a longer 45–60s story or an
accompanying expandable product-details page. Short reels present a SINGLE
source-verified feature per product and the website CTA; detailed five-product
educational paragraphs are preserved in storyboard JSON.

## Price-freshness and licensing gate

All archived pilot snapshots are historical and 15/15 lacked reliable
individual retail-check timestamps; catalog price fallback was observed for
several. `livePriceRefreshCompleted=true` DOES NOT establish item-level
freshness. Never replace the original check time with local request time.

Production remains blocked until:

1. A separate approved backend contract provides genuine per-item observed
   retailer price-check times and retailer availability proof.
2. TrustFolio's *real* authorized logo asset and permitted commercial use of
   retailer product images are documented.
3. A human reviewer approves natural Hindi/Hinglish audio, dialogue clarity,
   lip timing, design quality and supported feature statements.
4. Licensed animation artwork, music, video/model providers and operating
   costs are reviewed; paid Sarvam is NOT called without permission.
5. OAuth scopes, intended account identity, deduplication ledger, uncertainty
   reconciliation and explicit owner permission are implemented in a separate,
   reviewed social publishing integration.

Published videos, watermarks or price claims must not silently change due
to successful technical test runs. The repository's publisher explicitly
raises a BLOCKED exception regardless of environment variables.

## One-by-one reproducible setup checks

```bash
# On a checked-out development feature branch (no production deployment):
python -m pip install 'Pillow==11.3.0' 'numpy==2.2.6'
python -m unittest discover -s tests -v

# Source-ranked, nonpublishable educational story:
python -m trustfolio_video.educational_cli \
  --mode demo --snapshot evidence/washing-machines-snapshot.json \
  --output output/washing-machines-educational-story.json

# Read-only readiness report (expects BLOCKED, which is a safety pass):
python -m trustfolio_video.readiness \
  --snapshot evidence/washing-machines-snapshot.json \
  --story output/washing-machines-educational-story.json \
  --output output/readiness.json

# For 20 world preview stills and moving examples, use the isolated
# GitHub Action: world-atlas-qa.yml. They never claim actual product rankings.

# For source-photo-based premium demo MP4 and neural Hindi experiment, use
# the isolated GitHub Action: premium-bubble-kingdom-qa.yml.
```

## Review targets

- GitHub Actions for education storyboards: source hashes, 15 original IDs,
  five product facts, explicit not-for-publication and release blocker JSON.
- GitHub Actions for atlas: 20 genuinely distinct full-HD static world scenes,
  3 short moving scenery prototypes with no product data whatsoever.
- GitHub Actions for full washing-machine demo: actual 1080×1920 H264/AAC,
  source-bound product photography/verified specs, Hindi voice sample, 8
  still frames, licensed dependencies and actual scene duration.
- Manual visual/audio creative sign-off is **NOT** implied by CI.

Do not merge/open automatic production publishing to complete this checklist.
