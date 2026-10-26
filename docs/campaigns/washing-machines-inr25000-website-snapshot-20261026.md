# Washing Machines ₹25,000 — website snapshot and product-photo QA (2026-10-26)

**Source run:** https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/40264416408

**Result:** Successful website-only Top-5 GET, exactly five source product images fetched, and premium Flow edit prompts assembled. ZERO POST /api/live-prices calls. This is an **unpublished preview source**—not a verified-live price campaign.

## Same user screenshots vs later website response

User screenshot ~08:36 IST:
1. IFB (Flipkart) ₹23,500
2. IFB (Croma) ₹24,994
3. Samsung (Amazon) ₹20,990
4. Bosch (Flipkart) ₹23,290
5. Whirlpool (Amazon) ₹23,090

Website GET run 03:30 UTC (=09:00 IST):
1. IFB 8 kg (Flipkart) ₹23,500
2. IFB 8 kg (Croma) ₹24,994
3. Bosch 7 kg (Flipkart) ₹23,290
4. IFB 8 kg (Amazon) ₹22,990
5. Samsung 8 kg (Croma) ₹23,590

The two are DISTINCT Top-5 snapshots. Do not splice rank/image/name/price from one snapshot into the other, and do not call a website catalog price "Live" without independent successful live verification.

## Critical product photo blocker

The downloaded retailer source image for rank 1 IFB and rank 3 Bosch was **exactly the same Flipkart URL and exact same bytes**.

- Image: https://rukminim2.flixcart.com/image/300/300/xif0q/washing-machine-new/d/l/m/-original-imagpqt4zfnsfgnn.jpeg?q=90
- SHA256 of processed product_01.png and product_03.png: d087441a333a0bf4657059f6c4ab104c4c9f15ec36c74239f921273f1e453037
- Root-cause implication: wrong/reused product image already supplied by website API; NOT a mistake caused by Google's video model.
- Some photos were low-resolution (Flipkart 300x300, Amazon portrait height 218px) and insufficient for reliable premium HD.
- New guard PR #14 merged: https://github.com/jayantjos/trustfolio-animated-video-ads/pull/14 . URL and decoded byte SHA cross-brand reuse blocks Flow image ingredient generation.

**DO NOT** generate a premium Bosch clip from IFB imagery. Fix original source product image mapping/photography, verify model/title and source photo visually, then create a fresh snapshot/edit pack. Video repo changes do NOT modify user website, scraper or MongoDB.

## Safety and project status

The original 40-second master is unchanged and remains 360p. No new Google Flow edit clip or final master was generated. No paid GPU, RunPod Pod, Meta posting, or website app changes. The one-time GET workflow is now manual-only. Strict marketplace live-price refresh must independently succeed before marketing as live-priced.
