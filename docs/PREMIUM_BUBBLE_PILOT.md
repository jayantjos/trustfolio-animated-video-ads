# TrustFolio Premium Bubble Kingdom: private quality-gated pilot

**Scope:** only the separate video repository. Existing TrustFolio site, MongoDB, Android app, image-ad automation, scheduled Metricool ads, Meta and YouTube accounts remain untouched.

## Product/data provenance

- Source: pre-existing `evidence/washing-machines-snapshot.json` obtained from the genuine TrustFolio backend.
- Category/mode/budget: washing-machines / budget / ₹35,000.
- No product ID, original rank, advertised source price, category, brand or retailer may be fabricated, changed, replaced, or reranked.
- `premium/prepare.py` reuses `trustfolio_video.demo.approve_historical_demo` and copies genuine source retailer product images from allowlisted HTTPS origins.
- This snapshot is historical, does not prove each of the five item prices freshly verified, and is not approved for publishing.
- A persistent full-video demo watermark and disclaimer are mandatory.

## Premium pilot

- `premium/src/Reel.jsx` uses Remotion 4 / React for 1080×1920 24 fps 30-second animation.
- Style: playful blue-lilac Bubble Laundry Kingdom, podium-style photo characters, independently moving limbs and eyes, 5→1 ranked hero sequence, subtitles, fixed TrustFolio style title, CTA and footer.
- Typography uses installed open-source Noto Sans Devanagari fonts.
- Prototype concept wordmark is **NOT an independently verified official logo asset**. Official vector logo needs separate provenance before final approval.
- All character faces and limbs are *removable* layers; the original product pictures remain real and recognizable, in fixed source rank order.

## Neural Hindi audio evaluation

- Evaluation model: hexgrad/Kokoro-82M / `kokoro==0.9.4`, Apache-2.0.
- Uses real Hindi Devanagari, female/male voice identifiers hf_alpha and hm_omega, and a synchronized 100-ms narration-energy envelope for mouth motion.
- Instrumental bed and bubble SFX are synthesized from original Python signals: no downloaded samples, copyrighted song or cloned human voice.
- The open model’s published Hindi voice grades are modest; natural Indian voice quality **MUST BE REVIEWED BY HUMAN LISTENING** before use.
- A future Sarvam Bulbul v4 Flash adapter might offer more natural Hinglish, but **NO API call or paid usage is authorized or performed in this branch**. The user must separately authorize API usage/cost and configure their own secret; credentials must never appear in chat, commits or logs.

## Licensing

- Remotion 4: license is free for individuals / eligible organizations up to 3 people; 4+ person for-profit companies need company license. Verify actual entity eligibility before production.
- Kokoro model Apache-2.0, voice availability/quality varies.
- FFmpeg and libx264 binary redistribution can trigger GPL/LGPL obligations; no distributed encoder binaries in Git.
- PIL/Pillow/NumPy/SoundFile dependencies use their own open-source terms.
- Original commercial-retailer images are included for private QA preview only; advertising/commercial image licensing has not been approved.
- Official TrustFolio icon reproduction rights and accurate original source asset pending owner verification.

## Quality gates

The GitHub Actions pilot workflow:
1. Runs the existing 36 pipeline contract/storyboard regression tests, including 180 combinations.
2. Loads five genuine photos and keeps source IDs/ranks unchanged.
3. Generates native Hindi narration without the old robotic eSpeak fallback.
4. Renders actual motion video with synchronized subtitles and audio.
5. FFprobe verifies H264 video, AAC audio, 1080×1920, 30-second duration.
6. Extracts eight independent frame stills for human inspection.
7. Uploads the MP4, QA reports and frames in a private GitHub Actions artifact, **never social platforms**.

**Do not equate passing video technical QA with approval of voice quality, brand look, creative taste, retail-price freshness, official logo or product image usage.**

## Production blockers

- Trustworthy per-item live price-check timestamps and non-fallback status from current backend.
- Verified official TrustFolio logo asset.
- Approval for actual advertising reuse of retailer imagery.
- Native Hindi speech clarity and timing human sign-off.
- Visual inspection of 1/5/9/13/17/21/26/29-second frames and correction of overlaps.
- Explicit social platform OAuth/account checks and separate written enablement.
