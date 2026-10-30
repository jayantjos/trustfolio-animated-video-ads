# TrustFolio FINAL approved assets rebuild (migration branch)

**Only approved source:** `assets/video/washing-machines/complete washing machine.zip` and `TrustFolio_Washing_Machine_Master_Kit.zip`. Do not silently use removed 40-second V1, V6, V8, V10 or Wan-generated media.

## Current implementation
- `scripts/audit_assets.py`: verifies both archives, ZIP CRC, source SHA, paths and inventory.
- `final-master-assets-qa.yml`: manual / source-change audit, **no social publishing**.
- Original spoken audio is an immutable character reference. It does not make new product names speak dynamically.
- Exact product photo, live price, four source-backed specs, script, consistent authorized TTS voice and audio-driven lips all require independent render and QA before first publish.
- Never place static product names or prices in final visual masters. Only render verified live JSON at publish-time; fail closed if fewer than five eligible products.
- Play Store QR must be a real static overlay and tested from actual output frames.

## Migration safety
This is a new branch; legacy workflows on `main` remain untouched until replacement is tested. Do not turn on `TF_VIDEO_REELS_AUTO_ENABLED` or `TF_VIDEO_REELS_PUBLISH_ENABLED` yet. Legacy workflow paths will be removed from this branch after dependency audit and a working replacement renderer exists. Existing daily image ads repository is out of scope.

## Roadmap
1. Source ZIP audit.
2. Strict live API ranked Top 5 receipt for `budget` and `brand_budget` with freshness and availability.
3. Product-image replacement + four specifications.
4. Voice reference QA, consistent synthesis and cartoon lip-sync.
5. Render and QR scan QA.
6. Explicit pilot publish after successful release gates.
