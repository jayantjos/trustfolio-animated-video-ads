# TrustFolio Premium V6 54s — verified-live product video and caption/posting rollout

The user approved the V6 54-second **visual direction** on 28 Oct 2026.
Uploaded original: `TrustFolio_Washing_Premium_V6_54s_5_Product_Specs_QA(1).mp4`.
SHA256: `da1e0193a7c50bfc1253c9794bedfff941b739aead0c0a4b913f6377b16c9923`.
7,024,753 bytes; 54 seconds; 720×1280; H.264 + AAC 48 kHz stereo.

## Exact binary upload status

The 40s original master is already on GitHub. **The 54s V6 binary IS now uploaded and exact checksum-verified** (GitHub Actions run 40592285055).
The text/code GitHub connector cannot transfer MP4 bytes from this chat's local sandbox.
The approved V6 original MP4 is now at:
`assets/video/washing-machines/trustfolio_washing_v6_54s_approved_visual_master.mp4`.
Do not replace the existing 40s file. CI `verify-v6-54s-master.yml` then validates its original SHA256, size, length, dimensions and codecs.

## Live video product-price safety

For one budget + category + mode, fetch ONE authoritative Top5 from
`GET https://api.trustfolio.in/api/products/top?category=washing-machines&budget=25000&limit=5`,
then do exactly ONE POST to `/api/live-prices` with the same five IDs.
All five must have `live.status=ok` with timestamp ≤15 minutes old, prices within the budget,
four actual specifications per product, the same rank/IDs, and model-correct approved source photographs.
Catalog fallback, Croma `missing_live`, Amazon `blocked`, wrong IFB/Bosch images or stale observations **BLOCK** the Reel.
See https://github.com/jayantjos/trustfolio-scraper/issues/1 for upstream image data corruption.

The approved V6 contains **historical baked-in price text and product photos**.
A new dynamic video must be rendered from the clean original 40s cartoon footage and a new
14s five-product sequence using one current-live receipt; never label the static V6 reference a live product Reel.
A genuine generic production renderer does **not yet exist**. V6 `render_v6.py` in the supplied ZIP is historical.

`trustfolio_flow/v6_live_campaign.py` validates 5 fresh live prices, four actual feature rows,
individual photographic model approvals (including image bytes), source-specific accurate caption,
rendered text/rank/price/audio QA, and independent latest receipt match immediately before publication.
The `washing-v6-live-video-qa.yml` workflow runs offline tests on push/PR;
only **manual dispatch** performs one real live-price refresh and produces data/caption/image-review artifacts.
No automatic retry or social publish is performed from the handoff.

## Hindi voice and sound

Original V6 audio measured approx. -14.78 integrated LUFS, -0.52 dBTP, 14.6 LU LRA.
An audio-balanced derivative with video bits unchanged measures approx. -17.09 LUFS,
-1.51 dBTP and 8.2 LU LRA. **Balancing does not add Hindi product narration.**
For the 5×2.8s product showcase, each model needs a short product-specific
Hindi narration (one product intro and its verified price), human audition/QA, and ducked background ambience.
Display the four real specs visually, not hurriedly spoken in 2.8 seconds.

## Posting with caption: Instagram and Facebook Reels

Use original TrustFolio authorized Page/Instagram connection, with Page token in a protected secret,
a real publicly accessible HTTPS MP4 URL, and Meta's official Instagram Reels API:
`POST /{ig_id}/media` (`media_type=REELS,video_url,caption`), poll `FINISHED`,
then `POST /{ig_id}/media_publish`. Facebook Page Reels uses
`POST /{page_id}/video_reels` (upload_phase=start), a hosted/local video
upload to `rupload.facebook.com`, then finish with `video_state=PUBLISHED`.
Use one persistent ledger lock per campaign and network to avoid duplicate posts on timeouts.
Do not merge this with current daily poster cron. Instagram caption URLs aren't clickable;
bio link or other supported link placement requires separate setup.

**Video publisher is currently OFF and not connected to a complete rendering/hosting path.**
Do not enable any automatic video posting until source photo QA, all 5 live statuses,
new rendered MP4, clear Hindi voice, audience-safe caption, precise hosted SHA256,
Meta account/quota preflight and the first explicit approved test pass.
Proposed future kill switch: `TF_VIDEO_REELS_PUBLISH_ENABLED=false`.

## Current truth

DONE: approved V6 visual master MP4 on GitHub, exact checksum PASS, QA locally, audio-balanced derivative locally, code/test/CI/manual live handoff.
NOT DONE: upstream wrong image repair, production-ready persistent 5-product photo registry,
production dynamic video renderer, new Hindi narration, video media hosting and actual Reels publishing.
No paid GPU/Flow render and no Instagram/Facebook video post were initiated by this work.

## 28 October development update
User uploaded the approved 54s MP4; binary/hash verification PASS. New branch PR #19 implements source-driven 54s compositor, auto product-photo download + strict durable approval registry, optional limited five-line Hindi TTS, guarded daily render workflow and dedicated Meta Instagram/Facebook Reels publisher with independent ledgers/kill-switch. FULL synthetic end-to-end 54s video render: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40594549201 PASS. Production automatic posting remains OFF while IFB/Bosch share the wrong source photo and there is no approved model/photo registry, voice secret, public media SSH config or first QA release.
