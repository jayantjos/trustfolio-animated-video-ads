#!/usr/bin/env python3
"""Stage one freshly validated nine-scene manifest to existing RunPod volume.

This does not start Pods, call video model, publish content, or mutate backend.
All reference art has baked sample product lettering: manifest explicitly marks
it reference-only, and forbids using these PNGs as factual output frames.
"""
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import sys

from trustfolio_video.contract import Blocked
from trustfolio_video.washing30 import verify_reference_images

BUCKET="1bch597yrz"
ENDPOINT="https://s3api-eu-ro-1.runpod.io"
MAX_AGE_SECONDS=900

def file_hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def validate_stage(story):
    assert story.get("schema_version")==2 and story.get("duration_seconds")==30
    assert story.get("category")=="washing-machines"
    assert story.get("publishing_enabled") is False and story.get("runpod_gpu_launch_approved") is False
    assert story.get("live_price_api_completed") is True
    assert len(story.get("scenes",[]))==9
    dt=datetime.fromisoformat(story["data_observed_at"].replace("Z","+00:00"))
    assert dt.tzinfo and -60<=(datetime.now(timezone.utc)-dt).total_seconds()<=MAX_AGE_SECONDS
    refs=verify_reference_images()
    for index,scene in enumerate(story["scenes"]):
        assert scene["scene"]==f"scene{index+1:02d}"
        assert scene["reference_path"]==refs[index]["path"]
        assert scene["reference_sha256"]==refs[index]["sha256"]
        assert scene["reference_only"] is True and scene["must_erase_all_baked_text_and_products"] is True
    if story.get("catalog_fallback_count",0):
        for scene in story["scenes"][2:7]:
            if scene["dynamic"]["price_source"]=="website_catalog":
                assert scene["dynamic"]["price_label"].startswith("Catalog fallback")
    return refs

def run(story,*,dry_run=False,s3=None):
    refs=validate_stage(story)
    cid=story["campaign_id"]
    assert len(cid)==64 and all(ch in "0123456789abcdef" for ch in cid)
    prefix="videos/private-qa/washing30-inputs/"+cid+"/"
    jobs=[]
    for item in refs:
        p=Path(item["path"])
        jobs.append({"key":prefix+p.name,"sha256":item["sha256"],"bytes":p.stat().st_size,"source":str(p)})
    payload=json.dumps(story,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    digest=hashlib.sha256(payload).hexdigest()
    report={"status":"DRY_RUN_VERIFIED" if dry_run else "STAGED_TO_EXISTING_VOLUME",
            "gpu_created":False,"published":False,"bucket":BUCKET,
            "prefix":prefix,"manifest_key":prefix+"manifest.json",
            "manifest_sha256":digest,"assets":jobs}
    if dry_run:
        return report
    if s3 is None:
        import boto3
        from botocore.config import Config
        assert os.environ.get("TRUSTFOLIO_STORYBOARD_S3_STAGE")=="yes"
        s3=boto3.client("s3",region_name="eu-ro-1",endpoint_url=ENDPOINT,
             aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY_ID"],
             aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_ACCESS_KEY"],
             config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                           connect_timeout=10,read_timeout=35,retries={"max_attempts":3,"mode":"standard"}))
    for job in jobs:
        s3.upload_file(job["source"],BUCKET,job["key"],
            ExtraArgs={"ContentType":"image/png","Metadata":{"sha256":job["sha256"],"referenceonly":"yes"}})
        remote=s3.get_object(Bucket=BUCKET,Key=job["key"])
        h=hashlib.sha256()
        try:
            for chunk in remote["Body"].iter_chunks(chunk_size=1024*1024):
                if chunk:h.update(chunk)
        finally:remote["Body"].close()
        if h.hexdigest()!=job["sha256"]:
            raise RuntimeError("S3 storyboard reference readback mismatch")
    s3.put_object(Bucket=BUCKET,Key=report["manifest_key"],Body=payload,ContentType="application/json")
    latest=s3.get_object(Bucket=BUCKET,Key=report["manifest_key"])
    try: copy=latest["Body"].read(800000)
    finally:latest["Body"].close()
    if hashlib.sha256(copy).hexdigest()!=digest:
        raise RuntimeError("S3 live storyboard readback mismatch")
    return report

def main():
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("--story",required=True)
    a.add_argument("--dry-run",action="store_true")
    a.add_argument("--output",default="output/washing30-stage/receipt.json")
    args=a.parse_args()
    result=run(json.loads(Path(args.story).read_text("utf-8")),dry_run=args.dry_run)
    p=Path(args.output);p.parent.mkdir(exist_ok=True,parents=True)
    # Do not expose S3 credentials, model weights or product responses in logs.
    p.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("WAN5_NINE_SCENES_S3_STAGE="+result["status"])
    print("WAN5_ASSET_COUNT="+str(len(result["assets"])))
    print("WAN5_NO_POD_CREATED=true")
    return 0

if __name__=="__main__":
    sys.exit(main())
