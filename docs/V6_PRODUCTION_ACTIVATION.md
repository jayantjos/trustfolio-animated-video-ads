# TrustFolio Washing Machine Premium V6 — automated live Reels: activation contract

Current date: 28 Oct 2026, Asia/Kolkata. This file is the actual implementation handoff, not a claim of published content.

## What is verified

- Exact 54-second user-approved visual master binary was uploaded to `main` and checksum/format CI passed: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40592285055
- Approved original 40-second cartoon master remains untouched (assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4).
- A synthetic 54s *full original-master-derived rendering* passed GitHub Actions: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40594549201. Synthetic output is marked NEVER POST.
- Source live prices 5/5 and 4 real source specs per rank **at the test instant** passed: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40588739723
- PR #19 creates a **source-driven** 54s renderer plus persistent exact-model image SHA registry, five-short-lines Hindi TTS, audio mastering/quality checks, deterministic caption and separate direct Instagram + Facebook Reels publishing code with GitHub per-mode/day/network ledger.

## Actual automated process

1. Cron: `.github/workflows/v6-daily-live-reel-pipeline.yml`. Starts at **20:40 IST daily** (15:10 UTC) only if `TF_VIDEO_REELS_AUTO_ENABLED=true`. Manual Run Workflow also available.
2. `GET /api/products/top` gets precisely five website-ranked Washing Machines for the selected mode and budget. `POST /api/live-prices` refreshes those same five IDs exactly once. All five must have **status ok** and price ≤ advertised budget. If no data or fallback, skip; never use catalog price as verified live.
3. `v6_product_images.py` downloads model photos from allowlisted HTTPS retailer hosts. Identical cross-brand image URL/bytes, low resolution or unmaskable background: **block**. For near-white backgrounds, deterministic cutouts are made but still require one-time model-photo QA. A wrong image is never auto-approved merely because URL looks legitimate.
4. `v6_photo_registry.py` uses `masters/washing-machines/approved_product_photos.json`. Manually enter evidence-supported approval for exact product ID, original retailer image URL, processed PNG SHA256, model identifier. Once reviewed, **future budgets automatically reuse that same model hash**. Any source URL, image byte, model or photo change requires reapproval. Registry is initially EMPTY.
5. `v6_dynamic_renderer.py` uses only the original clean 40-sec cartoon story and V6's fixed CTA, and re-renders new category+budget, true 4 features for every product, same-ranked images, title, current prices, dynamic comparison, plus five independent 2.8-second product highlight slides. It never overlays new prices onto the historical V6 baked-price frames.
6. `v6_hindi_voice_tts.py` optionally requests five source-backed short Hindi voice lines from the protected speech API key **only after ALL five photos have passed the registry** (up to five billable requests, no automatic retry). Produces 14 seconds with track lengths checked. Original cartoon dialogue audio is retained and showroom ambience ducked using `scripts/mix_v6_hindi_voice.py`.
7. `v6_release_qa.py` verifies correct product IDs, exact prices, 4 features, photo approvals, deterministic text frame sources, exact 54s vertical H264+AAC format, 48 kHz audio, integrated loudness and safe peak, same-caption provenance, approved Hindi voice template, and first human-reviewed template release. If **any** missing: no public post.
8. `.github/workflows/v6-meta-reels-guarded-publish.yml` can be dispatched manually or triggered by a fully successful render. It runs only if BOTH `TF_VIDEO_REELS_PUBLISH_ENABLED=true` and `TF_VIDEO_FIRST_REEL_QA_APPROVED=true`. It SCPs the exact reviewed MP4 to the pinned, owner-controlled media host; downloads the public HTTPS version and verifies full SHA256; retrieves fresh live Top5/prices AGAIN and compares substantive rank/models/prices/specs (ignoring legitimate refresh timestamps); confirms FB Page/IG identity and quota, reserves an independent GitHub reel ledger record, and uses actual Meta Instagram/Facebook **Reels** APIs. Ambiguous publish results remain locked—no blind retry.
9. Existing daily poster-image cron, Meta JPEG publisher and its ledger are **not modified**. GPU RunPod not involved.

## One-time owner setup — only after first high-quality REAL-product reviewed Reel

GitHub → video repository → Settings → Secrets and variables → Actions.

**GitHub Actions secrets** (never paste them in chat or commit to files):
- `TF_VIDEO_OPENAI_TTS_API_KEY`: optional billable Hindi TTS. OpenAI API is separately billed; this is NOT a ChatGPT subscription entitlement. May be replaced by another user-approved source voice provider in future.
- `TF_META_PAGE_ACCESS_TOKEN`: Page access token for exact TrustFolio Facebook Page `619193294620746` linked to Instagram `@trustfolio3`. Existing image-ads repository secrets are **not automatically shared** with this repo.
- `TF_VIDEO_MEDIA_SSH_KEY`: dedicated least-privilege key limited to uploading MP4 to an owner-controlled public media directory.
- `TF_VIDEO_MEDIA_SSH_KNOWN_HOSTS`: pinned server host-key record, never disable StrictHostKeyChecking.

**Actions variables**:
- `TF_VIDEO_BUDGET_INR=25000`
- `TF_VIDEO_MODE=budget` (alternatively `brand_budget` with `TF_VIDEO_BRAND`, or `comparison`)
- `TF_VIDEO_MEDIA_SSH_HOST`: approved media upload server hostname/IP
- `TF_VIDEO_MEDIA_SSH_USER`: dedicated least-privilege upload user
- `TF_VIDEO_MEDIA_UPLOAD_DIR`: absolute directory already served as `https://media.trustfolio.in/trustfolio-videos/`. Server Nginx mapping, upload permissions and real HTTPS readback must be independently verified before enabling.
- `TF_VIDEO_REELS_AUTO_ENABLED=false` initially
- `TF_VIDEO_HINDI_VOICE_TEMPLATE_APPROVED=false` initially
- `TF_VIDEO_FIRST_REEL_QA_APPROVED=false` initially
- `TF_VIDEO_REELS_PUBLISH_ENABLED=false` initially (**emergency kill switch**)

After verified correct model photos and first preview with clear natural Hindi voice, owner may approve the first genuinely compliant Reel. Only then set the template/voice/auto/post variables true (one by one). The workflow itself never secretly enables flags.

## Current blockers, NOT falsely claimed complete

1. **IFB/Bosch bad same image URL** remains upstream on the TrustFolio site (latest ₹25k live receipt ranks 1 and 2): https://github.com/jayantjos/trustfolio-scraper/issues/1. Fix model-accurate photo data first; reapprove genuinely verified commercial source images.
2. Five exact product-photo approvals have NOT been recorded in the GitHub registry, which is intentionally EMPTY; therefore daily pipeline safely stops before voice charges.
3. Protected video-repo TTS/Meta/SSH secrets and public MP4 hosting route are NOT VERIFIED configured.
4. A genuine newly-rendered ₹25k V6 with current products and approved Hindi voice has NOT passed first human QA; all publishing flags default OFF.
5. Neither an Instagram nor Facebook V6 Reel has been published from this pipeline.

### Failure and restart rules

- API status missing/blocked, stale observation, wrong image, model/brand mismatch, not exactly 4 source-backed specs, no key, low voice quality or ambiguous Meta response → skip, quarantine audit evidence, never claim success.
- Turn `TF_VIDEO_REELS_PUBLISH_ENABLED=false` to immediately prevent subsequent writes.
- Posting ledger: `trustfolio-v6-reels-publication-ledger`; one reservation per day+mode+network. Inspect provider post IDs and ledger before any manual recovery.
- Once Washing Machine V6 is genuinely complete, reuse code with category-specific visual masters for the other 19 categories; never recycle washing-machine room as a visual for unrelated products.

**Result:** Production code/infrastructure is built and fail-closed, not actually live-posting until external model-photo and access/QA prerequisites pass.

## Confirmed read-only infrastructure audit — 28 Oct 2026

GitHub run: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40597161176 **SUCCESS** (this audit does NOT post anything).

As observed inside the ACTUAL video repo, all are **NOT PRESENT**:
- `TF_META_PAGE_ACCESS_TOKEN` secret
- `TF_VIDEO_OPENAI_TTS_API_KEY` secret
- `TF_VIDEO_MEDIA_SSH_KEY` secret
- `TF_VIDEO_MEDIA_SSH_KNOWN_HOSTS` secret
- `TF_VIDEO_MEDIA_SSH_HOST` variable
- `TF_VIDEO_MEDIA_SSH_USER` variable
- `TF_VIDEO_MEDIA_UPLOAD_DIR` variable

All four flags currently **FALSE/OFF**:
- `TF_VIDEO_REELS_AUTO_ENABLED`
- `TF_VIDEO_REELS_PUBLISH_ENABLED`
- `TF_VIDEO_FIRST_REEL_QA_APPROVED`
- `TF_VIDEO_HINDI_VOICE_TEMPLATE_APPROVED`

Meta Page/IG read-only preflight could not run without a video-repo Page token. No social write and NO live-price POST were attempted in this secret audit. The audit workflow was made manual-only after this result to prevent needless recurring Actions charges.

**Owner setup is required to proceed with public Reels**: provide these protected values through the *video repository* GitHub Settings UI, not chat or source. A connected Meta token in the separate **poster/image** repository is NOT automatically available in the video repo. Until the IFB/Bosch photo source is corrected and actual first voiced video QA passes, keep auto/publish flags OFF.
