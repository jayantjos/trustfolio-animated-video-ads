# TrustFolio Animated Cartoon Video Ads

**Status: 3 playable historical-data animated MP4 demos; production publishing remains blocked/OFF.**

Private development repository, isolated from TrustFolio's existing scheduled image
advertisements, website, Android app, MongoDB and scraper.

## Implemented

- Read-only official TrustFolio Top-5 API client with strict rank, category,
  budget, brand, active/in-stock and individual price freshness checks.
- Separate historical-demo validation: original signed response hashes, genuine
  product IDs, genuine historical ranked prices, HTTPS retailer images, no
  reranking, no live-price claims; permanently watermarked and unpublishable.
- Creative registry: 20 backend-supported category story/world templates and
  10 intentionally disabled slots; 3 advertising modes, 15/20/30s storyboards.
- Twenty distinct Hindi/Hinglish dialogue drafts and creative world concepts.
- CPU-only layered character animation for three pilot worlds with actual
  retailer photos, moving arms/legs/eyes/mouth and reacting partner characters.
- Offline eSpeak character voices (experimental robotic Hinglish only), original
  procedural background music and pop SFX; safe scene timing and subtitle captions.
- Genuine 1080×1920 24fps H.264/AAC MP4 export via FFmpeg, with QA JSON,
  immutable source storyboard JSON and independently extracted frame samples.
- 36 passing source tests, including the original 180 storyboard combinations,
  with GitHub Actions video artifacts for three demo pilots.
- Video publishing OFF; no credentials or new social scheduling jobs.

## Reproduce one historical QA-only pilot

Requirements: Python 3.11+, Pillow 11.3, NumPy 2.2, FFmpeg/FFprobe, eSpeak.

```bash
python -m pip install 'Pillow==11.3.0' 'numpy==2.2.6'
python -m unittest discover -s tests -v
python -m trustfolio_video.cartoon \
  --snapshot evidence/washing-machines-snapshot.json \
  --output output/washing-machines-demo.mp4 \
  --duration 15
```

For a complete automated three-video smoke test, run the
`Genuine cartoon video pilots (DEMO ONLY)` workflow in GitHub Actions.

The output video, storyboard, original five product IDs and image evidence,
recorded prices, preview image, and media QA report are uploaded as a workflow
artifact. Videos are NOT automatically published.

## Three pilot creative worlds

1. Washing Machines — ₹35,000 — Bubble Laundry Kingdom — budget/funny.
2. Samsung Smartphones — ₹20,000 — Neon Notification Nagar — brand+budget.
3. Headphones/Earbuds — ₹3,000 — Beat Street — comparison.

Prices are historical and do not imply current retailer stock or offer.

## Not production-ready

- All 15 original pilot products lack trustworthy per-item price check times.
  Several were catalog-price fallbacks. Strict live-price validation correctly
  prevents public ad approval.
- eSpeak demonstration voices are not yet approved natural Hindi/Hinglish.
- Official logo and retailer product image advertising rights unverified.
- Character movement and expressions are basic rigs, not advanced cinematic
  cartoon animation or phoneme-accurate lip sync.
- Only 3 of 20 verified categories have actual distinct video environments.
  17 categories are storyboard-level only, and 10 unknown slots disabled.
- Instagram Reels/Facebook Reels/YouTube Shorts publishing remain OFF pending
  explicit authorization and provider account rights.

See `docs/STATUS.md` and `docs/CARTOON_PILOT_STATUS.md` for current
implementation evidence, licensing limitations and remaining milestones.

Do not merge the draft PR into a publishing or production deployment flow just
because these watermarked demo MP4s passed technical tests.
