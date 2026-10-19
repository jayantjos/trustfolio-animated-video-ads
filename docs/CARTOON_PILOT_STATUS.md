# Cartoon pilot implementation — evidence and production boundary

Implemented on the existing draft PR #1 feature branch. No website, database,
scraper, Android, old ad schedule, Meta or YouTube account was modified.

## Actual implementation

- `trustfolio_video/demo.py`: verifies the original signed/hashed historical
  TrustFolio Top-5 JSON snapshots, product IDs, rank order, category, brand,
  budget, stock, HTTPS image provenance and the explicit demo-only state.
  It never calls the live production validator as a shortcut or re-ranks.
- `trustfolio_video/cartoon.py`: CPU-based layered photo characters with
  independent bouncing eyes, mouth, arms, legs, friend interactions and three
  distinctive world backgrounds (Bubble Laundry, Neon City, Beat Street).
  Preserves five actual retailer product photos per pilot when downloadable.
- Speech: offline `espeak` synthesizer called as a separate executable, with
  two English/Indian-style character-voice variants reading original romanized
  Hinglish lines. Speech quality is robotic and NOT yet approved as natural
  Indian conversational voice. Devanagari/native Hindi language packs remain
  an unsolved production task.
- Music/SFX: original, procedurally synthesized simple soundtrack with
  scene-triggered pops, no downloaded copyrighted songs or sound samples.
- Composition: FFmpeg raw frame pipeline to genuine 1080x1920 H.264 MP4/AAC.
- Existing `trustfolio_video/storyboard.py` supplies scene timings and
  rank/product identity for final rendering and stored `.storyboard.json`.
- Each video has immutable product IDs, original price evidence, separate
  `.qa.json`, selected source photos and SHA256, and inspected preview frames.

## Three pilot outputs

1. `washing-machines-demo.mp4` — historical ₹35,000 budget campaign, Bubble Laundry.
2. `samsung-smartphones-demo.mp4` — historical ₹20,000 Samsung brand-budget campaign, Neon City.
3. `earbuds-comparison-demo.mp4` — historical ₹3,000 comparison campaign, Beat Street.

The 15-second output is 1080×1920 24fps H.264/AAC, with a permanent
`DEMO - NOT FOR PUBLICATION` watermark and a disclaimer that historical
prices require current verification.

The original retailer images were retrieved only for private QA; their
third-party advertising/commercial reuse rights are **not verified**.
The banner uses a text wordmark, NOT a proven approved official vector logo.
Never remove the watermark or publish these videos as ads.

## Model / source provenance and licensing constraints

- `espeak` or `espeak-ng`: open-source offline TTS, GPL-family licensed;
  provenance: https://github.com/espeak-ng/espeak-ng. Executed externally,
  not embedded or redistributed in the GitHub source repository. License
  compliance must be separately reviewed before production distribution.
- FFmpeg: https://ffmpeg.org/legal.html — LGPL/GPL build-specific conditions;
  `libx264` brings GPL obligations for a built binary. The workflow installs
  or uses stock runner tools, does not distribute encoder binaries.
- Pillow and NumPy: pinned runner dependencies and normal open-source licenses.
- Images: media.tatacroma.com / Amazon / Flipkart snapshot-derived URLs, only
  from an allowlisted HTTPS host, size-limited, no tracking of user data.
- Sound effects/music: original procedural source code, no third-party clips.
- Fonts: system DejaVu / Liberation fonts with their respective licenses.
- **No external generative model checkpoints installed**. Natural Indian
  Hindi/Hinglish voices and polished cartoon style still need model review,
  benchmark, licensing and human listening.

## Explicit gates and known blockers

Production campaign validation remains strict in
`trustfolio_video/contract.py`, requiring evidence for all five recent
retailer checks. The recorded pilot set lacks all fifteen per-product
timestamps; six rows used catalog fallback. Demo validation does not alter
this requirement.

The output is **NOT production-approved**:
- Raw eSpeak Hinglish quality can sound artificial.
- Character movement and mouth shapes are basic procedural animation, not
  phoneme-accurate lip sync.
- Only three pilot categories currently have actual rendered world presets;
  the other seventeen enabled categories have storyboard worlds/config and
  distinct reviewed drafts, NOT independent render-ready environments.
- Indian Hindi and English language packs, official logo, commercial asset
  rights, narration human QA, accessibility, and platform-specific publishing
  adapters remain outstanding.
- Visual frame inspection can reveal layout problems despite tests passing;
  do not claim human creative approval solely because FFprobe or tests pass.
- 10 additional category slots remain disabled until supported by backend.

All video artifacts are kept in Actions for QA only. **No upload, scheduling
or publication to Instagram, Facebook, YouTube, LinkedIn or X is implemented
or enabled in this repository.**

## Reproducibility

Install FFmpeg/FFprobe, eSpeak, Python 3.11+, Pillow and NumPy, then:

```sh
python -m unittest discover -s tests -v
python -m trustfolio_video.cartoon \
  --snapshot evidence/washing-machines-snapshot.json \
  --output output/washing-machines-demo.mp4 --duration 15
```

Inspect the MP4, accompanying source-bound `.qa.json`,
`.storyboard.json`, `.preview.png` and GitHub Actions 1, 6 and 12 second
frames. The generated outputs belong in QA artifacts, not Git commits.

## Safe next production milestones

1. Resolve freshness/provenance with a separately reviewed website API
   contract change, without guessing timestamps.
2. License official TrustFolio vector logo and retailer image advertising use.
3. Evaluate and test commercial-usable natural Hindi/Hinglish character voices.
4. Improve 2D photo rigs, polish design/camera timing, add phoneme lip sync.
5. Implement the remaining 17 unique visual category worlds and proper
   language packs; keep ten unverified backend slots disabled.
6. Human visual and audio sign-off on several categories and ad modes.
7. Only after user approval, implement new-repo-only official publishing
   adapters and credentials. Never touch existing scheduled image campaigns.
