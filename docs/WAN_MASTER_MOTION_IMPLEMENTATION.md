# TrustFolio Master Theme: original character animation pilot

**Status: working asset-preparation code and GPU render adapter, NOT actual Wan video inference.**

The approved creative truth is the user's tropical/cinematic cartoon lady in pink
kurta and five distinct washing-machine characters, with the full-color
purple/yellow TrustFolio brand. Do not substitute low-poly boxes, generic
cartoons, static card zoom, fake brands, unverified prices, or arbitrary ranks.

## What is now implemented

- `trustfolio_video/wan_master_pilot.py`: two real reference crops from the
  user's uploaded approved cartoon paintings. Input PNG hashes are locked.
- Model plan: locally installed **Wan2.2-TI2V-5B** source revision
  `1ea34ff48f87168174e12956e200b1d908b1c5ff`,
  using the official upstream image-to-video CLI in *two separate shots*.
- GPU gate: at least 24 GB CUDA VRAM and already-installed auditable
  weights. No silent downloads, installing external shell scripts or paid APIs.
- After real inference: SHA and codec/duration evidence, source-identity
  review **still mandatory**. No publish adapter.
- `tests/test_wan_master_pilot.py`: checks exact reference hashes,
  misidentification/source tampering, no GPU/model fallbacks, frame dimensions,
  missing assets and never-publish flags.
- `.github/workflows/wan-master-preflight.yml`: CPU-safe technical readiness
  report. It explicitly does NOT run Wan or produce a fake MP4.

## Approved original source art SHA256

| Art | Source original SHA256 |
| --- | --- |
| Approved 30s washing storyboard design | `c5ce062090f34ab414a125d91c3ad39ff81f37a8ad4e629726e5ced0f3458ba1` |
| Lady in pink from approved washing-comedy storyboard image | `2a2af14bae1c5c3f49cec647b1d67b1016e01db98a48ed54374bcdd56d642a1e` |
| Tropical five washer friends scene | `bcc90bf85a9c2f4fee8b57b0c02b78e5b80f4c8a184b5d528ccb21a1ca934e0c` |

Original artwork is supplied in the conversation and is **not committed** as
binary assets into this GitHub source branch. Prepared references live in the
conversation downloadable private bundle, not in the Actions runner.
A GPU worker must have these same SHA-locked files and audited weights before
an image-to-video inference can begin. Neither GPU availability nor approval
of paid GPU cost can be inferred from GitHub's green CPU tests.

## Proof commands (private only; no social/video API writes)

```bash
python -m trustfolio_video.wan_master_pilot --action check
python -m trustfolio_video.wan_master_pilot --action prepare \
  --lady-art path/to/trustfolio_washing_machine_showdown.png \
  --machine-art path/to/trustfolio_s_tropical_washing_machine_parade.png \
  --master-art path/to/trustfolio_s_top_5_washing_machines.png \
  --output-dir work/character_refs

# Only on an already authorized CUDA GPU machine, with 24GB+ VRAM,
# exact upstream Git commit, preinstalled model and verified sources:
python -m trustfolio_video.wan_master_pilot --action render \
  --manifest-dir work/character_refs \
  --wan-dir path/to/pinned/Wan2.2 \
  --weights-dir path/to/audited/Wan2.2-TI2V-5B \
  --output-dir work/private-mp4s --allow-local-gpu
```

**No such GPU render has been claimed.** This is setup and a gated
inference implementation, not a completion certificate.

## Why the alternative tools cannot directly deliver this

- **Wan2.2-Animate-14B** copies motion from a driving video and needs an
  appropriate pose/face source, which our nonhuman washers do not yet have.
  The more practical first experiment is source-image-guided TI2V-5B
  (24GB+ GPU); test for drift in accessories, faces and appliance body.
- **LivePortrait** code is MIT, but upstream's default InsightFace models
  are for noncommercial research. Its default detector weights must NOT
  be used for commercial TrustFolio ads; it also does not rig whole bodies.
- **MoneyPrinterTurbo** can assemble licensed video clips, voice, captions and
  music, but cannot by itself create real facial/arm/body performance from
  the supplied still. Its stock/pricing/editor features are not an
  authorization to publish.
- **CPU image cutout animation** was tested as a rejected technical
  experiment: visual halos, quality drift and unconvincing limbs/mouth.
  It must not be presented as passing the approved 3D movie master.

## Acceptance gates before the first publishable 30s Washing Machine ad

1. Two coherent, identity-matched **real** 3–5s GPU-rendered Master-Theme
   character clips with verified model/source receipts.
2. The **cartoon woman talks**, eyes blink, hair and hands respond naturally.
3. Actual washing-machine model characters turn, move their articulated
   hands/feet, blink, react to one another, mouths match Hindi voice timing.
4. Scene-to-scene consistency, no disappearing parts, no text distortion,
   no visual mismatch from supplied master approved art.
5. 30s full-HD picture editing, convincing sound design and native-reviewed
   Hindi/Hinglish conversation, rank #5 to #1, branded CTA.
6. Original official TrustFolio logo provenance, commercial art/voice/music
   rights and per-product live price evidence; rankings remain backend-owned.
7. Owner creative review; even then publishing remains OFF until authorized.

**Do not edit website, app, MongoDB, static-image ads or existing publishing.**
