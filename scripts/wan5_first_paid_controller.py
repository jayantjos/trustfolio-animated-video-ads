#!/usr/bin/env python3
"""One approved $1 Wan2.2 5-second RunPod GPU pilot, automated GitHub->RunPod.

Single exact-name, exact-region, exact-volume Pod. Server-side terminateAfter
is mandatory. Main-branch independent reaper handles CI crash. A finally
block always terminates Pod, verifies 404, and removes temporary GHCR auth.
Media is accepted only when S3 readback matches the real GPU receipt.
No model weights, character assets, Pod credentials, or videos are published.
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config

from scripts.first_wan5_gpu_preflight import (
    BASE, DATACENTER, GPU, VOLUME, read_inputs, check_catalog, api_read,
)
from scripts.wan5_gpu_worker import IMAGE_SHA, IMAGE_BYTES, JOB_ID

GRAPHQL="https://api.runpod.io/graphql"
NAME="trustfolio-video-"+JOB_ID
IMAGE="ghcr.io/jayantjos/trustfolio-wan5-worker@sha256:5f920321ce5cd6485e560a670b3b53f8f69cc07b2b71b10caa28723eea15cdf1"
S3_BUCKET=VOLUME
S3_HERO="assets/characters/shared/pink_kurta_lady_v1.png"
RECEIPT="videos/private-qa/"+JOB_ID+"/scene01.receipt.json"
MP4="videos/private-qa/"+JOB_ID+"/scene01.mp4"
# $0.89/h initially. Even $1.50/h over 38 minutes is < $1.
POD_PROVIDER_TTL_MINUTES=38
# Each of these models offers >=24GiB physical VRAM. Prefer 32GB, then
# established RTX4090, and use cost-effective RTX PRO4000 if it is the only
# EU-RO-1 stock. All are for the SAME one approved $1 pilot.
GPU_PREFERENCE=("NVIDIA RTX PRO 4500 Blackwell",
                "NVIDIA GeForce RTX 4090",
                "NVIDIA RTX PRO 4000 Blackwell")
OWN_POLL_MAX_MINUTES=30
MAX_ACCEPTED_RATE_USD_PER_HR=Decimal("1.50")

class PilotError(RuntimeError): pass

def safe_api(key,path,method="GET",data=None,timeout=25,opener=urlopen):
    if not key or "\n" in key or "\r" in key:
        raise PilotError("RUNPOD_KEY_MISSING")
    if not (path in ("/pods","/catalog/gpus",
                     "/catalog/datacenters?include=GPU_AVAILABILITY",
                     "/network-volumes/"+VOLUME)
            or re.fullmatch(r"/pods/[A-Za-z0-9_-]{5,80}",path)
            or path=="/registries"
            or re.fullmatch(r"/registries/[A-Za-z0-9_-]{5,80}",path)):
        raise PilotError("NON_ALLOWLISTED_API_PATH")
    if method in ("POST","DELETE"):
        if path=="/pods" or path.startswith("/network-volumes"):
            raise PilotError("REFUSE_REST_POD_CREATE_OR_VOLUME_DELETE")
    headers={"Authorization":"Bearer "+key,"Accept":"application/json"}
    if data is not None:headers["Content-Type"]="application/json"
    req=Request(BASE+path, data=json.dumps(data).encode() if data is not None else None,
                method=method, headers=headers)
    try:
        with opener(req,timeout=timeout) as r:
            if r.status==204:return {"deleted":True}
            if r.status not in (200,201,202):
                raise PilotError("BAD_REST_RESPONSE_CODE")
            b=r.read(500001)
            if len(b)>500000:raise PilotError("REST_RESPONSE_TOO_LARGE")
            return json.loads(b) if b.strip() else {}
    except HTTPError as ex:
        if ex.code==404 and method=="GET" and path.startswith("/pods/"):
            return {"deleted":True}
        raise PilotError("RUNPOD_REST_HTTP_"+str(ex.code)) from None
    except (URLError,OSError,TimeoutError,ValueError):
        raise PilotError("RUNPOD_REST_NETWORK_ERROR") from None

def graphql_create(key, payload, opener=urlopen):
    if not key:raise PilotError("GRAPHQL_WRITE_KEY_MISSING")
    query=("mutation TrustfolioWan5FirstPilot($input:PodFindAndDeployOnDemandInput)"
           " { podFindAndDeployOnDemand(input:$input)"
           " { id name imageName costPerHr } }")
    body=json.dumps({"query":query,"variables":{"input":payload}}).encode()
    req=Request(GRAPHQL+"?"+urlencode({"api_key":key}),data=body,method="POST",
                headers={"Content-Type":"application/json","Accept":"application/json"})
    try:
        with opener(req,timeout=40) as r:
            data=json.loads(r.read(100001))
    except HTTPError as exc:
        raise PilotError("GRAPHQL_CREATE_HTTP_"+str(exc.code)+"_RECONCILE_REQUIRED") from None
    except (URLError,OSError,TimeoutError,ValueError):
        raise PilotError("GRAPHQL_CREATE_AMBIGUOUS_RECONCILE_REQUIRED") from None
    if data.get("errors"):
        message="; ".join(str(x.get("message","")) for x in data["errors"] if isinstance(x,dict))
        # Do not log provider error text (might embed authentication or image URLs).
        if "no available" in message.lower() or "out of stock" in message.lower():
            raise PilotError("GPU_STOCK_UNAVAILABLE_NO_RENDER")
        raise PilotError("GRAPHQL_CREATE_REFUSED_RECONCILE_REQUIRED")
    pod=data.get("data",{}).get("podFindAndDeployOnDemand")
    if not isinstance(pod,dict) or not pod.get("id"):
        raise PilotError("GRAPHQL_CREATE_NO_POD_ID_RECONCILE_REQUIRED")
    return pod

def validate_target(p):
    if not isinstance(p,dict) or p.get("name")!=NAME:
        raise PilotError("TARGET_POD_NAME_WRONG")
    if p.get("dataCenterId")!=DATACENTER:
        raise PilotError("TARGET_POD_REGION_WRONG")
    mounts=p.get("mounts")
    if not isinstance(mounts,dict) or mounts.get("network")!=[
        {"volumeId":VOLUME,"path":"/workspace"}]:
        raise PilotError("TARGET_POD_MOUNT_WRONG")
    if not re.fullmatch("[A-Za-z0-9_-]{5,80}",str(p.get("id",""))):
        raise PilotError("TARGET_POD_ID_INVALID")
    return p["id"]

def find_owned_pods(key, requester=safe_api):
    data=requester(key,"/pods")
    pods=data.get("pods")
    if not isinstance(pods,list):raise PilotError("RUNPOD_PODS_LIST_SCHEMA_CHANGED")
    return [x for x in pods if isinstance(x,dict) and x.get("name")==NAME]

def kill_owned_pods(key, requester=safe_api, sleep=time.sleep):
    # Handles ambiguous network errors during CREATE where the response might
    # be lost but billing already started. Never touch any other Pod.
    existing=find_owned_pods(key,requester)
    if len(existing)>1:raise PilotError("MULTIPLE_PILOT_PODS_MANUAL_ESCALATION")
    if not existing:return "NO_OWNED_GPU_POD"
    pid=validate_target(existing[0])
    fresh=requester(key,"/pods/"+pid)
    if fresh.get("deleted"):return "ALREADY_REMOVED"
    validate_target(fresh)
    requester(key,"/pods/"+pid,"DELETE")
    for attempt in range(12):
        check=requester(key,"/pods/"+pid)
        if check.get("deleted"):return "DELETE_GET_404_CONFIRMED"
        if attempt<11:sleep(3)
    raise PilotError("CRITICAL_PILOT_POD_DELETE_NOT_CONFIRMED")

def make_s3():
    a=os.environ.get("RUNPOD_S3_ACCESS_KEY_ID","")
    b=os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY","")
    if not a or not b:raise PilotError("S3_WRITE_CREDENTIALS_MISSING")
    return boto3.client("s3",region_name="eu-ro-1",
        endpoint_url="https://s3api-eu-ro-1.runpod.io",
        aws_access_key_id=a,aws_secret_access_key=b,
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      connect_timeout=25,read_timeout=180,
                      retries={"max_attempts":3,"mode":"standard"}))

def get_object(s3,key,max_bytes):
    try:obj=s3.get_object(Bucket=S3_BUCKET,Key=key)
    except Exception as exc:
        code=str(getattr(exc,"response",{}).get("Error",{}).get("Code",""))
        if code in ("NoSuchKey","404","NotFound"):return None
        raise PilotError("S3_READ_FAILED") from None
    size=int(obj.get("ContentLength",-1))
    if size<0 or size>max_bytes:
        obj["Body"].close()
        raise PilotError("S3_OBJECT_TOO_LARGE_OR_LENGTH_INVALID")
    data=obj["Body"].read(max_bytes+1)
    obj["Body"].close()
    if len(data)!=size:raise PilotError("S3_TRUNCATED_OR_UNEXPECTED_BYTES")
    return data

def verify_hero(s3):
    data=get_object(s3,S3_HERO,IMAGE_BYTES)
    if data is None or len(data)!=IMAGE_BYTES or hashlib.sha256(data).hexdigest()!=IMAGE_SHA:
        raise PilotError("ORIGINAL_CHARACTER_S3_SHA_NOT_VERIFIED")

def check_fresh_output(s3):
    if get_object(s3,RECEIPT,64000) is not None:
        raise PilotError("PREEXISTING_VIDEO_RECEIPT_REFUSE_SECOND_PAID_TEST")
    if get_object(s3,MP4,100*1024*1024) is not None:
        raise PilotError("PREEXISTING_VIDEO_REFUSE_SECOND_PAID_TEST")

def verify_mp4_s3(s3,receipt):
    if receipt.get("status")!="VOLUME_MP4_WRITTEN_PENDING_S3_GET_VERIFICATION":
        raise PilotError("WORKER_RECEIPT_BAD_STATUS")
    if (receipt.get("job_id")!=JOB_ID or receipt.get("s3_key")!=MP4
        or receipt.get("character_sha256")!=IMAGE_SHA
        or receipt.get("social_publishing") is not False
        or receipt.get("gpu_pod_destroyed") is not False):
        raise PilotError("WORKER_RECEIPT_WRONG_JOB_OR_POLICY")
    expected_hash=receipt.get("sha256","")
    size=receipt.get("bytes",0)
    duration=receipt.get("seconds")
    if (not re.fullmatch(r"[0-9a-f]{64}",str(expected_hash))
        or not isinstance(size,int) or not 10240<=size<=200*1024*1024
        or not isinstance(duration,(float,int)) or not 4.8<=duration<=5.3):
        raise PilotError("WORKER_RECEIPT_INVALID_MP4_META")
    obj=s3.get_object(Bucket=S3_BUCKET,Key=MP4)
    h=hashlib.sha256()
    count=0
    try:
        if int(obj.get("ContentLength",-1))!=size:
            raise PilotError("MP4_S3_SIZE_MISMATCH")
        while True:
            chunk=obj["Body"].read(2*1024*1024)
            if not chunk:break
            count+=len(chunk)
            if count>size:raise PilotError("MP4_S3_OVERSIZE")
            h.update(chunk)
    finally:obj["Body"].close()
    if count!=size or h.hexdigest()!=expected_hash:
        raise PilotError("MP4_S3_SHA256_MISMATCH")
    return {"status":"FIRST_GENUINE_WAN5_MP4_VERIFIED_PRIVATE_QA",
            "mp4_s3_key":MP4,"size_bytes":size,"sha256":expected_hash,
            "duration_seconds":duration,"published":False}

def check_cost_and_availability(read_key):
    p,m=read_inputs()
    if p["gpu_usd_spend_approved"]!=1 or p["clip_duration_seconds"]!=5:
        raise PilotError("USER_APPROVAL_SCOPE_MISMATCH")
    v=api_read(read_key,BASE+"/network-volumes/"+VOLUME)
    if v.get("id")!=VOLUME or v.get("size")!=100 or v.get("dataCenter")!=DATACENTER:
        raise PilotError("EXISTING_NETWORK_VOLUME_MISMATCH")
    g=api_read(read_key,BASE+"/catalog/gpus")
    d=api_read(read_key,BASE+"/catalog/datacenters?include=GPU_AVAILABILITY")
    center=next((x for x in d.get("dataCenters",[])
                 if x.get("id")==DATACENTER),None)
    if not isinstance(center,dict):
        raise PilotError("EU_RO_1_CATALOG_MISSING")
    available={
        x.get("id"):x.get("availability")
        for x in center.get("gpuAvailability",[])
        if isinstance(x,dict)
    }
    gpu_by_id={x.get("id"):x for x in g.get("gpus",[]) if isinstance(x,dict)}
    options=[]
    for gpu_id in GPU_PREFERENCE:
        # Inventory LOW is a hint, not a guaranteed allocation; the inventory
        # may temporarily omit stock during fleet synchronization. An actual
        # GraphQL allocation is authoritative. Never skip live price gating.
        price=gpu_by_id.get(gpu_id,{}).get("price",{})
        try:rate=Decimal(str(price.get("secure")))
        except Exception:continue
        if (rate.is_finite() and rate>0
            and rate<=MAX_ACCEPTED_RATE_USD_PER_HR
            and rate*POD_PROVIDER_TTL_MINUTES/60<Decimal("1")):
            stock=available.get(gpu_id,"NOT_LISTED")
            options.append((gpu_id,rate,stock))
    if not options:
        raise PilotError("NO_APPROVED_GPU_WITH_LIVE_PRICE_WITHIN_1_USD")
    # Attempt provider allocation with the best in-region hint first.
    present=[x for x in options if x[2] in ("LOW","MEDIUM","HIGH")]
    gpu_id,rate,stock=(present or options)[0]
    return {"gpu_type":gpu_id,
            "rate_usd_per_hour":str(rate),"stock":stock,
            "max_gpu_usd_at_38m":str(round(rate*POD_PROVIDER_TTL_MINUTES/60,4))}

def create_registry(key,github_token,requester=safe_api):
    if not github_token:raise PilotError("GITHUB_PACKAGES_PULL_TOKEN_MISSING")
    # Github GITHUB_TOKEN is scoped to Actions and expires; delete registry
    # credential after Pod cleanup, never print its contents.
    data=requester(key,"/registries","POST",
        {"name":"trustfolio-wan5-one-time-ghcr",
         "username":os.environ.get("GITHUB_ACTOR","jayantjos"),
         "password":github_token})
    x=data.get("registry",data)
    rid=x.get("id") if isinstance(x,dict) else None
    if not isinstance(rid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",rid):
        raise PilotError("REGISTRY_AUTH_CREATE_ID_MISSING")
    return rid

def make_graphql_payload(registry_id,now=None,gpu_id=None):
    if not re.fullmatch("[A-Za-z0-9_-]{5,80}",registry_id):
        raise PilotError("REGISTRY_ID_INVALID")
    gpu_id=gpu_id or "NVIDIA GeForce RTX 4090"
    if gpu_id not in GPU_PREFERENCE:raise PilotError("GPU_NOT_IN_24GB_PLUS_ALLOWLIST")
    now=now or datetime.now(timezone.utc)
    deadline=(now+timedelta(minutes=POD_PROVIDER_TTL_MINUTES)).replace(microsecond=0)
    return {"cloudType":"SECURE",
            "gpuTypeId":gpu_id,"gpuCount":1,
            "dataCenterId":DATACENTER,
            "networkVolumeId":VOLUME,
            "volumeMountPath":"/workspace",
            "containerDiskInGb":25,
            "name":NAME,"imageName":IMAGE,
            "containerRegistryAuthId":registry_id,
            "ports":"","startJupyter":False,"startSsh":False,
            "terminateAfter":deadline.isoformat().replace("+00:00","Z"),
            "env":[{"key":"TRUSTFOLIO_PRIVATE_QA","value":"yes"},
                   {"key":"TRUSTFOLIO_GPU_JOB_ID","value":JOB_ID}]}

def polling_for_mp4(s3,write_key,deadline_seconds=OWN_POLL_MAX_MINUTES*60,
                    interval=20,sleep=time.sleep):
    started=time.monotonic()
    while time.monotonic()-started<deadline_seconds:
        try:r=get_object(s3,RECEIPT,64000)
        except PilotError:
            r=None
        if r is not None:
            try:receipt=json.loads(r)
            except (ValueError,TypeError):raise PilotError("CORRUPTED_GPU_RECEIPT") from None
            return verify_mp4_s3(s3,receipt)
        owned=find_owned_pods(write_key)
        if len(owned)!=1:raise PilotError("GPU_POD_DISAPPEARED_OR_DUPLICATED")
        pod=owned[0]
        if pod.get("status") in ("EXITED","TERMINATED","FAILED","ERROR"):
            raise PilotError("GPU_POD_EXITED_WITHOUT_MP4")
        sleep(interval)
    raise PilotError("GPU_RENDER_TIMEOUT_WITHIN_BUDGET")

def run():
    read_key=os.environ.get("RUNPOD_API_KEY","")
    write_key=os.environ.get("RUNPOD_POD_WRITE_KEY","")
    github_token=os.environ.get("GHCR_GITHUB_TOKEN","")
    if not read_key or not write_key:
        raise PilotError("RUNPOD_READ_OR_WRITE_KEY_MISSING")
    if os.environ.get("TRUSTFOLIO_PAID_FIRST_TEST")!="yes":
        raise PilotError("PAID_ONE_TIME_TEST_NOT_ARMED")
    s3=make_s3()
    verified=None
    registry_id=None
    cleanup_result="NOT_NEEDED"
    report={"status":"NOT_STARTED","video_rendered":False,"gpu_pod_deleted":False}
    try:
        cost=check_cost_and_availability(read_key)
        print("PILOT_GPU_TYPE="+cost["gpu_type"],flush=True)
        print("PILOT_GPU_STOCK_HINT="+cost["stock"],flush=True)
        print("PILOT_GPU_QUOTE_USD_HR="+cost["rate_usd_per_hour"],flush=True)
        print("PILOT_GPU_MAX_COST_UNDER_1_USD="+cost["max_gpu_usd_at_38m"],flush=True)
        verify_hero(s3)
        check_fresh_output(s3)
        if find_owned_pods(write_key):
            raise PilotError("ALREADY_EXISTING_PILOT_POD_PREVENT_DUPLICATE")
        registry_id=create_registry(write_key,github_token)
        payload=make_graphql_payload(registry_id,gpu_id=cost["gpu_type"])
        print("PILOT_PROVIDER_TERMINATE_AFTER="+payload["terminateAfter"],flush=True)
        print("PILOT_CREATING_REAL_GPU=TRUE",flush=True)
        pod=graphql_create(write_key,payload)
        pod_id=str(pod["id"])
        print("PILOT_GPU_CREATED_ID="+pod_id,flush=True)
        if pod.get("name")!=NAME or pod.get("imageName")!=IMAGE:
            raise PilotError("CREATED_GPU_POD_NAME_OR_IMAGE_MISMATCH")
        verified=polling_for_mp4(s3,write_key)
        print("PILOT_MP4_SHA256_VERIFIED="+verified["sha256"],flush=True)
        report={**verified,"video_rendered":True,"gpu_pod_deleted":False,
                "quote_usd_hr":cost["rate_usd_per_hour"]}
        return report
    finally:
        # Even ambiguous create errors or failed inference MUST attempt a scoped
        # clean-up before exiting; confirmation is GET 404.
        try:
            cleanup_result=kill_owned_pods(write_key)
            report["gpu_pod_deleted"]=cleanup_result in (
                "NO_OWNED_GPU_POD","DELETE_GET_404_CONFIRMED","ALREADY_REMOVED")
            print("PILOT_GPU_DELETE_RESULT="+cleanup_result,flush=True)
        except Exception:
            report["gpu_pod_deleted"]=False
            print("PILOT_CRITICAL_CLEANUP_UNCONFIRMED_REAPER_EXPECTED",flush=True)
        if registry_id:
            try:
                safe_api(write_key,"/registries/"+registry_id,"DELETE")
                print("PILOT_TEMP_GHCR_CREDENTIAL_REMOVED=true",flush=True)
            except Exception:
                print("PILOT_TEMP_GHCR_CREDENTIAL_REMOVAL_FAILED",flush=True)
        Path("output").mkdir(exist_ok=True)
        Path("output/wan5-first-paid-test.json").write_text(
            json.dumps(report,indent=2)+"\n")
        if not report["gpu_pod_deleted"]:
            raise PilotError("CRITICAL_PAID_GPU_TERMINATION_NOT_CONFIRMED")

def main():
    try:
        result=run()
        print("PILOT_FINAL="+result["status"],flush=True)
        return 0
    except PilotError as exc:
        print("PILOT_FINAL=BLOCKED_"+str(exc),flush=True)
        return 1
    except Exception:
        print("PILOT_FINAL=UNEXPECTED_FAILURE_CHECK_INDEPENDENT_REAPER",flush=True)
        return 1

if __name__=="__main__":
    sys.exit(main())
