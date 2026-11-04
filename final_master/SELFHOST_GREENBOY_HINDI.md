# TrustFolio self-hosted Green Boy Hindi voice — first real test

This changes **only voice**. It does not regenerate any animated video, replace original music, or assert lip-sync.

Official engine: [Resemble Chatterbox](https://github.com/resemble-ai/chatterbox) Multilingual V3, Hindi (hi), MIT open-source. Use ONLY the approved repo reference `assets/video/washing-machines/original_greenboy_reference.wav`. No Higgsfield API key or per-clip generation credits.

1. On an isolated **GPU** machine with CUDA drivers, Python 3.11 and sufficient VRAM, run:
   ```bash
   python3.11 -m venv .venv-tts
   source .venv-tts/bin/activate
   python -m pip install --upgrade pip
   python -m pip install chatterbox-tts
   ```
2. Obtain **fresh verified** top-five TrustFolio receipt using the project's existing live receipt fetch; then generate five dialogue rows:
   ```bash
   python -m final_master.scripts.dialogues --receipt /secure/fresh_receipt.json --out /tmp/greenboy_dialogues.json
   ```
3. Render just ONE voice test:
   ```bash
   python -m final_master.scripts.selfhost_voice --dialogues /tmp/greenboy_dialogues.json --outdir /tmp/greenboy_sample --rank 1 --device cuda
   ```
4. Listen to `rank_01.wav`; compare with the approved original, pronounce IFB/specs, and confirm speech fits 10s. The JSON sidecar deliberately says `voice_approved: false`. **Do not approve automatically.**
5. Once approved, regenerate using a fresh receipt, run ranks 2–5 separately; follow with separately verified mouth-only lip sync and original 90s video composition.

Hardware and expense: no provider credits, but GPU rental or electricity is not free. Ordinary CPU-only VPS may be too slow or have insufficient RAM. No billable GPU Pod launched in this change. No auto-social publishing from this branch.

Important: Chatterbox can sound *similar* to the supplied reference, not guaranteed identical. Verify model version compatibility and test output pronunciation/voice by listening.
