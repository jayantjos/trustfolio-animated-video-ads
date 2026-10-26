# TrustFolio Animated Ads — clean Google Flow master

**Status:** Visual master V1 prepared locally; binary MP4 upload pending. NOT a final ad, NOT published. Dynamic renderer has NOT been implemented on this branch.

Lean, non-GPU-rendering starting point for the user-approved 40-second vertical Washing Machine video created using Google Flow. Historical WAN2.2 experiments remain in untouched branches. The **existing emergency stop / independent GPU Pod reaper safety workflows, their scripts and tests are intentionally retained**; do not remove them without verifying no active Pods or operational dependencies.

## Visual master
- Category: Washing Machines; 10 × 4 seconds = 40 seconds
- Source: `TrustFolio_40s_Reordered_Preview(1).mp4` (visual preview, not branded final)
- GitHub target: `assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4`
- Expected SHA256: `2d58880dc27c04c245ff95a10b53ba009538badd04f314062275149c9b5bb48c` (4,427,446 bytes)
- Native: 360×640 H.264/AAC MP4, NOT HD
- Shot order, dynamic slots: [manifest](masters/washing-machines/manifest.json)

**A manifest or commit does not prove the MP4 binary is uploaded.** After upload run `python scripts/verify_master.py`.

## Still to implement
1. Upload exact MP4 and SHA256-verify it.
2. Hindi dialogue and lip-sync QA; character/room continuity.
3. Original TrustFolio logo, `TrustFolio.in` URL and final CTA overlay.
4. Backend data: `GET /api/products/top`, `POST /api/live-prices`, Budget / Budget+Brand / Comparison, verified price/stock/specs; fail closed.
5. Motion-stable dynamic compositing, Hindi voice and HD export.
6. Review before any publishing.

**Safety:** No paid GPU inference, no automatic social publishing, no VPS changes, no TrustFolio app repo changes. See [legacy recovery](docs/LEGACY_ARCHIVE.md).
