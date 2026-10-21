# TrustFolio video pipeline: GitHub > on-demand GPU > GitHub

**Current scope (21 Oct 2026): Washing Machine pilot ONLY, CPU-only preflight.**
This document does not authorize GPU rental, TTS billing, publication, new crons, or a change to the existing TrustFolio image ads.

## User-requested architecture
1. GitHub is the control plane for stories, category/scene manifests, model source revision, character identity and asset references. A future VPS may only send a GitHub workflow trigger; no inference work on the VPS.
2. Keep large approved character/scene images, Hindi MP3, checkpoint weights and MP4s in separately durable storage. Never commit multi-GB weights, personal keys or production MP4s directly to Git.
3. GitHub packages the exact scene instructions, approved input image files and the approved audio into an authenticated per-job ZIP. The job contains per-file SHA256 checksums.
4. GPU worker receives that job, validates checksums and model revisions, creates scene videos, then makes a composite video with Hindi voice and independently verified lip-sync.
5. GPU worker uploads final MP4 and QA metadata to a GitHub workflow artifact or a durable object-storage bucket referenced in GitHub. Confirm successful upload and digest before teardown.
6. A future provider controller deprovisions GPU even when work fails; only after confirmed cleanup is billing assumed stopped. Publishing via Meta/YouTube is a separate, disabled phase.

## Critical durability detail
Hostinger's documentation warns that destroying a GPU instance permanently removes its local data. Thus simply caching checkpoint files on the GPU instance is NOT permanent caching. To avoid repeated huge downloads, the chosen solution needs an explicitly durable mounted volume, object store or baked and versioned reusable worker image. Compatibility with Hostinger on-demand GPUs and its cost must be confirmed before claiming model weights are reused without redownloading. GitHub Actions artifacts are temporary, expire and are not suitable for checkpoint storage.

## Model choice for initial 5-second scene
- Official code: https://github.com/Wan-Video/Wan2.2 (Apache-2.0 code license; retain notices).
- First model weights: https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B (verify exact revision/license before production).
- Wrapper already in PR #8: scripts/render_wan2_washing_pilot.sh.
- TI2V-5B produces image-to-video shots on a suitable GPU (official docs specify >=24 GB VRAM), not guaranteed Hindi mouth-sync. Audio-driven lip-sync is a separate, unverified stage.
- Pin actual source commit and exact model weight revision/hash before GPU deployment, not a moving main branch.
- The old category registry currently uses category-specific character IDs. Making one pink-kurta woman genuinely identical in all 20 categories will require later harmonizing that registry and visual QA. It is not yet completed.

## What is implemented in this PR
- scripts/package_gpu_job.py: CPU-only verified input bundle builder; explicitly blocks wrong hero SHA or missing images/audio.
- tests/test_gpu_job_package.py: offline bundle tests; no external API, GPU, uploads or charges.
- .github/workflows/washing-gpu-input-preflight.yml: CPU-only workflow that creates a short-lived GitHub artifact containing metadata only. It is NOT a GPU deployment workflow.
- Existing config/pilots/washing-machines.json supplies the 30-second fixed storyboard.

Commands (run from repo root):
    python -m unittest discover -s tests -p test_gpu_job_package.py -v
    python scripts/package_gpu_job.py --plan-only --output output/washing-gpu-plan.json

The plan shows exactly which images and MP3 are still missing. Once each image is approved, its SHA confirmed and the MP3 voice approved:
    python scripts/package_gpu_job.py --asset-root . --audio /secure/approved/washing-hi.mp3 --output output/washing-gpu-job.zip

That ZIP is a portable INPUT, not an MP4 and not a published video. The voice must be generated or supplied separately; this packaging does not synthesize new voice.

## Hostinger API verification status
Official Hostinger documentation currently describes GPU deployment and management in the dashboard, hourly on-demand billing and local disk deletion on destroy. Hostinger's public generic API materials document account/VPS operations, but in this review a public contract for GPU create/delete endpoints was **not verified**. Do not invent endpoints or assume an existing VPS API token supports GPU provisioning. Connecting GitHub to paid GPU requires provider-account capabilities, a secure secret, explicit spending controls, a teardown/failure policy and end-to-end paid-test approval. None is configured here.

References:
- https://www.hostinger.com/support/how-to-set-up-a-gpu-instance-at-hostinger/
- https://www.hostinger.com/support/how-to-choose-a-template-for-your-hostinger-gpu-instance/
- https://www.hostinger.com/support/10840865-what-is-hostinger-api/
- https://docs.github.com/en/actions/tutorials/store-and-share-data

## Outstanding
Persist the approved master/source images; approve a non-robotic Hindi MP3; verify model commercial/license terms and stable weight storage; identify confirmed Hostinger GPU API and billing safeguards; then do a SINGLE isolated GPU render and explicit stop/teardown verification. Social publishing remains OFF.
