# TrustFolio live video cron: exact design and completion gates

## The requested production flow

`Separate VPS cron → GET /api/products/top + POST /api/live-prices → current, budget-safe Top5 → GitHub Actions → validation → queue → RunPod GPU worker → animated scenes + independent Hindi lipsync → MP4 S3 and SHA256 → terminate GPU Pod → verify Pod absent → next cron job`.

The separate VPS is ONLY the schedule and live data producer. Do not alter the already-running ads pipeline or deploy any cron without confirming access and its existing even/odd budget and category schedule. Job dispatch needs an intentionally scoped GitHub token and duplicate detection; source envelope must be authenticated between systems. Published ads remain a separate disabled phase.

A trusted cron JSON payload requires:
- `schema_version: 1`, `producer: trustfolio-vps-cron`
- unique `job_id` and timezone-aware recent `requested_at`
- `campaign: {category, budget, mode, brand}` where mode is `budget`, `brand_budget`, or `comparison`
- `snapshot`: the unmodified response envelope from the existing `trustfolio_video.contract.fetch()` function, not an invented or historical sample.

`python -m trustfolio_video.cron_video_job --input private_live_payload.json --output output/validated-video-job.json` validates all five product IDs, rank order, each current live price check, availability and budget. It does NOT render, rent a GPU, or publish. A price refresh must run AGAIN before the actual GPU render; a queued snapshot can age out.

## Video timing from the supplied storyboard reference

0–3 sec fixed woman reacting to laundry, 3–6 intro, rank 5 at 6–10, rank 4 at 10–14, rank 3 at 14–18, rank 2 at 18–22, rank 1 at 22–26, podium at 26–28, TrustFolio CTA at 28–30. Product names/prices in the supplied image are VISUAL EXAMPLES ONLY. They cannot be copied as real live prices. Only the validated backend ranks and trusted unmodified product photos can be displayed, with removable mascot overlays.

## Saved vs missing

- DONE: Twenty category slugs, themes, palettes, script ideas and location paths (configuration ONLY); one canonical pink-kurta-woman ID for all 20; the storyboard timeline and dynamic live rank-mapping contract.
- DONE: Pre-existing `1bch597yrz` EU-RO-1 100GB Standard Network Volume; 9 Wan2.2 files totaling 34,180,083,066 bytes with successful remote audit and initial upload checksums; 3 Hindi preview clips on S3 with exact S3 GET checksums.
- NOT DONE: Original pink-kurta PNG has not been staged into S3; 20 per-category backgrounds are **not rendered nor approved**. At least 3 Washing Machine scene pictures are missing. No final 30s animated MP4, real lip-sync, live Top5 on a fresh cron run, or production publishing.
- NOT DONE: The actual other VPS cron wiring, independent GPU reaper, Pod API write key, hourly account quote, authorized GPU spending. The current RunPod GPU cost permission is **$0**. Thus no Pod launch workflow exists in this PR.
- Vimeo/YouTube/Meta publishing remains disabled. Existing image-ad workflows untouched.

## GPU cost and destruction policy

RunPod supports Pods and attachable Network Volumes. After the movie is saved into persistent S3 and its digest is verified, terminate (DELETE) the GPU Pod, NOT merely stop it. A provider-level terminate-after timer and separate reaper/watchdog are both needed as failure backstops, with idempotent deletion and confirmation. The persistent **network volume remains**, continuing its separately approved ~$7/month charge even when GPU Pods are destroyed.

See RunPod official documentation: https://docs.runpod.io/runpodctl/reference/runpodctl-remove-pods and https://docs.runpod.io/pods/troubleshooting/zero-gpus

The model and assets remain on the persistent volume. Each new paid GPU should attach exactly volume `1bch597yrz` in `EU-RO-1`, then load existing weights instead of downloading all 34GB from Hugging Face. GPU attach success and actual 24GB VRAM performance have not been tested.

The user-provided sample includes illustrative claims about AI Wash, Steam, origins and efficiency; never publish invented feature claims without reliable product evidence. The approved production character must be preserved exactly and Hindi dialogs need human listening QA; rendering moving lips from separate TTS audio is a distinct tested model step, not accomplished by muxing.

This PR is implementation-in-progress, not an approved production deployment.
