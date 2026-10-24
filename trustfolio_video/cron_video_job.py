"""Cron->GitHub->RunPod video job contract. Produces DATA-ONLY job, no paid GPU.

The existing TrustFolio API Top5 contract is authoritative. VPS may send
campaign metadata and its live response envelope; nothing is rendered until
the pipeline REVALIDATES the latest prices again immediately before GPU work.
"""
import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from .contract import Blocked,campaign,canonical,timestamp,validate
from .fixed_pilot import check_registry

ROOT=Path(__file__).resolve().parent.parent
QUEUE_MARKER="VALIDATED_LIVE_DATA_ART_QA_PENDING"
MAX_EVENT_AGE_SECONDS=900

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate_cron_payload(raw,*,now=None):
    now=now or datetime.now(timezone.utc)
    if not isinstance(raw,dict) or raw.get("schema_version")!=1:
        raise Blocked("Cron job must use schema version 1")
    if raw.get("producer")!="trustfolio-vps-cron":
        raise Blocked("Unapproved job producer")
    job_id=raw.get("job_id")
    if not isinstance(job_id,str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{7,79}",job_id):
        raise Blocked("Invalid idempotency job id")
    dt=timestamp(raw.get("requested_at"))
    age=(now-dt).total_seconds()
    if age < -60 or age > MAX_EVENT_AGE_SECONDS:
        raise Blocked("Cron job timestamp is stale or future")
    desired=campaign(**raw.get("campaign",{}))
    known=check_registry()
    if desired["category"] not in known:
        raise Blocked("Not one of 20 verified categories")
    envelope=raw.get("snapshot")
    if not isinstance(envelope,dict):
        raise Blocked("Cron must pass signed-source-compatible authoritative snapshot envelope")
    if envelope.get("request")!=desired:
        raise Blocked("Campaign and live snapshot do not match")
    verified=validate(envelope,now=now,max_age_seconds=MAX_EVENT_AGE_SECONDS)
    if verified["campaign"]!=desired:
        raise Blocked("Live response campaign mismatch")
    return job_id,desired,verified,known[desired["category"]]

def build_video_job(raw,*,now=None,story=None):
    job_id,spec,valid,entry=validate_cron_payload(raw,now=now)
    source={item["rank"]:item for item in valid["products"]}
    if set(source)!={1,2,3,4,5}:
        raise Blocked("Top5 rank set is invalid")
    candidate=(story if story is not None else
               read_json(ROOT/"config/storyboards/washing-machines-reference30.json"))
    supported=spec["category"]=="washing-machines"
    shots=[]
    if supported:
        if candidate["category"]!=spec["category"] or candidate["output"]["seconds"]!=30:
            raise Blocked("Storyboard category/duration mismatch")
        boundaries=[(0,3),(3,6),(6,10),(10,14),(14,18),(18,22),(22,26),(26,28),(28,30)]
        if [(shot["start"],shot["end"]) for shot in candidate["shots"]]!=boundaries:
            raise Blocked("Reference timeline changed")
        if [s["rank"] for s in candidate["shots"] if s["kind"]=="live_product"] != [5,4,3,2,1]:
            raise Blocked("Authoritative rank reveal order changed")
        for part in candidate["shots"]:
            shot={"id":part["id"],"start":part["start"],"end":part["end"],
                  "kind":part["kind"]}
            if part["kind"]=="live_product":
                rank=part["rank"]
                product=source[rank]
                shot["product"]={
                  "source_id":product["id"],"rank":rank,
                  "brand":product.get("brand",""),"title":product["title"],
                  "price_inr":str(product["price_inr"]),
                  "retailer":product["platform"],"image_url":product["main_image"],
                  "live_checked_at":product.get("live_checked_at") or product.get("live_priced_at"),
                }
                shot["text_hi"]=f"रैंक {rank} • ₹{product['price_inr']}"
            elif part["kind"]=="podium":
                shot["rank_order"]=[5,4,3,2,1]
            else:
                shot["text_hi"]=part.get("text_hi","")
            shots.append(shot)
    job={
       "schema_version":1,"job_id":job_id,"campaign":spec,
       "mode":spec["mode"],"category_theme":entry["world"],
       "lead_character_id":entry["character_id"],
       "lead_image_asset":entry["hero_asset"],
       "category_location_asset":entry["location_asset"],
       "scene_timeline":shots,
       "authoritative_top5_ids":[source[i]["id"] for i in range(1,6)],
       "rank_reveal_order":[5,4,3,2,1],
       "source_sha256":valid["source_sha256"],
       "source_observed_at":valid["observed_at"],
       "render_eligibility":QUEUE_MARKER if supported else "CATEGORY_SCENE_ART_NOT_APPROVED",
       "character_asset_uploaded_verified":False,
       "background_assets_uploaded_verified":False,
       "live_prices_must_be_refetched_at_render_start":True,
       "paid_gpu_authorized":False,
       "gpu_started":False,
       "mp4_created":False,
       "social_publishing_enabled":False,
    }
    # Stable content fingerprint for duplicate cron retries. Never depend on list order
    # except the authoritative ranking and shot timeline.
    job["idempotency_sha256"]=hashlib.sha256(canonical({
       "job_id":job_id,"campaign":spec,"snapshot_sha256":job["source_sha256"],
       "lead":job["lead_character_id"],"shots":shots,
    }).encode("utf-8")).hexdigest()
    return job

def main():
    p=argparse.ArgumentParser(description="CPU-only validated incoming VPS cron job")
    p.add_argument("--input",required=True,help="JSON envelope received from trusted VPS cron")
    p.add_argument("--output",default="output/video-cron-job.json")
    args=p.parse_args()
    try:
        job=build_video_job(read_json(args.input))
        target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(job,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("TRUSTFOLIO_CRON_STATUS="+job["render_eligibility"])
        print("TRUSTFOLIO_GPU_STARTED=false")
        print("TRUSTFOLIO_PUBLISHING_ENABLED=false")
        return 0
    except (Blocked,ValueError,KeyError,TypeError,OSError):
        print("TRUSTFOLIO_CRON_STATUS=BLOCKED_BAD_OR_STALE_DATA")
        return 1
if __name__=="__main__":
    raise SystemExit(main())
