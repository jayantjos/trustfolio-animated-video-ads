# TrustFolio fixed-character GPU video pilot (Washing Machines)
## What is actually implemented
- One common approved pink-kurta woman across all 20 category worlds, each with unique location assets: `config/characters_fixed.json`.
- First 30-second Hindi *story plan* with approved lead visual reference SHA, speech scripts, locations and five dynamic ranked product slots: `config/pilots/washing-machines.json`.
- Strict asset hash check, official Wan2.2 image-to-video 5-second lead-shot wrapper, and two Hindi voice adapters (offline robotic draft; official Google Cloud TTS billable opt-in).
- All product ranks/prices must come from the existing validated live API before any ad goes public; historical demo data is never publication-ready.
- The canonical character artwork is verified locally against the approved SHA-256 but **not yet in Git/S3**; all 20 categories share that exact image. Location artwork is **not yet in Git**; original output is staged outside the repo and must pass asset intake. No 30-second GPU video or Hindi lip-sync is claimed.

## Make a plan on CPU
```bash
python -m unittest discover -s tests -v
python -m trustfolio_video.fixed_pilot --output output/washing-plan.json
# Optional read-only LIVE check, blocks on missing fresh prices:
python -m trustfolio_video.fixed_pilot --live --category washing-machines --budget 35000 --output output/washing-live-plan.json
```
If the scene asset paths are missing, the plan explicitly reports ASSETS_PENDING. Add category-approved images only after separate visual QA and replace the image hash in the manifest only when master art is deliberately reapproved.

## Run first 5-second silent shot on an already-owned ZERO-MARGINAL-COST GPU
Only on a 24GB+ NVIDIA GPU, with locally installed verified Wan2.2 code/checkpoints and approved image:
```bash
export TRUSTFOLIO_APPROVED_EXISTING_GPU=yes
export TRUSTFOLIO_GPU_COST_PER_HOUR_USD=0
export WAN2_REPO=/path/to/Wan2.2
export WAN2_CKPT=/path/to/Wan2.2-TI2V-5B
export TRUSTFOLIO_HERO_IMAGE=/path/to/approved/hero.png
export WAN2_OUTPUT=$PWD/output/washing-intro-silent.mp4
bash scripts/render_wan2_washing_pilot.sh
```
This does not rent a GPU, download a model, or remotely provision a server. GitHub's normal ubuntu runners and most standard Hostinger VPSs provide no NVIDIA GPU. Do not pretend an auto-stop GPU avoids billed time; if GPU is rented, stop/deprovision in finally, confirm provider billing, and charge the actual usage. The zero-dollar policy deliberately BLOCKS nonzero/unknown price GPUs.

## Hindi voice
```bash
python -m trustfolio_video.hindi_voice --backend offline-demo --output output/washing-demo-robotic.mp3
```
This creates robotic audio for timing only, not production Hindi. To call official Google Cloud TTS, the user must independently configure billing/quota controls and a short-lived authorized access token, *explicitly* opt in to possible fees, then set `TRUSTFOLIO_ALLOW_BILLABLE_TTS=I_ACCEPT_POSSIBLE_CHARGES` and `GOOGLE_CLOUD_ACCESS_TOKEN` privately. Don't commit tokens. Google's free usage is finite; model-specific charges may apply. Never describe it as unlimited.

## Integration / publishing boundary
Git is for source + manifests, not GPU checkpoint weights or large MP4 releases. GitHub Actions artifacts/object storage can retain videos. A Hostinger cron/orchestrator could later trigger an authorized GPU worker, upload MP4 + QA hashes, tear down GPU, and forward **only** validated approved videos into an isolated Meta/YouTube publishing queue. No access to Hostinger GPU/provider control plane, Meta tokens, video publishing authorization, or YouTube OAuth was available here. Existing image-ad repository and production crons are untouched. The current `trustfolio_video.publishing.publish` remains hard-disabled. Wan2.2 TI2V motion + separately muxed audio is **not** phoneme-accurate lip-sync; that remains a separate production QA gate.

## Live staging update — October 21, 2026

- Full Wan2.2-TI2V-5B storage confirmed: nine files / 34,180,083,066 bytes, HEAD audit run 39591459675, upload SHA-256 receipts on GitHub. This does not verify GPU inference.
- Common lead fixed across 20 categories: one exact SHA-pinned `pink_kurta_lady_v1.png`. The approved original is present in the conversation filesystem; it has **NOT yet been uploaded into GitHub or S3**. The new `stage-approved-character.yml` uploads it automatically when user adds it to the specified repo branch path. No fake alternate woman may be substituted.
- Natural Hindi female voice generated using Indus-Labs/indus-pocket-tts, 3 MP3 clips stored in S3 with SHA-verified receipt 39592735082. Voice needs private listening QA; CC-BY-4.0 attribution required.
- MuseTalk 1.5 was identified as a commercially supported lip-sync option (subject to checking all dependencies). No MuseTalk weights are stored or inference run. Audio muxing alone cannot pass this gate.
- New RunPod GPU spending is **NOT approved** (only existing $7/month volume approved). Do not create GPU without explicit separate budget, Pod write permissions, timeout enforcement and teardown/reaper.
- Live verified ranking and product photos, location art for the other scenes, final 30-sec video, real mouth sync and publishing are all still pending. Publishing OFF.
