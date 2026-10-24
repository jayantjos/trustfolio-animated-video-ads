"""Immutable nine-scene TrustFolio washing-machine story, bound to verified VPS data.

Reference PNGs contain illustrative SAMPLE brand/price lettering. They are *never*
served as final scenes or data; downstream renderers must recompose clean layers.
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from .contract import Blocked

ASSET_DIR = Path("assets/storyboards/washing-machines")
REFERENCE_LAYOUT = Path("config/storyboards/washing-machines-reference30.json")
TIMES = ((0,3),(3,6),(6,10),(10,14),(14,18),(18,22),(22,26),(26,28),(28,30))
KINDS = ("hook","intro","product","product","product","product","product","ranking","cta")
RANKS = (None,None,5,4,3,2,1,None,None)
ALLOWED_SPEC_KEYS = (
    "capacity","washing_capacity","wash_capacity","type","washing_type",
    "spin_speed","rpm","energy_rating","energy_efficiency","wash_programs",
    "number_of_programs","warranty","motor_warranty",
)

def safe_label(value, *, limit=95):
    if not isinstance(value, (str,int,float)) or isinstance(value, bool):
        return ""
    text = re.sub(r"\\s+", " ", str(value)).strip()
    if any(ord(c)<32 for c in text) or len(text)>limit:
        return ""
    return text

def evidence_fact(product):
    facts = product.get("specifications") or {}
    if not isinstance(facts, dict):
        return None
    for key in ALLOWED_SPEC_KEYS:
        if key in facts:
            value=safe_label(facts[key],limit=45)
            if value:
                return {"label":key.replace("_"," ").title(),
                        "value":value,"source_product_id":product["id"],
                        "claim_level":"catalog_spec_only_not_independently_tested"}
    return None

def verify_reference_images(base=ASSET_DIR):
    paths=[]
    for i in range(1,10):
        filename=f"scene{i:02d}.png"
        file=base/filename
        if not file.is_file():
            raise Blocked("Missing exact fixed story reference: "+filename)
        if not 100_000 <= file.stat().st_size <= 8_000_000:
            raise Blocked("Invalid reference file size: "+filename)
        with file.open("rb") as stream:
            header=stream.read(24)
        if header[:8]!=bytes((137,80,78,71,13,10,26,10)) or header[12:16]!=b"IHDR":
            raise Blocked("Reference is not PNG: "+filename)
        paths.append({"path":file.as_posix(),"sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
    return paths

def build30(approved, *, references=None, blueprint=None):
    """Only call with contract.validate output. Defence-in-depth rechecks key facts."""
    campaign=approved.get("campaign") or {}
    if campaign.get("category")!="washing-machines" or campaign.get("mode") not in ("budget","brand_budget","comparison"):
        raise Blocked("Washing-machine-only approved campaign required")
    budget=campaign.get("budget")
    if type(budget) is not int or not 1<=budget<=10_000_000:
        raise Blocked("Invalid verified campaign budget")
    products=approved.get("products")
    if not isinstance(products,list) or len(products)!=5:
        raise Blocked("Five verified products required")
    if not re.fullmatch(r"[a-f0-9]{64}",str(approved.get("source_sha256","")).lower()):
        raise Blocked("Verified source hash required")
    source_time=approved.get("observed_at")
    try:
        dt=datetime.fromisoformat(str(source_time).replace("Z","+00:00"))
        if dt.tzinfo is None or not -60<=(datetime.now(timezone.utc)-dt).total_seconds()<=900:
            raise ValueError("stale")
    except (ValueError,TypeError):
        raise Blocked("Live Top5 source expired; fetch fresh data") from None
    ids=set();by_rank={}
    for item in products:
        rank=item.get("rank")
        pid=item.get("id")
        if type(rank) is not int or rank not in (1,2,3,4,5) or rank in by_rank or not isinstance(pid,str) or pid in ids:
            raise Blocked("Authoritative rank/id mismatch")
        ids.add(pid);by_rank[rank]=item
        if item.get("price_source")!="website_live_price_api" or item.get("live_price_status")!="ok" or item.get("in_stock") is not True:
            raise Blocked("No live-price evidence or out of stock")
        try:
            price=Decimal(str(item["price_inr"]))
            if not price.is_finite() or not 0<price<=budget:raise ValueError()
        except (ValueError,TypeError,ArithmeticError,KeyError):
            raise Blocked("Live price over budget or invalid") from None
        if not safe_label(item.get("title"),limit=150) or not safe_label(item.get("platform"),limit=80):
            raise Blocked("Missing approved product title/retailer")
    if references is None:
        references=verify_reference_images()
    if len(references)!=9 or len({x["sha256"] for x in references})!=9:
        raise Blocked("Require nine unique scene reference images")
    if blueprint is None:
        blueprint=json.loads(REFERENCE_LAYOUT.read_text(encoding="utf-8"))
    if blueprint.get("category")!="washing-machines" or len(blueprint.get("shots",[]))!=9:
        raise Blocked("Invalid fixed thirty-second blueprint")
    for idx,shot in enumerate(blueprint["shots"]):
        if (shot.get("start"),shot.get("end"))!=TIMES[idx]:
            raise Blocked("Scene timing drift from approved reference")
    scenes=[]
    for idx,((start,end),kind,rank) in enumerate(zip(TIMES,KINDS,RANKS)):
        scene={"scene":f"scene{idx+1:02d}","start":start,"end":end,"seconds":end-start,
               "kind":kind,"reference_sha256":references[idx]["sha256"],
               "reference_path":references[idx]["path"],
               "reference_only":True,"must_erase_all_baked_text_and_products":True}
        if rank:
            item=by_rank[rank]
            scene["dynamic"]={
                "rank":rank,"source_product_id":item["id"],"title":item["title"],
                "brand":safe_label(item.get("brand"),limit=60) or safe_label(item["title"].split()[0]),
                "price_inr":item["price_inr"],"retailer":item["platform"],
                "unaltered_photo_url":item["main_image"],"verified_spec":evidence_fact(item),
                "name_badge":item["title"],"rank_badge":f"#{rank}",
                "speech_pattern":"मैं हूँ {product}. मेरी कीमत ₹{price} है।",
            }
        elif kind in ("intro","ranking"):
            scene["dynamic"]={"budget_inr":budget,"ranked_product_ids":[by_rank[r]["id"] for r in (5,4,3,2,1)]}
        elif kind=="hook":
            scene["fixed_dialogue"]="अरे बाप रे! इतने सारे कपड़े? अब कौन धोएगा?"
            scene["emotion"]="surprised_panicked_hands_at_head"
        else:
            scene["fixed_dialogue"]="अपने बजट की वॉशिंग मशीन TrustFolio पर तुलना करो!"
            scene["url"]="https://www.trustfolio.in"
            scene["emotion"]="happy_smiling_pointing_phone"
    assert sum(x["seconds"] for x in scenes)==30
    snapshot_identity=hashlib.sha256(json.dumps({"campaign":campaign,"source":approved["source_sha256"],
        "assets":[r["sha256"] for r in references]},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {"schema_version":2,"campaign_id":snapshot_identity,"campaign":campaign,"category":"washing-machines",
        "duration_seconds":30,"fps":24,"size":[1080,1920],"scenes":scenes,"source_sha256":approved["source_sha256"],
        "data_observed_at":source_time,"validated_budget_inr":budget,
        "original_product_photos_must_be_unchanged":True,"source_must_be_revalidated_before_publish":True,
        "no_unverified_performance_claims":True,"publishing_enabled":False,
        "stage":"DYNAMIC_STORYBOARD_DATA_BOUND_NOT_ANIMATED_OR_VOICE_QA","runpod_gpu_launch_approved":False}
