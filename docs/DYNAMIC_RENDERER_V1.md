# Google Flow 40s dynamic renderer — offline V0.1

This is a working local CPU-only compositor for the user-approved 40-second 360x640 Washing Machine visual master. It is NOT the final live-price publishing system.

Expected exact master file: assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4
Expected SHA256: 2d58880dc27c04c245ff95a10b53ba009538badd04f314062275149c9b5bb48c (4,427,446 bytes).
The actual MP4 BINARY is NOT in GitHub until separately uploaded and verified. The manifest/README is not the MP4.

Usage (offline fixture only):
Install: pip install pillow, and install ffmpeg and Noto Sans Devanagari fonts.
Validate: python -m unittest discover -s tests -p test_dynamic_receipt.py -v
Render: python -m trustfolio_dynamic.render --master assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4 --receipt demo/sample_receipt.json --output output/sample.mp4 --demo

Dynamic windows: 12-20s features, 24-28s budget/brand, 28-32s ranked Top Five, 32-36s two-product comparison cards, 36-40s typographic TrustFolio.in CTA.
DEMO mode adds visible SAMPLE NOT LIVE labels. Never publish the demo.
Receipt must contain mode (budget, brand_budget, comparison), category, budget_inr, optional brand, exactly 5 ranked active in-stock products, fresh live price timestamps and statuses, product titles, brand, prices and verified specifications.
JSON receipt fields alone do NOT independently authenticate actual backend calls. Production adapter must still verify GET /api/products/top + POST /api/live-prices from TrustFolio, in-budget freshness and real availability. No fabricated price or feature data.

Outstanding: actual MP4 upload, trusted live backend adapter, real product image compositing/locked tracking, original TrustFolio logo (prototype only has a typographic wordmark), Hindi audio QA, HD export, publishing release gate. No paid GPU calls or social writes.
