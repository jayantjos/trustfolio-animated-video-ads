# Wan2.2 First 5s GPU worker candidate — NOT YET RUN / DO NOT LAUNCH

This is a genuine inference script for the private **5s**, no-dialogue, first-scene **original pink-kurta woman**. It calls pinned official Wan2.2 TI2V-5B `generate.py` with 121 frames, 704x1280, model-offload, and original SHA256-pinned image. It never substitutes a slideshow, talks to social publishers, or claims lip-sync.

- Source artwork on EU-RO-1 network volume: `/workspace/assets/characters/shared/pink_kurta_lady_v1.png` (original SHA256 checked).
- Wan official checkpoint: `/workspace/models/Wan2.2-TI2V-5B/921dbaf3f1674a56f47e83fb80a34bac8a8f203e/`.
- Exact official code Git commit: `1ea34ff48f87168174e12956e200b1d908b1c5ff`.
- Worker Dockerfile: `gpu/Dockerfile.wan5`. This image **has not been built or published as a pinned OCI digest** and has **never been GPU-tested**.
- Output after genuine GPU inference: `/workspace/videos/private-qa/wan5-laundry-first-20261021/scene01.mp4`.
- Written volume receipt: `scene01.receipt.json`; status `VOLUME_MP4_WRITTEN_PENDING_S3_GET_VERIFICATION`. A separate controller MUST download the MP4 back through RunPod S3, verify length + sha256 + 5s duration, and only then call it verified.
- The current approved spend is **$1 for one trial only**; quote at recent preflight $0.89/hr (may change). S3 volume recurring cost is separate. Social publishing OFF.
- CPU unit tests verify command and safety guards only. Wan2.2's official source uses PyTorch SDPA fallback without flash attention, but RTX 4090 performance/memory/driver compatibility remains UNTESTED.
- **Paid Pod launch BLOCKED** until actual worker image is built/published and pinned by digest, provider's per-Pod `terminate-after` is verified on selected creation interface, independent automatic pod reaper is deployed (and not just an alert), price/availability rechecked and one-click run command has fail-safe DELETE + reconcile.
- GitHub Action in this commit is strictly CPU validation. It cannot create billable GPU resources.

RunPod's official CLI docs describe `runpodctl pod create --terminate-after <duration>` but it has NOT been verified in this user's account. REST v2 request currently has no verified native deadline field. Do not assume docs for CLI imply REST field support.

`Wan2.2` generative inference can fail OOM or exceed time cap; no MP4 should be announced until an actual 5s video with artifact hash is verified.
