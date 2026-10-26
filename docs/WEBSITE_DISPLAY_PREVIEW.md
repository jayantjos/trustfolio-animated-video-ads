# TrustFolio website-display price parity — preview only

**Goal:** Premium Google Flow scenes reuse the exact five products in TrustFolio website Top-5. No cheap 2D dashboard overlays.

## Why website-display is different from live-marketplace verification

Earlier strict ₹25,000 live-price verification failed:
- Rank 1 Flipkart: live ok
- Rank 2 Croma: missing_live
- Rank 3 Amazon: blocked
- Rank 4 Flipkart: live ok
- Rank 5 Amazon: blocked

User's TrustFolio screenshots (around 08:36 IST) show:
1. IFB 8 kg (Flipkart): ₹23,500
2. IFB 8 kg (Croma): ₹24,994
3. Samsung 8 kg (Amazon): ₹20,990
4. Bosch 7 kg (Flipkart): ₹23,290
5. Whirlpool 7.5 kg (Amazon): ₹23,090

**Critical:** Earlier backend diagnostic ranked Voltas Beko at #4 instead of Bosch. Those are different snapshots! Never mix ranks/product names/prices across snapshots. The new GitHub workflow writes a screenshot_parity.json file comparing the **new single website GET** with the user-supplied screenshot.

## Trust policy

Use the command:

    python -m trustfolio_flow.cli fetch-website-display --category washing-machines --budget 25000 --output handoff/data/verified_receipt.json

- Makes ONE read-only website Top-5 GET with category and budget, ZERO POST /api/live-prices calls.
- Preserves original product rank, ID, name, brand, platform, listed price, listed specs and retailer image reference.
- Rejects duplicates, over-budget prices, malformed ranking, bad retailer image URL, wrong brand and explicitly unavailable products.
- Emits source=trustfolio_website_display, pricing_verification=WEBSITE_LISTED_ONLY, publishable=false, and product live_price_status=not_verified_for_video.
- A price from website GET is **not** independently confirmed as current marketplace price—even when a website screenshot displays a green Live badge. Never copy the Live badge without specific freshness evidence.
- Human review MUST verify product-title/photo correspondence: screenshots include top-load listings with apparently front-load-looking product photos. Do not promise attributes contradicted by the actual product.

## Premium Google Flow shots

After capturing source data, the original Google Flow scenes 04, 05, 07, 08, 09 and 10 receive premium reference-photo editing prompts. Source image ingredients come from the exact ranked product retailer URLs. Original characters, room, podium, scene timing, Hindi dialogue and premium style remain unchanged except user-approved product-specific edits.

GitHub cannot automatically edit the video in Google Flow. Export the approved 4-second Flow clips, check original product appearance, every INR price, Hindi words, characters and transitions; then the assembler verifies exact SHA256 and produces a 40-second **unpublished visual review**, never a live-price-certified ad.

## Publishing and safety

- Strict fetch-live remains unchanged: any catalog-only/missing/blocked current marketplace price still blocks verified-live campaigns.
- Website-display receipt is for unpublished preview only; never call it live-verified or publishable.
- Reverify all five current marketplace prices, availability and ranks before publishing a price ad, otherwise withhold.
- No TrustFolio app repository, database, VPS, GPU Pod, preserved 100GB volume or social publisher changes.
