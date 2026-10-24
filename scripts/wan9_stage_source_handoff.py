"""GitHub -> RunPod persistent volume: transfer nine user scene REFERENCES and story.

References explicitly are NOT approved clean text-free I2V images. This bridge
prepares the reusable story and current price snapshot but NEVER authorizes the
GPU worker to use logo/price-bearing references as clean animation plates.

No GPU Pods are created. Files are SHA256 read-back verified on S3.
"""
import argparse,hashlib,json,os
from pathlib import Path

from scripts.stage_washing30_s3 import run as stage_story, BUCKET, ENDPOINT
from trustfolio_video.washing30 import verify_reference_images
from trustfolio_video.wan5_nineshot import verified_plan
from trustfolio_video.contract import Blocked

POINTER="jobs/washing-9scene-v1/latest-reference-handoff.json"
MAX_JSON_BYTES=350000

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def upload_verified(s3,key,data):
    if not isinstance(data,bytes) or len(data)>MAX_JSON_BYTES:
        raise Blocked("S3_HANDOFF_MANIFEST_OVERSIZE")
    digest=hashlib.sha256(data).hexdigest()
    s3.put_object(Bucket=BUCKET,Key=key,Body=data,ContentType="application/json",
                  Metadata={"sha256":digest,"privateonly":"yes"})
    obj=s3.get_object(Bucket=BUCKET,Key=key)
    try:
        actual=obj["Body"].read(MAX_JSON_BYTES+1)
    finally:
        obj["Body"].close()
    if actual!=data or hashlib.sha256(actual).hexdigest()!=digest:
        raise Blocked("S3_READBACK_SHA_MISMATCH_"+key)
    return digest

def build_payload(story,stage):
    plan=verified_plan(story)
    refs=verify_reference_images()
    if len(stage["assets"])!=9:
        raise Blocked("NINE_REFERENCE_IMAGES_NOT_STAGED")
    indexed={Path(item["source"]).name:item for item in stage["assets"]}
    scenes=[]
    for idx,shot in enumerate(plan["shots"]):
        name=f"scene{idx+1:02d}.png"
        ref=indexed.get(name)
        if (not ref or ref["sha256"]!=refs[idx]["sha256"]
            or shot["source_storyboard_sha256"]!=ref["sha256"]):
            raise Blocked("SCENE_IMAGE_SHA_INCONSISTENT_"+name)
        scenes.append({
            "scene":shot["scene_id"],"start":shot["start"],"end":shot["end"],
            "reference_s3_key":ref["key"],"reference_sha256":ref["sha256"],
            "motion_prompt":shot["motion_prompt"],
            "clip_output_expected":shot["expected_clip_name"],
            "reference_only":True,"not_safe_directly_as_wan_image":True,
            "clean_plate_s3_key":None,"gpu_motion_rendered":False})
    if [x["scene"] for x in scenes] != [f"scene{i:02d}" for i in range(1,10)]:
        raise Blocked("WRONG_SCENE_ORDER")
    return {
        "schema_version":1,"name":"TRUSTFOLIO_WAN9_GITHUB_TO_RUNPOD_SOURCE_HANDOFF",
        "category":"washing-machines","budget_inr":story["validated_budget_inr"],
        "source_snapshot_observed_at":story["data_observed_at"],
        "campaign_id":story["campaign_id"],"source_sha256":story["source_sha256"],
        "storyboard_s3_key":stage["manifest_key"],
        "storyboard_sha256":stage["manifest_sha256"],
        "motion_job_hash":plan["motion_job_hash"],
        "shots":scenes,"total_duration_seconds":30,
        "ranking_order_in_scenes":[5,4,3,2,1],
        "cta_website":"https://www.trustfolio.in",
        "content_is_reference_only":True,
        "live_products_must_be_refreshed_before_final_publish":True,
        "every_reference_image_contains_potential_stale_sample_text":True,
        "clean_image_visual_qa_passed":False,
        "gpu_input_manifest_built":False,
        "paid_gpu_authorized":False,
        "gpu_pods_created":0,"published":False}

def make_s3():
    import boto3
    from botocore.config import Config
    return boto3.client("s3",region_name="eu-ro-1",endpoint_url=ENDPOINT,
        aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      connect_timeout=7,read_timeout=30,retries={"max_attempts":2}))

def stage(story,s3):
    if os.environ.get("TRUSTFOLIO_STORYBOARD_S3_STAGE")!="yes":
        raise Blocked("PRIVATE_S3_STAGE_NOT_ARMED")
    original=stage_story(story,s3=s3)
    handoff=build_payload(story,original)
    prefix=original["prefix"]
    manifest=prefix+"wan9-reference-handoff.json"
    digest=upload_verified(s3,manifest,canonical(handoff))
    pointer={"schema_version":1,"handoff_key":manifest,
             "handoff_sha256":digest,"scene_count":len(handoff["shots"]),
             "source_snapshot_observed_at":story["data_observed_at"],
             "reference_only":True,"gpu_ready":False,"published":False}
    pointer_sha=upload_verified(s3,POINTER,canonical(pointer))
    return {"status":"NINE_GITHUB_SOURCE_IMAGES_AND_STORY_AT_RUNPOD_S3_VERIFIED",
            "bucket":BUCKET,"reference_scene_count":9,
            "handoff_key":manifest,"handoff_sha256":digest,
            "pointer_key":POINTER,"pointer_sha256":pointer_sha,
            "storyboard_s3_key":original["manifest_key"],
            "reference_only":True,"gpu_ready":False,
            "gpu_pods_created":0,"paid_gpu_cost_usd":0,"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--story",required=True)
    p.add_argument("--out",default="output/wan9-github-to-runpod-handoff.json")
    a=p.parse_args()
    story=json.loads(Path(a.story).read_text(encoding="utf-8"))
    data=stage(story,make_s3())
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("WAN9_SOURCE_HANDOFF="+data["status"])
    print("WAN9_S3_REFERENCE_IMAGES="+str(data["reference_scene_count"]))
    print("WAN9_S3_HANDOFF_KEY="+data["handoff_key"])
    print("WAN9_S3_POINTER_KEY="+data["pointer_key"])
    print("WAN9_RENDER_GPU_READY=false")
    print("WAN9_NEW_GPU_COST_USD=0")

if __name__=="__main__":
    main()
