# V10 — Fixed Specifications, Original Character Audio and Reusable Hindi Voice Model

User-reported issue: specifications shake / do not line up when cartoon characters gesture; V9 offline Hindi eSpeak product narration is hard to understand.

## Correct root cause and tested output

Old local `build_v9_room_match.py` animated each STILL product/spec frame by moving the video crop every frame with `sin(n/35)` and `cos(n/37)`. In addition, prior 0–28s graphics were already baked onto V8 animated source. This produced visible jitter and detached lettering.

V10 rebuild uses the **original clean 40-second Flow master** for 0–28s, static warm-gold transparent text layers at 12–16s, 16–20s, and 24–28s, and still source product visuals for 28–86s with **NO animated crop/pan/zoom**. The original Pink Girl CTA remains 86–90s. `trustfolio_flow/v10_stable_specs.py` provides the repeatable 4-spec generator from current live Top5.

Local V10 QA preview (not GitHub binary): `TrustFolio_V10_90s_FIXED_SPECIFICATIONS_Original_Cartoon_Audio_REVIEW_ONLY.mp4`
- SHA256: `06700ae0ca949d99739dce01119c10e143d797a527a63c9ce8da796d894445d3`
- 90.000 seconds, 720×1280, H.264 + AAC 48kHz
- 37.5s vs 38.0s product-detail frames: average absolute per-channel pixel difference 0.003 (codec noise only), compared with prior intentional oscillating crop.
- Product prices are from the **28 Oct 2026 historical snapshot**, NOT necessarily live today; the source IFB/Bosch photo approvals remain blocked. Preview MUST NOT be published.

## Original character voices vs new dynamic speech

0–28s and 86–90s preserve original cartoon character soundtrack. **Do not reuse eSpeak Hindi** (too robotic). The new approved voice cannot be synthesized by replaying recorded character lines: an actual speech model or a user-owned voice clone and clean voice reference is needed.

The V10 provider profile at `masters/washing-machines/v10_voice_profile.json` pins:
- provider `inworld` (API hosted outside GitHub),
- model `inworld-tts-2` supporting Hindi,
- provisional preset `Ashley` (voice ID stays stable across generations),
- `approved_for_hindi_narration: false` **until actual Hindi sample is audible and accepted**.
- Only the chosen voice ID and script/code belong in GitHub; provider weights, billing key and private voice recordings DO NOT.

Official Inworld TTS API is `POST https://api.inworld.ai/tts/v1/voice` with fields `modelId`, `voiceId`, `text`, and Base64 `audioContent`. See https://docs.inworld.ai/api-reference/ttsAPI/texttospeech/synthesize-speech for current provider documentation. An Inworld account/API key is separate from existing Higgsfield, Runway or ChatGPT access.

### One-time voice listening sample

1. GitHub video repo → Settings → Secrets and Variables → Actions. Add secret `TF_VIDEO_INWORLD_API_KEY` with the Inworld *Basic Base64 credential*; never paste in a chat or commit.
2. Enable Action Variable `TF_VIDEO_VOICE_AUDITION_APPROVED=true` to authorize **one small billable sample**.
3. Actions → `V10 Hindi voice model ONE sample for listening - explicit manual only` → Run workflow. Download `TrustFolio_V10_Hindi_Narrator_Preview_NOT_APPROVED.mp3` and listen to Hindi pronunciation.
4. Approve or change voice ID. If good, update `v10_voice_profile.json`: `approved_for_hindi_narration=true` plus actual sample's SHA256 evidence, with reviewed GitHub PR. Do not auto-approve a voice for all 20 categories.
5. Only AFTER source model photos are accurately repaired and approved, turn `TF_VIDEO_HINDI_VOICE_TEMPLATE_APPROVED=true`, `TF_VIDEO_V10_VOICE_AUTO_ENABLED=true` for recurring **voice handoff only**. The voice workflow performs exact five current live price checks and source photo checks BEFORE any paid voice request.
6. It then builds five dynamically source-backed Hindi lines, one **fixed 10s natural-speaking chapter per ranked product** (32–82s). No audio time stretching. It produces `50-second` voice WAV and receipt artifacts tagged by snapshot SHA256.
7. A genuine 90s current-live video render must be rebuilt from the fresh photo/data receipt, then merged via `v10_fixed_voice.mix` with the original character audio. Check Hindi pronunciation, model-image accuracy, loudness, video timing and SHA. At posting time recheck live prices/ranks and do not post stale historical video.

### About SAME cartoon character voice

A generic TTS preset, even a good Hindi one, is a **separate narrator** — it is NOT guaranteed to match the exact Flow character voice. To speak *new words in the exact cartoon voice*, use the user's original Google Flow character voice model/project, or an authorized clean same-speaker voice sample with a cloning provider. Do not automatically scrape, extract multi-character/mixed music audio and call it a trained voice model.

## Safety and current status

- Higgsfield `seed_audio` short sample was attempted on 28 Oct and rejected **Out of credits**; NO new TTS audio was created.
- Runway connected workspace had **no enabled speech generation models**. No model download or unauthorized paid audio was created.
- New Inworld voice model **not auditioned / not configured with API key yet**; therefore V10 preview carries only the original cartoon speech and ambience.
- `v10-dynamic-fixed-voice-handoff.yml` is installed but OFF until explicit user approvals and photo source repair; separate existing poster/image-post cron and the older 54s pipeline untouched.
- `v10-first-voice-audition.yml` is manual-only. No video has been posted by this work.
- This repository cannot be used as permanent storage for proprietary voice-model weights; versioned vendor voice ID/configuration gives repeatable identity.

Next step after audition: production dynamic 90s video renderer, model-photo QA, real voice sound QA, live-price prepublish recheck, one manually approved Instagram/Facebook Reel.
