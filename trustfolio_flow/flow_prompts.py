"""Create product-grounded Google Flow EDIT prompts, never rectangle-overlay renders."""
from pathlib import Path
import json
import re
from .live import canonical, sha, DataBlocked
from .site_display import check_flow_receipt, SOURCE as WEBSITE_DISPLAY_SOURCE

DYNAMIC = (4, 5, 7, 8, 9, 10)
SCENE_NAMES = {4:"purple_girl_features",5:"green_boy_features",7:"yellow_boy_budget",
               8:"premium_top5_podium",9:"premium_two_product_comparison",10:"trustfolio_premium_cta"}
SCENE_TIME = {n:((n-1)*4,n*4) for n in range(1,11)}


def money(v):
    from .live import amount
    return "₹"+f"{amount(v):,.0f}"


def fact(p, limit=2):
    specs=p.get("specifications") or {}
    return list(specs.items())[:limit]


def fline(p, *, i=None):
    rank = p['rank'] if i is None else i
    return (f"RANK #{rank}: EXACT SOURCE PRODUCT: {p['title']} | "+
            f"BRAND: {p['brand']} | {'WEBSITE-LISTED PRICE (NOT LIVE VERIFIED)' if p.get('price_source')=='website_displayed_price' else 'VERIFIED CURRENT PRICE'}: {money(p['price_inr'])} | "+
            f"SOURCE REFERENCE IMAGE: product_{rank:02d}.png | "+
            f"{'WEBSITE-LISTED SPECS (VERIFY MODEL/IMAGE MATCH)' if p.get('price_source')=='website_displayed_price' else 'VERIFIED SOURCE SPECS'}: "+ ("; ".join(f"{k}: {v}" for k,v in fact(p,3)) or "No listed specs"))


def prompt_for(scene,receipt):
    p=receipt['products']
    # This wording prioritizes product staging in Flow over cheap 2D card boxes.
    common=(
        "EDIT THE ATTACHED FOUR-SECOND ORIGINAL GOOGLE FLOW VIDEO CLIP. This is a targeted edit, NOT a new movie. "
        "Keep the same approved premium 3D animated-film characters, identities, faces, clothing, gestures, warm cinematic lighting, "
        "coherent space, camera movement, framing, original Hindi dialogue and continuity. "
        "Keep original first/last framing as close as possible. Absolutely no generic dark rectangles, dashboard panels, cheap stickers, "
        "giant floating UI slabs, watermarks, extra actors or invented brand markings. "
        "Only create elegant, material-integrated 3D product storytelling: true physical product silhouettes, polished metallic or glass labels "
        "subtly built into the set with natural occlusion, reflections and appropriate perspective. "
        "Use EXACT attached reference product images. Never replace the machines with a different model. "
        "Use only provided facts. Do not invent efficiency percentages, warranty, savings, capacities or other claims. "
        "If exact digits / written Hindi cannot be preserved, do NOT substitute guesses: the result requires human text QA. "
        "9:16 vertical, four seconds. Preserve spatial continuity and premium theatrical look. "
    )
    if scene==4:
        # Features on purple girl's original shot; one actual verified product only.
        specs=fact(p[0],2)
        if not specs:
            raise DataBlocked("No verified product features for Scene 4")
        detail="; ".join(f"{k} = {v}" for k,v in specs)
        specific=(f"SCENE 4, PURPLE HOODIE GIRL. The girl gestures to the EXISTING washing machine. "
                  f"Edit the machine to match product_01.png faithfully. Integrate TWO understated premium embossed feature cues "
                  f"anchored to the machine instead of UI boxes. Exact verified product #1: {fline(p[0])}. "
                  f"Use ONLY these source-listed cues (photo/model match must be manually verified): {detail}. Keep her original dialogue unless user separately approves a new Hindi voice track.")
    elif scene==5:
        facts=fact(p[0],2)
        if not facts:
            raise DataBlocked("No verified feature data for Scene 5")
        specific=(f"SCENE 5, GREEN HOODIE BOY WITH GLASSES. Retain him on left and natural pointing to right. "
                  f"On the far-right physical surface in the existing set, integrate a subtle gleaming 3D feature showcase "
                  f"with no giant cards, for SOURCE PRODUCT #1. Actual product: {fline(p[0])}. "
                  f"ONLY these website-listed features (require model QA): "+"; ".join(f"{k}: {v}" for k,v in facts)+". Keep fingers and face unaltered.")
    elif scene==7:
        specific=(f"SCENE 7, YELLOW HOODIE BOY. Keep his shot unchanged except tasteful 3D budget/price storytelling "
                  f"physically integrated near his pointing direction. Campaign budget {money(receipt['budget_inr'])}. "
                  f"Rank #1 {'TRUSTFOLIO-LISTED (NOT LIVE VERIFIED)' if receipt.get('source')==WEBSITE_DISPLAY_SOURCE else 'LIVE VERIFIED'} PRICE {money(p[0]['price_inr'])}, source {p[0]['title']}. "
                  "No fake crossed-out prices, sale claims, savings or unsupported promises. "
                  "The visual must feel like a polished advertisement shot rather than a text panel.")
    elif scene==8:
        lineup="\n".join(fline(x) for x in p)
        specific=("SCENE 8, PURPLE-BLUE GOLD LUXURY RANKING STAGE. Replace the FIVE EMPTY original podium positions "
                  "with precisely FIVE attached REAL product reference machines. #1 largest CENTER, #2 LEFT, #3 RIGHT, #4 LOWER LEFT, "
                  "#5 LOWER RIGHT. Preserve the original stage architecture, elegant spotlights and physically grounded reflections. "
                  "Each actual machine must keep its own reference shape, colour and controls; correct size on podium, correct occlusion, "
                  "no duplicate identical silver machine for all five. Small legible elegant brand and INR price details engraved or "
                  "illuminated on podium plinths—not generic floating cards; if lettering fails the human QA rejects the clip.\n"+lineup)
    elif scene==9:
        facts=[fline(p[0]),fline(p[1])]
        specific=("SCENE 9, COMPARISON STAGE. Remove extraneous podiums so there are exactly TWO elegant premium product bays left and right. "
                  "Put real PRODUCT #1 from product_01.png on left and PRODUCT #2 from product_02.png on right, each with honest size, controls, lighting. "
                  "Physically integrated minimal brand/price and ONE common website-listed spec comparison, if present in both records, subject to model verification. "
                  "No fictitious 'winner', unsupported better/worse labels or made-up discount.\n"+"\n".join(facts))
    elif scene==10:
        specific=("SCENE 10, TRUSTFOLIO CTA. PRESERVE the original approved pink floral-shirt girl on left and luxurious ivory purple/gold curved stage. "
                  "Use the user's attached ORIGINAL TrustFolio logo file as branding reference (logo_reference.png, if supplied). "
                  "Make the last seconds feel like a premium film end-card. On the curved physical stage feature a crisp, readable, "
                  "correct URL 'TrustFolio.in' and exact Hindi tagline 'अपना बजट डालो, Best 5 पाओ!'. "
                  "Keep text large, elegant and high contrast, matching the original stage perspective, never cheap opaque panels. "
                  "Do not generate an imitation or misspelled TrustFolio logo. If letter-perfect branding cannot be achieved, "
                  "leave the logo position pristine for precision finishing; do not fabricate characters. "
                  "Ensure final brand frame holds legibly. Preserve original approved Hindi girl dialogue.")
    else:raise DataBlocked("Unsupported replacement scene")
    return (f"TRUSTFOLIO FLOW TARGETED EDIT — SCENE {scene:02d}; ORIGINAL TIMECODE "
            f"{(scene-1)*4:02d}–{scene*4:02d} SECONDS.\n\n"+common+"\n\n"+specific+"\n\n"+
            "SOURCE EVIDENCE (QA USE): website/product-data snapshot sha256="+receipt['snapshot_sha256']+
            ". Source images: listed product_NN.png ingredients. Product facts must match source receipt; "+("WEBSITE LISTED PRICES ONLY, NO VERIFIED LIVE CLAIMS. Do not generate green Live badges. PREVIEW ONLY, NEVER PUBLISH.\n" if receipt.get('source')==WEBSITE_DISPLAY_SOURCE else "Strict live receipt still requires publication recheck.\n"))


def write_prompts(receipt,output,*,allow_demo=False):
    check_flow_receipt(receipt,allow_demo=allow_demo)
    output=Path(output);(output/'prompts').mkdir(parents=True,exist_ok=True)
    (output/'data').mkdir(exist_ok=True)
    for scene in DYNAMIC:
        txt=prompt_for(scene,receipt)
        (output/'prompts'/f'scene_{scene:02d}_{SCENE_NAMES[scene]}.txt').write_text(txt,encoding='utf-8')
    (output/'data'/'verified_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={"status":"FLOW_EDITS_NOT_YET_GENERATED","verified_receipt_sha256":receipt['snapshot_sha256'],
              "category":receipt['category'],"budget_inr":receipt['budget_inr'],"mode":receipt['mode'],
              "required_flow_edits":[f'scene_{i:02d}.mp4' for i in DYNAMIC],
              "source_handoff_sha256":sha({"receipt_sha":receipt['snapshot_sha256'],"scenes":list(DYNAMIC)}),
              "note":"AI Flow output may alter exact product appearance or text; manual visual and factual approval is mandatory.",
              "source":receipt["source"],"publishable":False,
              "pricing_verification":receipt.get("pricing_verification","LIVE_RECEIPT_AT_CAPTURE_ONLY")}
    (output/'data'/'flow_handoff_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'START_HERE.md').write_text(
        "# Premium Google Flow image-to-video editing handoff\n\n"
        "1. Use `original_clips/scene_04.mp4` etc from the approved 40s Google Flow visual master. "
        "**Do not upload a low-quality dynamic overlay demo.**\n"
        "2. In Google Flow (Omni Flash), choose VIDEO EDIT on the selected original 4-second clip, not an unrelated new video. "
        "Flow accepts clips up to 10 seconds for edit; original 40s is split into 4s scenes.\n"
        "3. Attach EXACT reference product images from `product_images/product_01.png` to `product_05.png` "
        "generated by the optional trusted image downloader. Keep original characters/stage as a visual reference.\n"
        "4. Paste matching `prompts/scene_XX_*.txt`; generate. Compare product morphology, exact names and prices "
        "against `data/verified_receipt.json`, not AI output guesses.\n"
        "5. Export an approved 4s MP4 for each edit under `replacements/scene_XX.mp4` and compute SHA256. "
        "Check faces, lip-sync, brand spellings, prices, product count, UI integration and transitions.\n"
        "6. Fill `approvals.json` with exact approved SHA256 and QA booleans. Run `assemble` to splice the new "
        "Flow-generated clips into the original master; no ugly static boxes are drawn.\n"
        "7. **Website-listed prices are not live verified** unless a strict-live receipt exists; never generate a Live badge based only on a listing. New verification must run before publication. "
        "No automatic social posting is present.\n",encoding='utf-8')
    return manifest
