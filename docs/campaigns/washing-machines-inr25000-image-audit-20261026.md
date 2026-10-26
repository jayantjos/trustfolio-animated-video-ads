# TrustFolio ₹25,000 Washing Machine product-photo source QA — 26 October 2026

## Verified source
- Run: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40347129272
- Artifact: https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40347129272/artifacts/12662780277
- Source: exactly ONE read-only `GET /api/products/top?category=washing-machines&budget=25000&limit=5`; **ZERO** `POST /api/live-prices`.
- Source-response SHA256: `6fe47374c6464fec7fbc9a0ec03a1590a9f409cbb466510911dda283f87738f6`.
- Offline tests: **6 pass**. The action successfully completed.
- No paid GPU, no RunPod changes, no publishing, no website/scraper changes.

## Actual ranked website snapshot (website-listed prices; NOT independently verified marketplace-live prices)

| Rank | Website product | Platform | Website-listed price | Candidate image URLs |
| --- | --- | --- | ---: | ---: |
| 1 | IFB 8 kg fully automatic top load, built-in heater | Flipkart | ₹23,500 | 1 |
| 2 | IFB TL801MB1S 8 kg 5-star fully automatic top load | Croma | ₹24,994 | 1 |
| 3 | BOSCH 7 kg fully automatic top load, silver | Flipkart | ₹23,290 | 1 |
| 4 | IFB 8 kg AI-powered top load | Amazon | ₹22,990 | 1 |
| 5 | Whirlpool 7 kg inverter fully automatic front load | Amazon | ₹24,490 | 1 |

**Important:** This snapshot is different from the user's earlier 08:36 IST screenshots and from the 09:00 IST website GET. Do not mix ranks or prices between captures.

## Confirmed blocker
- Rank 1 IFB and rank 3 Bosch have the **exact same retailer image URL** despite being different brands.
- Shared URL: `https://rukminim2.flixcart.com/image/300/300/xif0q/washing-machine-new/d/l/m/-original-imagpqt4zfnsfgnn.jpeg?q=90`.
- Rank 3 Bosch's source record supplies **NO alternate valid retailer image URL**.
- Image swap must not happen merely from another product's photo, a Google Flow hallucination, or a guessed search-result image.
- Earlier image-quality guard PR #14 blocks this source error and remains active.
- New PR #15 added a read-only audit of same-record alternate photo candidates and six offline tests.
- Source mapping must be repaired in the owning TrustFolio product data/database or official retailer product listing **after verifying the correct model and photo**. The animated video repo cannot establish this from the current site API.

## Next safe work
1. Verify product model identity & correct retailer images upstream; preferably put correct unique image in the Bosch source record and revalidate other ranks. Do not touch live-price refresh to repair a picture.
2. Capture ONE fresh website Top 5 receipt; images must match brand/model. Use fresh data as one atomic snapshot only.
3. Produce Flow edit inputs for scenes 04/05/07/08/09 from that single snapshot, preserving premium cinema and character identities.
4. Independently prepare the **Scene 10 TrustFolio CTA** (does not require any product photo); only original logo/verified website URL, no invented labels. Ensure Hindi voice and timing are QA'd.
5. After Flow returns genuine edited 4s clips, verify scene receipts/SHA256 before reassembling; no budget/price live marketing or automatic publishing without fresh valid live-price receipt.

## Safety
The exact original 40-second Google Flow visual master is unchanged. The source-image audit workflow was made manual-only after its first successful run. The 100 GB RunPod network volume and emergency stop safeguards are untouched.
