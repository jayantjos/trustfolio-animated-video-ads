# Washing Machine ₹25,000 — Scene 8 CPU compositing milestone (27 Oct 2026)

## What is actually completed
- User-approved original Flow master remains unchanged: 40.0s 360x640 MP4, SHA256 2d58880dc27c04c245ff95a10b53ba009538badd04f314062275149c9b5bb48c.
- A local 4-second Scene 8 visual-QA MP4 (720x1280 upscaled) was produced using source-ranked product photos and candidate corrections on the original three physical purple-gold podiums. Ranks 1/2/3 are revealed first; 4/5 replace the two side stages later.
- A 40-second preview with only Scene 8 replaced was produced locally; the other nine scenes remain the original user-approved animation with original audio.
- These **preview MP4 binaries exist as conversation download artifacts, not in the GitHub repository**. They are not the final branded/publish-ready video.
- Reusable source renderer: scripts/render_washing_scene08_cpu_preview.py (CPU only); CI confirmed master hash and price/image guards PASS: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40414831764

## Atomic historical website source (2026-10-26 09:00 IST)
| Rank | Product identity | Website-listed price | QA photo provenance |
|---|---|---:|---|
| 1 | IFB TL800EP1S 8kg top load | ₹23,500 | exact-model external retailer photo **candidate**, not publication-approved |
| 2 | IFB TL801MB1S 8kg top load Croma | ₹24,994 | source Croma |
| 3 | Bosch WOE703S0IN 7kg top load | ₹23,290 | exact-model external retailer photo **candidate**, not publication-approved |
| 4 | IFB TL801MG1ID 8kg top load Amazon | ₹22,990 | source Amazon (low resolution) |
| 5 | Samsung WA80F08E2BTL 8kg Croma | ₹23,590 | source Croma |

Website source rank1 IFB and rank3 Bosch have exactly the same **wrong front-load** source image despite top-load model listings. The actual TrustFolio database has NOT been corrected; do not treat the external model-specific QA candidates as updated source data. Scraper issue: https://github.com/jayantjos/trustfolio-scraper/issues/1
Retailer/OEM model identity evidence:
- IFB exact Flipkart listing: https://www.flipkart.com/ifb-8-kg-fully-automatic-top-load-washing-machine-in-built-heater-multicolor/p/itmdcb1d4a483e0f
- Bosch exact Flipkart listing: https://www.flipkart.com/bosch-7-kg-fully-automatic-top-load-washing-machine-silver/p/itmb2095ceaccf06
- Candidate photo download QA run: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40412420954

## Preview renderer usage
Install FFmpeg, fonts, Pillow, numpy, opencv-python-headless. Provide the verified user-approved 40s master, ONE immutable website receipt JSON and five local model-reviewed photos rank_01.png ... rank_05.png. Run:

    python scripts/render_washing_scene08_cpu_preview.py --master assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4 --receipt receipt.json --photos reviewed_photos --output scene08_preview.mp4 --allow-model-photo-candidates

That override flag only permits an **unreleased visual QA preview** of explicitly unresolved bad source images; it never authorizes publication. All output prices are website-listed historical values, NOT independently live-verified. No current-live badges.

## Still required for a finished video
1. Fix source product image mapping upstream and confirm usage rights/model accuracy, improve blurry #4.
2. Fresh same-snapshot Top 5 and independent actual live prices/availability for all five products before ad publication. Do not mix rankings from multiple captures.
3. Improve material integration/occlusion beyond this 2D photo-cutout proof, then Scenes 4/5 feature integration, Scene 7 budget, Scene 9 exact two-product compare, Scene 10 official TrustFolio logo and Hindi CTA, audio continuity QA.
4. Approval gates and final automated 40-second render. No social posting until strict verification passes.

Safety: No RunPod/GPU job, no paid Google Flow edit, no social publishing, no app repo/VPS/DB changes. Old rejected sample MP4 removed from current main; correct premium master remains verified.