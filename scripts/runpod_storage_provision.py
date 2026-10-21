#!/usr/bin/env python3
"""Fail-closed RunPod 100GB Standard network volume controller.

Default: dry-run only. Never create GPU Pods or touch social publishing.
Actual create requires a separate scoped WRITE key and exact affirmative marker.
"""
import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from scripts.runpod_storage_discovery import get_json, list_all, Blocked

NAME = "trustfolio-wan-models-v1"
REGION = "EU-RO-1"
SIZE = 100
TYPE = "STANDARD"
CONFIRM = "CREATE_EXACTLY_100GB_EU-RO-1"
URL = "https://api.runpod.io/v2/network-volumes"

def check_policy(path):
    policy=json.loads(Path(path).read_text(encoding="utf-8"))
    if (policy.get("approval")!="MONTHLY_STORAGE_COST_ONLY"
        or policy.get("name")!=NAME or policy.get("data_center")!=REGION
        or policy.get("network_volume_type")!=TYPE
        or type(policy.get("volume_size_gb")) is not int
        or policy["volume_size_gb"]!=SIZE
        or policy.get("gpu_instance_creation_enabled") is not False
        or policy.get("video_publishing_enabled") is not False):
        raise Blocked("POLICY_REFUSED")
    monthly=Decimal(str(policy["standard_public_price_usd_gb_month"]))*Decimal(SIZE)
    if monthly>Decimal(str(policy["max_estimated_usd_month"])) or monthly!=Decimal("7.00"):
        raise Blocked("STORAGE_ESTIMATE_OVER_APPROVAL")
    return policy

def build_dry_plan(path):
    policy=check_policy(path)
    return {"status":"PREPARED_NOT_CREATED", "name":NAME,"datacenter":REGION,
            "size_gb":SIZE,"type":TYPE,"public_estimate_usd_month":7,
            "gpu_created":False,"volume_created":False,
            "needs_scoped_write_key":True,
            "warning":"This is NOT a binding quote; volume continues to accrue cost until deleted."}

def preflight(key, reader=get_json):
    # List current resources, plus validate same-region GPU/Standard storage
    existing=list_all(key,"/network-volumes","networkVolumes",reader=reader)
    matching=[v for v in existing if isinstance(v,dict) and v.get("name")==NAME]
    if len(matching)>1:
        raise Blocked("DUPLICATE_VOLUME_NAME")
    if matching:
        v=matching[0]
        if v.get("dataCenter")==REGION and v.get("size")==SIZE and v.get("type")==TYPE:
            return "ALREADY_EXISTS",v
        raise Blocked("CONFLICTING_EXISTING_VOLUME")
    centers=reader(key,"/catalog/datacenters",{"include":"GPU_AVAILABILITY"}).get("dataCenters")
    if not isinstance(centers,list):
        raise Blocked("CATALOG_UNAVAILABLE")
    candidate=next((v for v in centers if isinstance(v,dict) and v.get("id")==REGION),None)
    if not candidate or TYPE not in candidate.get("networkVolumeTypes",[]):
        raise Blocked("DATACENTER_STANDARD_NOT_AVAILABLE")
    suitable=any(isinstance(g,dict) and g.get("id")=="NVIDIA GeForce RTX 4090"
             and g.get("availability") in ("HIGH","MEDIUM")
             for g in candidate.get("gpuAvailability",[]))
    if not suitable:
        raise Blocked("GPU_STOCK_NOT_SUITABLE_AT_PURCHASE_TIME")
    return "READY", None

def create(key, policy_path, confirmation, writer=None, reader=get_json):
    check_policy(policy_path)
    if confirmation!=CONFIRM:
        raise Blocked("EXACT_CONFIRMATION_REQUIRED")
    if not key or "\n" in key or "\r" in key:
        raise Blocked("WRITE_KEY_MISSING")
    state,volume=preflight(key,reader=reader)
    if state=="ALREADY_EXISTS":
        return {"status":state,"volume_id":volume.get("id"),"created_now":False}
    body=json.dumps({"name":NAME,"size":SIZE,"dataCenter":REGION,"type":TYPE}).encode()
    req=Request(URL, data=body, method="POST", headers={
       "Authorization":"Bearer "+key,
       "Accept":"application/json","Content-Type":"application/json"})
    writer=writer or urlopen
    try:
        with writer(req,timeout=25) as response:
            if response.status!=201:
                raise Blocked("CREATE_HTTP_"+str(response.status))
            result=json.loads(response.read(1000001))
    except HTTPError as e:
        raise Blocked("CREATE_HTTP_"+str(e.code)) from None
    except (URLError,TimeoutError,OSError,ValueError):
        # Might have created on server: do not retry blindly, inspect by name.
        raise Blocked("CREATE_UNKNOWN_RESULT_CHECK_CONSOLE_BEFORE_RETRY") from None
    if not isinstance(result,dict) or not isinstance(result.get("id"),str):
        raise Blocked("CREATE_UNEXPECTED_RESPONSE_CHECK_CONSOLE")
    if any(result.get(k)!=v for k,v in
           (("name",NAME),("size",SIZE),("dataCenter",REGION),("type",TYPE))):
        raise Blocked("CREATE_RESPONSE_MISMATCH_CHECK_CONSOLE")
    # Confirm re-list result, without leaking account state.
    state,verified=preflight(key,reader=reader)
    if state!="ALREADY_EXISTS" or verified.get("id")!=result["id"]:
        raise Blocked("CREATED_BUT_NOT_VERIFIED_CHECK_CONSOLE")
    return {"status":"CREATED_AND_VERIFIED","volume_id":result["id"],
            "created_now":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--policy",default="config/runpod_storage_purchase.json")
    parser.add_argument("--create",action="store_true",help="Paid action: requires scoped secret and exact confirmation")
    parser.add_argument("--confirmation",default="")
    parser.add_argument("--output",default="output/runpod-storage-provision-plan.json")
    args=parser.parse_args()
    try:
        if args.create:
            if os.environ.get("TRUSTFOLIO_STORAGE_PAID_OPERATION_ENABLED")!="yes":
                raise Blocked("PAID_OPERATION_DISABLED")
            report=create(os.environ.get("RUNPOD_STORAGE_WRITE_KEY",""),args.policy,args.confirmation)
        else:
            report=build_dry_plan(args.policy)
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print("RUNPOD_NETWORK_VOLUME="+report["status"])
        if report.get("volume_id"):
            print("::add-mask::"+report["volume_id"])
        return 0
    except (Blocked,KeyError,ValueError,OSError) as exc:
        print("RUNPOD_NETWORK_VOLUME=BLOCKED_"+str(exc))
        return 1

if __name__=="__main__":
    sys.exit(main())
