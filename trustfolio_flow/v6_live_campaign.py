"""Premium V6 live-video handoff and publication guard.

This module never renders, uploads, or posts by itself.
No catalog fallback, stale price, wrong model/photo, unapproved voice or
historical V6 output can be labeled a live-price marketing Reel.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
import re
from pathlib import Path
from urllib.parse import quote, urlencode
from .live import check_receipt, DataBlocked, amount, sha

V6_APPROVED_VISUAL_SHA256="da1e0193a7c50bfc1253c9794bedfff941b739aead0c0a4b913f6377b16c9923"
V6_BALANCED_AUDIO_SHA256="9e3b469be2f0439d6548ad80b7304614cad34c08fe8317d872213499a3c9e04d"
FOUR_SPECS=("Capacity","Load Type","Energy Rating","Spin Speed",
            "Automation Type","Washing Machine Type","Wash Programs",
            "In-built Heater","Motor Type","Water Rating")

def source_specs(product):
    """Exactly four ACTUAL source features, or fail closed, no synthetic data."""
    raw=product.get("specifications")
    if not isinstance(raw,dict):raise DataBlocked("Product has no source specifications")
    rows=[]
    for key in FOUR_SPECS:
        val=raw.get(key)
        if isinstance(val,str) and val.strip() and val.strip().lower() not in (
                "n/a","na","unknown","not available","null","none","-","—"):
            rows.append({"label":key,"value":val.strip()})
        if len(rows)==4:break
    if len(rows)!=4:
        raise DataBlocked("Product does not contain four trustworthy source specifications")
    return rows

def validate_receipt(receipt,*,now=None):
    check_receipt(receipt,now=now)
    if receipt.get("source")!="trustfolio_live_api":
        raise DataBlocked("Website catalog-only and demo receipts cannot become live video ads")
    if receipt.get("category")!="washing-machines":
        raise DataBlocked("This artistic master is Washing Machines only")
    if len(receipt["products"])!=5 or any(
            p.get("live_price_status")!="ok" for p in receipt["products"]):
        raise DataBlocked("All five current marketplace prices must be verified")
    four={str(p["rank"]):source_specs(p) for p in receipt["products"]}
    return four

def check_photo_approvals(receipt,photo_manifest):
    """Manual visual/model check, exact source ID and URL and 64-digit content hash."""
    records=photo_manifest.get("products") if isinstance(photo_manifest,dict) else None
    if not isinstance(records,list) or len(records)!=5:
        raise DataBlocked("No five-model photo QA approvals")
    seen_sha={}
    for product,review in zip(receipt["products"],records):
        if not isinstance(review,dict) or review.get("rank")!=product["rank"] or (
                review.get("id")!=product["id"] or
                review.get("image_url")!=product["image_url"]):
            raise DataBlocked("Product and reviewed photo do not match")
        digest=str(review.get("image_sha256") or "")
        if not re.fullmatch("[a-f0-9]{64}",digest):
            raise DataBlocked("Missing exact product image checksum")
        old=seen_sha.get(digest)
        if old is not None and old.casefold()!=product["brand"].casefold():
            raise DataBlocked("Cross-brand duplicate product photo bytes")
        seen_sha[digest]=product["brand"]
        for k in ("model_identity_ok","product_photo_ok","commercial_usage_ok"):
            if review.get(k) is not True:
                raise DataBlocked("Product photo/model not manually approved: "+k)
    return True

def caption_for(receipt):
    """Exact source-backed caption for both network descriptions."""
    rows=validate_receipt(receipt)
    budget=receipt["budget_inr"]
    mode=receipt.get("mode","budget")
    brand=receipt.get("brand","")
    if mode=="brand_budget":
        title=f"Top 5 {brand} Washing Machines — ₹{budget:,} ke budget mein!"
    elif mode=="comparison":
        title=f"Washing Machine Comparison — ₹{budget:,} budget ke Top 5!"
    else:
        title=f"₹{budget:,} tak ki Top 5 Washing Machines! 🧺"
    lines=[f"✨ {title}","TrustFolio par source-ranked picks aur verify ki gayi prices:"]
    for product in receipt["products"]:
        short=product["title"].strip()
        if len(short)>75:short=short[:72].rstrip()+"..."
        value=format(amount(product["price_inr"]),",.0f")
        lines.append(f"#{product['rank']} {short} — ₹{value} ({product['platform'].title()})")
    qs={"budget":str(budget)}
    if mode=="brand_budget":qs["brand"]=brand
    landing=("https://trustfolio.in/category/washing-machines/products?"+
             urlencode(qs,quote_via=quote))
    lines.extend([
        "",
        "🔍 4 genuine source-listed features aur five-product comparison dekho.",
        "🔗 Same category + budget results: "+landing,
        "Instagram caption mein URL clickable nahi hota; website ya bio link open karo.",
        "Prices aur availability badal sakti hain. Khareedne se pehle retailer par confirm karo.",
        "#TrustFolio #WashingMachine #SmartShopping #ProductComparison #Best5"
    ])
    caption="\n".join(lines)
    if len(caption)>2200:raise DataBlocked("Caption unexpectedly too long")
    return {"caption":caption,"landing_url":landing,"four_specs_by_rank":rows}

def handoff(receipt,photo_manifest,*,now=None):
    four=validate_receipt(receipt,now=now)
    check_photo_approvals(receipt,photo_manifest)
    cap=caption_for(receipt)
    return {
        "schema_version":1,"status":"READY_FOR_DYNAMIC_RENDER_NOT_PUBLISHABLE",
        "category":"washing-machines","budget_inr":receipt["budget_inr"],
        "mode":receipt["mode"],"brand":receipt["brand"],
        "source_snapshot_sha256":receipt["snapshot_sha256"],
        "ranked_product_ids":[p["id"] for p in receipt["products"]],
        "prices_inr":[p["price_inr"] for p in receipt["products"]],
        "product_names":[p["title"] for p in receipt["products"]],
        "four_spec_rows_by_rank":four,
        "caption":cap["caption"],"landing_url":cap["landing_url"],
        "approved_art_direction_v6_sha256":V6_APPROVED_VISUAL_SHA256,
        "artistic_master_contains_historical_baked_in_prices":True,
        "must_rebuild_all_data_bearing_frames_from_fresh_receipt":True,
        "needs_clear_hindi_product_voiceover":True,
        "post_allowed":False,
        "note":"Render newly with actual live values; never post the static approved 54s V6 reference file."
    }

def stable_product_fingerprint(receipt):
    """Model/price/rank/spec/merchant identity without changing check timestamps.

    POST /api/live-prices legitimately refreshes live_checked_at; requiring two
    literal receipt hashes to match makes *every* prepublish POST fail.
    """
    fields=("rank","id","brand","title","platform","price_inr","image_url",
            "specifications","category","price_source","live_price_status")
    data={"campaign":{k:receipt[k] for k in ("category","budget_inr","mode","brand")},
          "products":[{k:p.get(k) for k in fields} for p in receipt["products"]]}
    return sha(data)

def prepublish_hard_gate(render_record,source_receipt,latest_receipt,*,now=None):
    """Recheck old rendered vs NEW live receipt. No API calls in this function."""
    validate_receipt(source_receipt,now=now)
    validate_receipt(latest_receipt,now=now)
    if stable_product_fingerprint(source_receipt)!=stable_product_fingerprint(latest_receipt):
        raise DataBlocked("Products/prices/specifications/model photos/rank changed; re-render")
    if not isinstance(render_record,dict) or (
            render_record.get("source_snapshot_sha256")!=source_receipt["snapshot_sha256"]):
        raise DataBlocked("Rendered frame data not bound to exact live receipt")
    digest=str(render_record.get("video_sha256") or "")
    if not re.fullmatch("[a-f0-9]{64}",digest) or digest in (
            V6_APPROVED_VISUAL_SHA256,V6_BALANCED_AUDIO_SHA256):
        raise DataBlocked("Historical artistic reference is not a live-price render")
    if render_record.get("rendered_product_ids")!=[
            p["id"] for p in source_receipt["products"]]:
        raise DataBlocked("Rendered product order differs from source")
    if render_record.get("rendered_prices_inr")!=[
            p["price_inr"] for p in source_receipt["products"]]:
        raise DataBlocked("Price displayed in video is not the current verified amount")
    for k in ("frame_text_qa_pass","product_model_qa_pass","four_specs_qa_pass",
              "hindi_voice_qa_pass","audio_loudness_qa_pass","video_duration_qa_pass",
              "caption_qa_pass","public_media_sha256_pass","human_release_approved"):
        if render_record.get(k) is not True:
            raise DataBlocked("Missing release gate: "+k)
    if render_record.get("published") is not False:
        raise DataBlocked("Video is already published or publication state unknown")
    return True

def main():
    p=argparse.ArgumentParser(description="Strict current-live V6 render handoff, never publish")
    p.add_argument("--receipt",required=True)
    p.add_argument("--photo-qa",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    receipt=json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    photos=json.loads(Path(args.photo_qa).read_text(encoding="utf-8"))
    output=handoff(receipt,photos)
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("V6_LIVE_HANDOFF_READY=YES")
    print("RENDER_READY_FOR_REVIEW=YES; POST_ALLOWED=NO")
if __name__=="__main__":main()
