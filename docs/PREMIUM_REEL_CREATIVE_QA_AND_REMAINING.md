# Premium Bubble Kingdom: verified progress and remaining work

Date: 2026-10-19. This is a private, demo-only branch of
`jayantjos/trustfolio-animated-video-ads`, not a live-ad deployment.

## Implemented and tested

- React / Remotion 4 1080×1920 24fps, 30-second video compositor.
- Actual original TrustFolio backend historical washing machine Top-5 product
  IDs, source rank order, brands, images, historical prices and original SHA.
- Five independently animated product-card characters with talking faces,
  smiling mouths responsive to voice energy, waving cartoon hands, legs,
  rotating body and partner reaction. These are **stylized product-photo
  characters**, not 3D film-quality cartoon characters.
- Distinct bubble-laundry background, branded premium purple-yellow
  header/footer, headline, ranks, price banners, subtitle overlays, CTA.
- Kokoro-82M neural Hindi evaluation, `hf_alpha` and `hm_omega` voices, model
  Apache-2.0, no paid APIs. Published upstream Hindi voice quality grade C:
  not a substitute for human listening or high-end natural voices.
- Original procedural music and SFX, audio-energy-driven mouths, 7 Hindi lines.
- First 30-second private MP4 achieved automated technical QA: H.264, AAC,
  1080×1920, 30.06s. Frame inspection revealed a final group-frame collision
  between purple Hindi CTA and product price cards.
- Follow-up correction: adjusted final group character scale and vertical
  positions, placed the closing Hindi CTA in a separate rounded panel.
  Extended arms outside product-card bodies and added waving glove/foot
  gestures so cartoon movement is visible in the actual rendered video.

## Unfinished requirements (do not misreport as done)

1. **Human creative QA** of the corrected frame sequence, plus native Hindi
   listening review. A green CI result does not prove visual attractiveness.
2. Natural expressive Hindi character dialogue: consider opt-in Sarvam Bulbul
   v4 Flash after explicit approval of paid API use and secure secret setup, or
   separately benchmark commercially permitted offline voices such as
   AI4Bharat IndicF5 after validating consent/licensing of reference speakers.
   Do **not** automatically fall back to robotic eSpeak.
3. Verified official TrustFolio logo artwork (current top shield and wordmark
   are concept marks), media asset rights for retailers' product photography.
4. Fresh per-product retailer price-check timestamps / source and stock
   evidence: current historical snapshot has incomplete freshness evidence.
   Retain the perpetual `CONCEPT DEMO - HISTORICAL PRICES - NOT FOR
   PUBLICATION` mark on all frames; do not publish.
5. More nuanced mouth phonemes, staging, camera choreography, fully rigged
   standalone cartoon product bodies and comedic back-and-forth. Current
   characters are talking product cards, a deliberate CPU-compatible pilot.
6. Expand production-ready renders to 20 backend-supported categories, three
   modes and 15/20/30s variants (only washing-machine premium mode complete).
   Ten slots remain unsupported/disabled until backend provides categories.
7. Private preview quality approval before any merging to production or
   enabling Instagram/Facebook Reels/YouTube Shorts API writes.

## Sources

- Kokoro official model and license: https://huggingface.co/hexgrad/Kokoro-82M
- Kokoro Hindi voice training grades:
  https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
- Sarvam Bulbul API docs (no API called):
  https://docs.sarvam.ai/api/getting-started/models/bulbul
- AI4Bharat IndicF5 official GitHub:
  https://github.com/AI4Bharat/IndicF5

## Safety

Old TrustFolio website, VPS, MongoDB, Android, scraper, static image ads,
scheduled posts, social account tokens and publishing ledgers remain untouched.
GitHub Actions only generates private artifacts for creative review.
