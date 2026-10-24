"""One capped PRIVATE technical WAN9 GPU attempt. No publishing, no volume deletes.

Incomplete scenes are saved for later review; a $1 limit never implies
nine full clips or a finished public advertisement.
"""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from scripts.first_wan5_gpu_preflight import BASE, api_read
from scripts.wan5_first_paid_controller import (
    safe_api, graphql_create, make_graphql_payload, create_registry,
)
from scripts.wan5_live_log_guard import scan_container_logs
from trustfolio_video.wan9_dollar1_budget import (
    quote_guard, deployment_guard, APPROVED_VOLUME, APPROVED_DATACENTER,
    APPROVED_GPU,
)

NAME = "trustfolio-video-wan9-multiscene-private-qa-20261024"
IMAGE = "ghcr.io/jayantjos/trustfolio-wan9-worker@sha256:a526ba3a516b337aa2281d5d1ae1f22f36c79645f210d1effbe98910711e35ef"
S3_PREFIX = "videos/private-qa/washing-9scene-v1/"
JOB = "jobs/washing-9scene-v1/"
REQUEST = Path("pilot/wan9-capped-once.request.json")
REPORT = Path("output/wan9-capped-first-attempt.json")
TTL_MIN = 30
MONITOR_SECS = 26 * 60
EXPECTED = [f"scene{i:02d}" for i in range(1, 10)]

class Wan9Blocked(RuntimeError):
    pass

def s3_client():
    import boto3
    from botocore.config import Config
    a=os.environ.get("RUNPOD_S3_ACCESS_KEY_ID")
    b=os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY")
    if not a or not b:
        raise Wan9Blocked("MISSING_PRIVATE_S3_KEYS")
    return boto3.client("s3", endpoint_url="https://s3api-eu-ro-1.runpod.io",
        region_name="eu-ro-1",aws_access_key_id=a,aws_secret_access_key=b,
        config=Config(signature_version="s3v4",
                      s3={"addressing_style":"path"},connect_timeout=8,read_timeout=35))

def load(s3,key,cap):
    obj=s3.get_object(Bucket=APPROVED_VOLUME,Key=key)
    try:
        if not 0<int(obj.get("ContentLength",0))<=cap:
            raise Wan9Blocked("INVALID_S3_OBJECT_LENGTH")
        data=obj["Body"].read(cap+1)
    finally:
        obj["Body"].close()
    if len(data)>cap:
        raise Wan9Blocked("S3_OBJECT_OVERSIZE")
    return data,obj.get("Metadata",{})

def save_sha_verified(s3,key,data,*,kind="application/json"):
    sha=hashlib.sha256(data).hexdigest()
    s3.put_object(Bucket=APPROVED_VOLUME,Key=key,Body=data,
                  ContentType=kind,Metadata={"sha256":sha,"privateonly":"yes"})
    remote,_=load(s3,key,max(len(data)+32,1000))
    if remote!=data or hashlib.sha256(remote).hexdigest()!=sha:
        raise Wan9Blocked("S3_UPLOAD_READBACK_HASH_MISMATCH")
    return sha

def require_fresh_one_time_request():
    r=json.loads(REQUEST.read_text())
    expected={"version":1,"private_technical_qa_only":True,"publish":False,
        "single_pod":True,"max_new_gpu_spend_usd":1,
        "network_volume_id":APPROVED_VOLUME,"user_approved":True,
        "approved_by":"jayantjos"}
    if any(r.get(k)!=v for k,v in expected.items()):
        raise Wan9Blocked("FRESH_APPROVAL_REQUEST_POLICY_MISMATCH")
    if set(r)!=set(expected)|{"approved_at_utc","approval_id"}:
        raise Wan9Blocked("ONE_TIME_APPROVAL_SCHEMA_INVALID")
    t=datetime.fromisoformat(r["approved_at_utc"].replace("Z","+00:00"))
    now=datetime.now(timezone.utc)
    if t.tzinfo is None or not timedelta(0)<=now-t<=timedelta(minutes=60):
        raise Wan9Blocked("APPROVAL_EXPIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT")!="1":
        raise Wan9Blocked("REPLAY_ATTEMPT_BLOCKED")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}",r["approval_id"]):
        raise Wan9Blocked("APPROVAL_ID_INVALID")
    return r["approval_id"]

def require_independent_reaper():
    import urllib.request
    token=os.environ.get("GHCR_GITHUB_TOKEN","")
    if not token:
        raise Wan9Blocked("GITHUB_ACTIONS_TOKEN_MISSING")
    url="https://api.github.com/repos/jayantjos/trustfolio-animated-video-ads/actions/workflows/wan9-independent-pod-reaper.yml/runs?branch=main&per_page=10"
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=20) as f:
        entries=json.load(f).get("workflow_runs",[])
    now=datetime.now(timezone.utc)
    if not any(x.get("conclusion")=="success" and x.get("head_branch")=="main"
        and x.get("created_at") and timedelta(0)<=now-datetime.fromisoformat(
        x["created_at"].replace("Z","+00:00"))<=timedelta(minutes=35)
        for x in entries):
        raise Wan9Blocked("NO_RECENT_HEALTHY_INDEPENDENT_MAIN_REAPER")

def list_owned(key):
    rows=safe_api(key,"/pods").get("pods")
    if not isinstance(rows,list):
        raise Wan9Blocked("POD_LIST_BAD_SCHEMA")
    return [p for p in rows if isinstance(p,dict) and p.get("name")==NAME]

def exact_owned(p):
    if not isinstance(p,dict) or p.get("name")!=NAME:
        raise Wan9Blocked("POD_NAME_MISMATCH")
    if p.get("dataCenterId")!=APPROVED_DATACENTER or p.get("mounts",{}).get("network")!=[
        {"volumeId":APPROVED_VOLUME,"path":"/workspace"}]:
        raise Wan9Blocked("POD_REGION_OR_MOUNT_MISMATCH")
    pid=p.get("id")
    if not isinstance(pid,str) or not re.fullmatch("[A-Za-z0-9_-]{5,80}",pid):
        raise Wan9Blocked("POD_ID_INVALID")
    return pid

def cleanup(key,pid=None):
    matches=list_owned(key)
    if len(matches)>1:
        raise Wan9Blocked("MULTIPLE_SAME_NAME_PODS_REFUSE_UNSAFE_DELETE")
    if not matches:
        return "NO_OWNED_POD"
    found=exact_owned(matches[0])
    if pid is not None and found!=pid:
        raise Wan9Blocked("POD_ID_CHANGED_REFUSE_DELETE")
    safe_api(key,"/pods/"+found,"DELETE")
    for _ in range(15):
        state=safe_api(key,"/pods/"+found)
        if state.get("deleted") is True:
            return "POD_DELETE_GET_404_VERIFIED"
        time.sleep(2)
    raise Wan9Blocked("POD_DELETION_UNCONFIRMED")

def check_quote(key):
    v=api_read(key,BASE+"/network-volumes/"+APPROVED_VOLUME)
    if v.get("id")!=APPROVED_VOLUME or v.get("size")!=100 or v.get("dataCenter")!=APPROVED_DATACENTER:
        raise Wan9Blocked("EXISTING_PROTECTED_VOLUME_CHANGED")
    cat=api_read(key,BASE+"/catalog/gpus")
    centers=api_read(key,BASE+"/catalog/datacenters?include=GPU_AVAILABILITY")
    gpu=next((g for g in cat.get("gpus",[]) if g.get("id")==APPROVED_GPU),None)
    center=next((d for d in centers.get("dataCenters",[]) if d.get("id")==APPROVED_DATACENTER),None)
    if not gpu or not center:
        raise Wan9Blocked("LIVE_GPU_OR_REGION_NOT_FOUND")
    stock=next((g.get("availability") for g in center.get("gpuAvailability",[])
                if g.get("id")==APPROVED_GPU),"UNKNOWN")
    if stock not in ("LOW","MEDIUM","HIGH"):
        raise Wan9Blocked("WAN9_GPU_NOT_ADVERTISED_IN_VOLUME_REGION")
    rate=gpu["price"]["secure"]
    quote=quote_guard(rate,ttl_minutes=TTL_MIN)
    return quote,stock

def stage_technical_candidates(s3):
    # This input is explicitly NON-PUBLISHABLE until independent visual review.
    pointer=json.loads(load(s3,JOB+"latest-reference-handoff.json",30000)[0])
    if pointer.get("reference_only") is not True or pointer.get("scene_count")!=9:
        raise Wan9Blocked("SOURCE_POINTER_NOT_NINE_REFERENCES")
    handoff_raw,_=load(s3,pointer["handoff_key"],200000)
    if hashlib.sha256(handoff_raw).hexdigest()!=pointer.get("handoff_sha256"):
        raise Wan9Blocked("SOURCE_HANDOFF_SHA_CHANGED")
    handoff=json.loads(handoff_raw)
    shots=handoff.get("shots",[])
    if len(shots)!=9 or handoff.get("content_is_reference_only") is not True:
        raise Wan9Blocked("UNEXPECTED_STORY_HANDOFF_SCHEMA")
    out=[]
    for n,src in enumerate(shots,1):
        sid=EXPECTED[n-1]
        if src.get("scene")!=sid or src.get("reference_only") is not True:
            raise Wan9Blocked("SHOT_ORDER_WRONG_"+sid)
        src_key=JOB+"visual-review-candidates/"+sid+".png"
        art,metadata=load(s3,src_key,8500000)
        if metadata.get("visuallyapproved")!="false":
            raise Wan9Blocked("CANDIDATE_VISUAL_STATE_AMBIGUOUS_"+sid)
        sha=hashlib.sha256(art).hexdigest()
        if sha!=metadata.get("sha256") or len(art)<50000:
            raise Wan9Blocked("CANDIDATE_REMOTE_SHA_INVALID_"+sid)
        # The manifest path is deliberately different from original text-bearing references.
        target="assets/candidates/washing-machines/"+sid+".png"
        save_sha_verified(s3,target,art,kind="image/png")
        prompt=src.get("motion_prompt")
        if not isinstance(prompt,str) or not 80<=len(prompt)<=1600:
            raise Wan9Blocked("GPU_PROMPT_INVALID_"+sid)
        out.append({"id":sid,"plate_path":target,"plate_sha256":sha,
          "reference_sha256":src["reference_sha256"],"prompt":prompt,
          "visual_qa_approved":False,"not_for_publication":True,
          "candidate_sha_verified":True})
    manifest={"version":1,"category":"washing-machines",
      "state":"MASKED_CANDIDATES_NONPUBLISHABLE_TECHNICAL_QA",
      "technical_render_only":True,"private_qa":True,"published":False,
      "paid_gpu_authorized":False,
      "motion_job_hash":handoff["motion_job_hash"],"shots":out}
    body=json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()
    save_sha_verified(s3,JOB+"gpu-input.json",body)
    return hashlib.sha256(body).hexdigest()

def check_clips(s3):
    clips=[]
    for sid in EXPECTED:
        try:
            raw,_=load(s3,S3_PREFIX+sid+".motion.receipt.json",15000)
            rc=json.loads(raw)
            if rc.get("scene_id")!=sid or rc.get("status")!="GPU_MOTION_WRITTEN_AWAITING_S3_CONTROLLER_VERIFICATION":
                continue
            raw_mp4,_=load(s3,S3_PREFIX+sid+".motion.mp4",200000000)
            if hashlib.sha256(raw_mp4).hexdigest()!=rc.get("sha256") or len(raw_mp4)!=rc.get("bytes"):
                raise Wan9Blocked("GPU_MP4_S3_SHA_MISMATCH_"+sid)
            clips.append(sid)
        except Exception as exc:
            if isinstance(exc,Wan9Blocked):
                raise
            continue
    return clips

def run():
    require_fresh_one_time_request()
    require_independent_reaper()
    read_key=os.environ.get("RUNPOD_API_KEY","")
    write_key=os.environ.get("RUNPOD_POD_WRITE_KEY","")
    token=os.environ.get("GHCR_GITHUB_TOKEN","")
    if not read_key or not write_key or not token:
        raise Wan9Blocked("GPU_READ_WRITE_OR_GITHUB_KEY_MISSING")
    quote,stock=check_quote(read_key)
    print("WAN9_LIVE_GPU_HOURLY_RATE="+quote["live_rate_usd_per_hour"],flush=True)
    print("WAN9_PROVIDER_TTL_PREDICTED_COST="+quote["predicted_upper_gpu_cost_usd"],flush=True)
    print("WAN9_GPU_STOCK="+stock,flush=True)
    s3=s3_client()
    bundle_sha=stage_technical_candidates(s3)
    print("WAN9_NINE_PRIVATE_TECHNICAL_INPUT_SHA="+bundle_sha,flush=True)
    if list_owned(write_key):
        raise Wan9Blocked("AN_EXISTING_WAN9_GPU_POD_ALREADY_EXISTS")
    existing=check_clips(s3)
    if existing:
        raise Wan9Blocked("PREEXISTING_RENDER_CLIPS_REQUIRE_RECONCILIATION")
    registry_id=None
    pod_id=None
    attempted=False
    report={"status":"NO_GPU_STARTED","verified_scenes":[],"published":False,
            "worker_image":IMAGE,"input_manifest_sha256":bundle_sha,
            "predicted_gpu_cost_usd":quote["predicted_upper_gpu_cost_usd"],
            "gpu_deleted":False}
    try:
        registry_id=create_registry(write_key,token)
        payload=make_graphql_payload(registry_id,gpu_id=APPROVED_GPU)
        payload["name"]=NAME
        payload["imageName"]=IMAGE
        payload["terminateAfter"]=(datetime.now(timezone.utc)+timedelta(
            minutes=TTL_MIN)).replace(microsecond=0).isoformat().replace("+00:00","Z")
        payload["env"]=[
            {"key":"TRUSTFOLIO_PRIVATE_QA","value":"yes"},
            {"key":"TRUSTFOLIO_WAN9_RENDER","value":"yes"},
            {"key":"TRUSTFOLIO_ATTEMPT_ID","value":"wan9-one-shot-20261024"}]
        deployment_guard(payload,quoted_rate=quote["live_rate_usd_per_hour"])
        print("WAN9_CREATING_ONE_CAPPED_GPU_POD=true",flush=True)
        attempted=True
        pod=graphql_create(write_key,payload)
        pod_id=pod["id"]
        if pod.get("name")!=NAME or pod.get("imageName")!=IMAGE:
            raise Wan9Blocked("PROVISIONED_WRONG_WORKER_POD")
        price=Decimal(str(pod.get("costPerHr")))
        quote_guard(price,ttl_minutes=TTL_MIN)
        report["status"]="GPU_POD_CREATED_PRIVATE_TECHNICAL_QA"
        report["pod_id"]=pod_id
        started=time.monotonic()
        fingerprint=None
        last_seen=started
        seen=False
        while time.monotonic()-started<MONITOR_SECS:
            owned=list_owned(write_key)
            if len(owned)!=1 or exact_owned(owned[0])!=pod_id:
                raise Wan9Blocked("GPU_OWNERSHIP_LOST_OR_DUPLICATE")
            clips=check_clips(s3)
            report["verified_scenes"]=clips
            print("WAN9_REAL_SHA_VERIFIED_SCENE_COUNT="+str(len(clips)),flush=True)
            if len(clips)==9:
                report["status"]="NINE_GPU_CLIPS_S3_SHA_VERIFIED_PRIVATE_QA"
                return report
            if owned[0].get("status") in ("EXITED","FAILED","ERROR","TERMINATED"):
                report["status"]="GPU_WORKER_ENDED_PARTIAL_"+str(len(clips))
                return report
            logs=scan_container_logs(read_key,pod_id)
            if logs.get("fatal"):
                raise Wan9Blocked("GPU_FATAL_LIVE_LOG_"+str(logs["fatal"])[:55])
            f=logs.get("fingerprint")
            if logs.get("available") and f and f!=fingerprint:
                fingerprint=f
                last_seen=time.monotonic()
                seen=True
            if time.monotonic()-last_seen>(100 if seen else 550):
                raise Wan9Blocked("NO_VISIBLE_LIVE_GPU_LOG_PROGRESS")
            time.sleep(20)
        report["status"]="STOPPED_AT_CAPPED_TIME_"+str(len(report["verified_scenes"]))
        return report
    finally:
        if attempted:
            try:
                state=cleanup(write_key,pod_id)
                report["gpu_deleted"]=True
                report["delete_receipt"]=state
                print("WAN9_POD_CLEANUP="+state,flush=True)
            except Exception as exc:
                report["gpu_deleted"]=False
                report["delete_receipt"]="CLEANUP_NEEDS_REAPER_"+type(exc).__name__
                print("WAN9_CLEANUP_NEEDS_INDEPENDENT_REAPER",flush=True)
        if registry_id:
            try:
                safe_api(write_key,"/registries/"+registry_id,"DELETE")
            except Exception:
                print("WAN9_EPHEMERAL_GHCR_REGISTRY_CLEANUP_UNCONFIRMED",flush=True)
        REPORT.parent.mkdir(exist_ok=True,parents=True)
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        if not report.get("gpu_deleted"):
            print("WAN9_GPU_DELETION_NOT_CONFIRMED",flush=True)

if __name__=="__main__":
    try:
        result=run()
        print("WAN9_PRIVATE_RESULT="+result["status"],flush=True)
        raise SystemExit(0 if result.get("gpu_deleted") else 4)
    except Exception as e:
        print("WAN9_CONTROLLER_ABORT="+type(e).__name__,flush=True)
        print("WAN9_CONTROLLER_REASON="+str(e)[:120],flush=True)
        raise SystemExit(2)
