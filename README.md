# TrustFolio Animated Ads — clean Google Flow master

**Status:** Visual master V1 prepared locally; binary MP4 upload pending. NOT a final ad, NOT published. Dynamic renderer has NOT been implemented on this branch.

This is a clean, non-GPU production starting point for the user-approved 40-second, vertical Washing Machine video created using Google Flow. It keeps the previous GPU research accessible through untouched legacy branches and a backup branch, but deliberately excludes billable RunPod workflows and legacy WAN test orchestration from this CLEAN branch.

## First visual master

- Category: Washing Machines
- Timeline: 10 × 4 seconds = 40 seconds
- Source approved for *visual reference*, not yet final publish-ready: `TrustFolio_40s_Reordered_Preview(1).mp4`
- GitHub upload destination: `assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4`
- Expected SHA256: `2d58880dc27c04c245ff95a10b53ba009538badd04f314062275149c9b5bb48c`
- Expected size: `4427446` bytes
- Native: 360×640 H.264/AAC MP4; 360p preview, NOT HD.
- Metadata, shot order and planned dynamic slots: [manifest.json](masters/washing-machines/manifest.json)

**Do not treat a manifest or GitHub commit as proof the MP4 was uploaded.** Check the actual repository path and its SHA256. To validate: `python scripts/verify_master.py` after the MP4 is uploaded.

## Next milestones (not implemented yet)

1. Upload exact original MP4 binary to the path above and validate its SHA256.
2. QA Hindi dialogue/lip-sync and improve continuity.
3. Add original TrustFolio logo, accurate `TrustFolio.in` URL, slogan and CTA as deterministic overlays.
4. Implement backend data contract: GET /api/products/top and POST /api/live-prices, with budget/brand/comparison modes and verified price/status checks. Only show eligible in-budget, available products and supported specifications. Add fail-closed behavior; no fabricated prices, savings, or product features.
5. Implement motion-stable dynamic overlays, Hindi voice and 1080×1920 export and test with fixture data.
6. Get review before allowing any scheduler or publishing integration.

**Safety:** No paid GPU runs, no automatic publishing, no VPS changes, and no alteration of the TrustFolio app repo. See [Legacy Archive](docs/LEGACY_ARCHIVE.md).
