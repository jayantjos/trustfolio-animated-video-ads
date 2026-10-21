#!/usr/bin/env python3
"""TrustFolio first 5s genuine Wan2.2 test: GET/HEAD ONLY preflight.

No GitHub Actions process running this script may start, modify or delete Pods.
Blockers are reported independently; unverified provider quote is never assumed.
"""
import hashlib, json, os, sys
from pathlib import Path
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PATH="config/first_wan5_gpu_test.json"
MODEL="config/wan_verified_model_manifest.json"
BASE="https://api.runpod.io/v2"
VOLUME="1bch597yrz"
GPU="NVIDIA GeForce RTX 4090"
DATACENTER="EU-RO-1"

def api_read(key,url,opener=urlopen):
    if not key or "\n" in key or "\r" in key:
        raise ValueError("RUNPOD_READ_KEY_MISSING")
    if url not in (BASE+"/pods",BASE+"/catalog/gpus",
                   BASE+"/catalog/datacenters?include=GPU_AVAILABILITY",
                   BASE+"/network-volumes/"+VOLUME):
        raise ValueError("ENDPOINT_NOT_READ_ONLY_ALLOWLISTED")
    req=Request(url,method="GET",headers={
        "Authorization":"Bearer "+key,"Accept":"application/json"})
    try:
        with opener(req,timeout=30) as resp:
            if resp.status!=200:
                raise ValueError("HTTP_NOT_200")
            body=resp.read(1500001)
            if len(body)>1500000:
                raise ValueError("RESPONSE_TOO_LARGE")
        return json.loads(body)
    except HTTPError as exc:
        raise ValueError("RUNPOD_READ_HTTP_"+str(exc.code)) from None
    except (URLError,TimeoutError,OSError):
        raise ValueError("RUNPOD_READ_UNAVAILABLE") from None

def read_inputs(config=PATH,model_path=MODEL):
    p=json.loads(Path(config).read_text())
    m=json.loads(Path(model_path).read_text())
    if not (
       p["gpu_usd_spend_approved"]==1.0
       and p["clip_duration_seconds"]==5
       and p["gpu_type"]==GPU
       and p["network_volume_id"]==VOLUME
       and p["datacenter"]==DATACENTER
       and p["hero_bytes"]==2484010
       and p["hero_sha256"]=="7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"
       and p["social_publishing"] is False
       and p["requires_real_inference"] is True
       and p["video_status"]=="PREPARED_NOT_RENDERED"
       and m["expected_total_bytes"]==34180083066
       and len(m["objects"])==9
    ):
       raise ValueError("FIRST_TEST_SCOPE_MISMATCH")
    return p,m

def price_within_usd_one(quote,minutes=60):
    try:
        value=Decimal(str(quote))
    except (InvalidOperation,ValueError,TypeError):
        return False
    return (value.is_finite() and value>0 and
            value*Decimal(minutes)/Decimal(60)<=Decimal("1"))

def check_catalog(gpus,centers):
    obj=next((x for x in gpus.get("gpus",[]) if x.get("id")==GPU),None)
    dc=next((x for x in centers.get("dataCenters",[]) if x.get("id")==DATACENTER),None)
    if not isinstance(obj,dict) or not isinstance(dc,dict):
        return {"quote_usd_hour":None,"stock":"UNKNOWN","rate_within_cap":False}
    quoted=obj.get("price",{}).get("secure")
    avail=next((x.get("availability") for x in dc.get("gpuAvailability",[])
            if x.get("id")==GPU), "UNKNOWN")
    return {"quote_usd_hour":quoted,"stock":avail,
            "rate_within_cap":price_within_usd_one(quoted,60)}

def evaluate(p,model,vol,pods,catalog,hero,is_write_key_present):
    problems=[]
    if not isinstance(vol,dict) or (vol.get("id")!=VOLUME or vol.get("size")!=100
      or vol.get("dataCenter")!=DATACENTER or vol.get("type")!="STANDARD"):
        problems.append("EXISTING_VOLUME_NOT_VERIFIED")
    if any(x.get("status") in ("PROVISIONING","STARTING","RUNNING","EXITED")
            and x.get("name","").startswith("trustfolio-video-")
            for x in pods.get("pods",[]) if isinstance(x,dict)):
        problems.append("POSSIBLE_EXISTING_VIDEO_POD")
    if hero is not True:
        problems.append("ORIGINAL_MASTER_ART_NOT_ON_S3")
    if not is_write_key_present:
        problems.append("RUNPOD_POD_WRITE_KEY_NOT_IN_GITHUB_SECRETS")
    if catalog["stock"] not in ("MEDIUM","HIGH"):
        problems.append("EU_RO_1_GPU_NOT_RELIABLY_AVAILABLE")
    if not catalog["rate_within_cap"]:
        problems.append("GPU_HOURLY_QUOTE_NOT_WITHIN_ONE_DOLLAR")
    # These are mandatory and not bypassable just because read-only APIs passed.
    problems += [
        "PINNED_WAN_GPU_WORKER_NOT_DEPLOYED",
        "PROVIDER_SIDE_TERMINATION_LIMIT_NOT_CONFIRMED",
        "INDEPENDENT_PAID_GPU_REAPER_NOT_LIVE",
        "REAL_WAN_5_SECOND_OUTPUT_NOT_YET_RENDERED",
    ]
    return {"status":"NOT_READY_NO_GPU_CREATED",
      "model_files_expected":len(model["objects"]),
      "approved_gpu_usd":p["gpu_usd_spend_approved"],
      "hourly_quote_usd":catalog["quote_usd_hour"],
      "region_gpu_stock":catalog["stock"],
      "volume_id":VOLUME,
      "character_master_s3_verified":bool(hero),
      "runpod_pod_write_secret_present":bool(is_write_key_present),
      "blockers":problems,"gpu_pod_created":False,
      "mp4_rendered":False,"publishing_enabled":False}


def verify_hero_s3_get(s3,key,expected_bytes,expected_sha):
    """Verify exact signed S3 object content, never just metadata or HEAD."""
    import hashlib
    if (key!="assets/characters/shared/pink_kurta_lady_v1.png"
        or expected_bytes!=2484010
        or expected_sha!="7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"):
        raise ValueError("UNAPPROVED_CHARACTER_REFERENCE")
    r=s3.get_object(Bucket=VOLUME,Key=key)
    body=r.get("Body")
    if body is None:raise ValueError("S3_CHARACTER_BODY_MISSING")
    try:
        if int(r.get("ContentLength",-1))!=expected_bytes:
            return False
        digest=hashlib.sha256()
        count=0
        while True:
            chunk=body.read(1024*1024)
            if not chunk:break
            count+=len(chunk)
            if count>expected_bytes:return False
            digest.update(chunk)
        return count==expected_bytes and digest.hexdigest()==expected_sha
    finally:
        body.close()

def main():
    try:
        p,m=read_inputs()
        read=os.environ.get("RUNPOD_API_KEY","")
        v=api_read(read,BASE+"/network-volumes/"+VOLUME)
        pods=api_read(read,BASE+"/pods")
        gpus=api_read(read,BASE+"/catalog/gpus")
        centers=api_read(read,BASE+"/catalog/datacenters?include=GPU_AVAILABILITY")
        catalog=check_catalog(gpus,centers)
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        a=os.environ.get("RUNPOD_S3_ACCESS_KEY_ID","")
        b=os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY","")
        if not a or not b:raise ValueError("S3_CREDS_NOT_CONNECTED")
        s3=boto3.client("s3",endpoint_url="https://s3api-eu-ro-1.runpod.io",
            region_name="eu-ro-1",aws_access_key_id=a,aws_secret_access_key=b,
            config=Config(signature_version="s3v4",s3={"addressing_style":"path"}))
        try:
            # Read the actual bytes: RunPod S3 HEAD metadata may not reflect
            # a successfully PUT and GET verified original PNG.
            hero=verify_hero_s3_get(s3,p["hero_s3_key"],
                                    p["hero_bytes"],p["hero_sha256"])
        except ClientError as exc:
            if exc.response.get("Error",{}).get("Code") in ("404","NoSuchKey","NotFound"):
                hero=False
            else:raise
        report=evaluate(p,m,v,pods,catalog,hero,
                  bool(os.environ.get("RUNPOD_POD_WRITE_KEY")))
        target=Path("output/first-wan5-gpu-preflight.json")
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(report,indent=2)+"\n")
        print("WAN5_PREFLIGHT="+report["status"])
        print("GPU_RATE_USD_PER_HOUR="+str(report["hourly_quote_usd"]))
        print("GPU_STOCK="+str(report["region_gpu_stock"]))
        print("APPROVED_CHARACTER_ON_S3="+str(report["character_master_s3_verified"]))
        print("POD_WRITE_SECRET_PRESENT="+str(report["runpod_pod_write_secret_present"]))
        for x in report["blockers"]:print("BLOCKER="+x)
        print("GPU_CREATED=false")
        return 0
    except Exception as exc:
        print("WAN5_PREFLIGHT=FAILED_READ_ONLY_API_OR_POLICY")
        print("ERROR_CATEGORY="+(str(exc) if isinstance(exc,ValueError) else "PROVIDER_SDK_ERROR"))
        return 1
if __name__=="__main__":sys.exit(main())
