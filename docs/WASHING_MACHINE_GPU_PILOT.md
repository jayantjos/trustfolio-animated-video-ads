# TrustFolio fixed-character GPU video pilot (Washing Machines)
## What is actually implemented
- 20 uniquely pinned category character IDs, worlds, asset paths and art directions: `config/characters_fixed.json`.
- First 30-second Hindi *story plan* with approved lead visual reference SHA, speech scripts, locations and five dynamic ranked product slots: `config/pilots/washing-machines.json`.
- Strict asset hash check, official Wan2.2 image-to-video 5-second lead-shot wrapper, and two Hindi voice adapters (offline robotic draft; official Google Cloud TTS billable opt-in).
- All product ranks/prices must come from the existing validated live API before any ad goes public; historical demo data is never publication-ready.
- The character artwork and location artwork are **not yet in Git**; original output is staged outside the repo and must pass asset intake. No 30-second GPU video or Hindi lip-sync is claimed.

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
