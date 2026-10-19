# TrustFolio Animated Story Video Ads

Private development workspace for animated Indian-audience Reels / Shorts,
separate from the working TrustFolio website, Android app, MongoDB, and
Instagram/Facebook static-image advertising scheduler.

**State: technically working demo pipelines, NOT production-approved videos.
Social publishing is hard-disabled.**

## What actually works

| Area | Verifiable implementation |
| --- | --- |
| Original backend Top-5 IDs/ranking/price rules | `trustfolio_video/contract.py` and `demo.py` strict vs historical modes |
| Thirty category idea slots | `config/category_education_30.json`: 20 backend-supported exact slugs, 10 intentionally disabled |
| Twenty distinctive creative worlds and story hooks | `config/worlds.json`, category-specific environment, comedy, character actions and SFX |
| Source-verified category specs, purpose and cautious "why ranked" | `trustfolio_video/educational.py` |
| Budget, Brand+Budget, Comparison | 20 supported categories × 3 modes with automated scenarios |
| Independent Remotion world atlas | `premium/src/WorldAtlas.jsx`: 20 illustrated environment proofs and 3 sample moving H.264 previews |
| Product-story full-HD pilot | `premium/src/Reel.jsx`, `premium/prepare.py`, `premium/tts_kokoro.py`; washing-machine 30s private demo |
| Three historical educational storyboard outputs | `trustfolio_video/educational_cli.py` and GitHub Actions artifact, 15 authentic source-product IDs |
| Read-only safety review | `trustfolio_video/readiness.py`: records real blockers, no silent approvals |
| Quality regression tests | Python CI; existing 180 timing/storyboard cases plus 60 new category/mode educational cases, data safety and source matching |
| Older simple cartoon pilots | `trustfolio_video/cartoon.py`: 3 CPU-only prototype demos (not approved ad style) |

## Preview / test workflows

- `.github/workflows/educational-storyboards.yml`: 3 real archived Top-5
  storyboards, source claims and release blocker JSONs.
- `.github/workflows/world-atlas-qa.yml`: 20 separate world-background
  previews + 3 short animated parallax environments. These do NOT contain
  actual ranked products and are NOT finished advertisements.
- `.github/workflows/premium-bubble-kingdom-qa.yml`: 30-second real
  photographed washing-machine demo, experimental neural Hindi Kokoro audio,
  H264/AAC and 8 frame samples. The Hindi human-quality review is pending.
- `.github/workflows/static-qa.yml` and `category-storyboards.yml`:
  source validation and creative registry QA.

Reproduce the source-bound nonpublishable story and release report:

```sh
python -m pip install 'Pillow==11.3.0' 'numpy==2.2.6'
python -m unittest discover -s tests -v
python -m trustfolio_video.educational_cli --mode demo \
  --snapshot evidence/washing-machines-snapshot.json \
  --output output/educational-story.json
python -m trustfolio_video.readiness \
  --snapshot evidence/washing-machines-snapshot.json \
  --story output/educational-story.json --output output/readiness.json
```

The release report is expected to remain BLOCKED for old price snapshots.

## Why this is NOT a finished automatic production system

- Historical data has **missing individual retailer price-check timestamps**;
  stored catalog prices cannot be advertised as live.
- The retailer product-photo advertising licenses and approved official
  TrustFolio logo artwork have not been supplied/verified.
- The original cinematic 3D cartoon-world quality and lifelike five-character
  acting requested by the owner is **NOT** achieved by the current small
  vector background previews or Remotion photo rigs.
- Kokoro Hindi needs a native-speaker listening review; Sarvam would require
  separate paid API approval and secure credential configuration.
- 17 categories still need actual premium product-story Reel production and
  sound/visual review, despite 20 completed scenery previews.
- Ten proposed categories have no verified backend support and stay disabled.
- Instagram/Facebook Reels and YouTube Shorts publishing integrations are
  unapproved, without provider OAuth/account verification or an idempotent
  publishing ledger, and remain OFF.

See `docs/COMPLETE_SETUP_STATUS_AND_RELEASE_GATES.md` for a detailed checklist,
test evidence, safe reproduction and exact blockers.

**Never interpret a green GitHub Actions demo-render result as permission
to post a reel or change scheduled image advertisements.**
