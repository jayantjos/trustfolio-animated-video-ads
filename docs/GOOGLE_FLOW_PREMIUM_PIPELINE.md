# TrustFolio — Premium Flow Clip Replacement (V1)

**This replaces the rejected cheap overlaid-panel prototype.** It is a manual-approval bridge to edit the *actual premium Google Flow scenes*, using TrustFolio source-verified live product facts and real retailer product images. This is not itself Google Flow automation or a publishing system.

## One-time setup

- Install Python 3.11+, FFmpeg/FFprobe and Pillow (`pip install Pillow`).
- Keep the exact approved 40-second 360×640 master MP4 locally. Never overwrite it.
- CPU-only GitHub workflow `Google Flow Premium Live Product Prompt Pack (Manual Only)` can generate fresh product reference images and prompt text on a selected budget. It uses the same public TrustFolio website `GET /api/products/top` followed by the five IDs in `POST /api/live-prices` (per the existing trustfolio-daily-ads contract).
- One explicit live-price refresh may consume website-side API resources. This workflow is never scheduled; only execute it for a desired campaign.

## Commands

```bash
# Fetch one campaign's real Top-5 and fresh live prices; this makes the 5-ID POST
python -m trustfolio_flow.cli fetch-live --category washing-machines --budget 35000 --output handoff/data/verified_receipt.json

# Generate premium target-edit prompts, download real product image references,
# and split the 40-second original into ten four-second Flow clips.
python -m trustfolio_flow.cli prepare --receipt handoff/data/verified_receipt.json --master visual_master.mp4 --output handoff --download-images
```

If the live API is unavailable, prices stale, product not in stock, Croma/catalog fallback, fewer than five available products or product images unavailable, **abort**. Never fill with test prices or different products. ₹35,000 in the example is **not a campaign selection**—replace it with the target budget.

## Google Flow (Omni Flash)

Google Flow supports editing user-supplied / generated videos: edit each original 4-second scene separately, not the entire 40-second MP4. Google documents selecting at most a 10-second edit segment and uploading an original video no longer than 30 seconds without trimming. From Flow, use Scene 04 (purple girl features), 05 (green boy features), 07 (yellow boy budget), 08 (Top-5 showroom), 09 (comparison), 10 (pink-girl premium CTA). Attach the right `product_images/product_NN.png` ingredients and paste `prompts/scene_NN_*.txt`.

Do **not** draw a fixed text box over the premium background. Instead have Flow render the correct product as part of the studio scene with authentic lighting and beautiful 3D material/podium reflections. Compare the resulting output with the original product photos. Price text, brand spelling and Hindi script from generative video **are not guaranteed exact**; visually QA every number/letter, or reject/regenerate. The actual TrustFolio logo must be the original reference, never invented by a model.

Save clips as `replacements/scene_04.mp4`, `scene_05.mp4`, `scene_07.mp4`, `scene_08.mp4`, `scene_09.mp4`, `scene_10.mp4` (4 s each, vertically framed). Example approval manifest:

```json
{
  "scenes": {
    "8": {
      "sha256": "ACTUAL_SHA256_OF_APPROVED_SCENE_08_MP4",
      "receipt_sha256": "RECEIPT_SNAPSHOT_SHA256_FROM_HANDOFF",
      "character_ok": true,
      "visual_quality_ok": true,
      "product_match_ok": true,
      "facts_text_ok": true,
      "hindi_audio_ok": true,
      "continuity_ok": true
    }
  }
}
```

Populate this for **all six** dynamic scenes only after inspecting the MP4 itself. A hash copied from a prompt or fixture is **not** an approval. AI-generated videos can vary; human QA remains necessary.

```bash
python -m trustfolio_flow.cli assemble \
  --master visual_master.mp4 --handoff handoff \
  --replacements replacements --approvals approvals.json \
  --output premium_review_only.mp4
```

The assembler: (1) checks the exact receipt source hash and clip SHA256; (2) checks six explicit human QA decisions; (3) preserves untouched original scenes 1/2/3/6; (4) splices six *Flow-generated* 4-second clips, normalizes audio/video and produces a 40-second MP4; (5) never draws product graphics on top of the original video. Failed/missing approvals or wrong file size → no output. Output contains a receipt `.json` that says it is a **visual review**, not live-price-certified for publishing.

**Critical limitation:** A price captured while editing is no longer guaranteed live when a video is published hours later. Trigger a fresh five-ID price recheck immediately before publishing and withhold ad on price/availability/rank differences. There is NO automatic publishing path here.

## Safety / scope

- No RunPod calls, no new GPU charges, no Meta / YouTube publishing, no app repository changes.
- Existing user-approved 40-second story is untouched. 360p source is not HD.
- Google Flow edit calls must be made in Google Flow UI; ChatGPT/GitHub integration here only prepares trusted prompts and assembles user-approved exported clips.
- This is intended for **Budget, Budget + Brand, Comparison** based on real backend response, and supports one category/budget per freshly verified prompt pack. Brand variants require separate source selection/Flow generation.
