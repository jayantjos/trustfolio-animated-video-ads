#!/usr/bin/env python3
"""RunPod storage and GPU location inventory: strictly GET requests, NO GPU/spend."""
import json, os, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

BASE = "https://api.runpod.io/v2"
ALLOW = ("/pods", "/network-volumes", "/catalog/datacenters")
GPUS = {
    "NVIDIA RTX A6000": 48, "NVIDIA A40": 48, "NVIDIA L40S": 48,
    "NVIDIA RTX 6000 Ada": 48,
    "NVIDIA GeForce RTX 4090": 24, "NVIDIA GeForce RTX 3090": 24
}

class Blocked(RuntimeError):
    pass

def get_json(key, endpoint, params=None, opener=urlopen):
    if not key or "\n" in key or "\r" in key:
        raise Blocked("KEY_MISSING_OR_INVALID")
    if endpoint not in ALLOW:
        raise Blocked("UNAPPROVED_ENDPOINT")
    url=BASE+endpoint+("?" + urlencode(params) if params else "")
    request=Request(url, method="GET", headers={
        "Authorization":"Bearer "+key, "Accept":"application/json"})
    try:
        with opener(request,timeout=25) as response:
            if response.status!=200: raise Blocked("HTTP_"+str(response.status))
            raw=response.read(3000001)
        if len(raw)>3000000: raise Blocked("RESPONSE_TOO_LARGE")
        body=json.loads(raw)
        if not isinstance(body,dict): raise Blocked("INVALID_RESPONSE")
        return body
    except HTTPError as e:
        raise Blocked("HTTP_"+str(e.code)) from None
    except (URLError,TimeoutError,ValueError,OSError):
        raise Blocked("NETWORK_OR_RESPONSE_ERROR") from None

def list_all(key,endpoint,field,reader=get_json):
    results=[];cursor=None;seen=set()
    for _ in range(10):
        args={"limit":100}
        if cursor: args["cursor"]=cursor
        data=reader(key,endpoint,args)
        items=data.get(field)
        if not isinstance(items,list): raise Blocked(field+"_MISSING")
        results.extend(items)
        page=data.get("pagination") or {}
        if not page.get("hasNextPage"): return results
        cursor=page.get("nextCursor")
        if not isinstance(cursor,str) or not cursor or cursor in seen:
            raise Blocked("PAGINATION_INVALID")
        seen.add(cursor)
    raise Blocked("PAGINATION_LIMIT")

def summarize(pods,volumes,centers):
    candidates=[]
    for center in centers:
        if not isinstance(center,dict) or "STANDARD" not in center.get("networkVolumeTypes",[]):
            continue
        usable=[{"gpu":g["id"],"vram_gb":GPUS[g["id"]],"stock":g["availability"]}
                for g in center.get("gpuAvailability",[])
                if isinstance(g,dict) and g.get("id") in GPUS
                and g.get("availability") in ("HIGH","MEDIUM","LOW")]
        if usable:
            usable.sort(key=lambda g:(-g["vram_gb"],g["gpu"]))
            candidates.append({"datacenter":str(center.get("id","")),
                               "region":str(center.get("region","")),"gpus":usable})
    candidates.sort(key=lambda c:(c["region"]!="ASIA",c["datacenter"]))
    storage=sum(v.get("size",0) for v in volumes
                if isinstance(v,dict) and type(v.get("size")) is int and v["size"]>=0)
    return {"status":"READ_ONLY_SUCCESS", "storage_volume_count":len(volumes),
            "existing_storage_gb":storage, "pod_count":len(pods),
            "running_pods":sum(p.get("status")=="RUNNING" for p in pods if isinstance(p,dict)),
            "standard_storage_and_gpu_datacenters":candidates[:20],
            "candidate_count":len(candidates),
            "proposed_storage_gb":100, "proposed_storage_usd_month":7.0,
            "wan_ti2v_model_repository_gb":34.2,
            "actual_gpu_hourly_quote_verified":False,
            "charged_resources_created":False,"publishing_enabled":False}

def inventory(key,reader=get_json):
    try:
        pods=list_all(key,"/pods","pods",reader=reader)
    except Blocked as exc:
        raise Blocked("PODS_"+str(exc)) from None
    try:
        volumes=list_all(key,"/network-volumes","networkVolumes",reader=reader)
    except Blocked as exc:
        raise Blocked("NETWORK_VOLUMES_"+str(exc)) from None
    try:
        data=reader(key,"/catalog/datacenters",{"include":"GPU_AVAILABILITY"})
        if not isinstance(data.get("dataCenters"),list):
            raise Blocked("DATACENTERS_MISSING")
    except Blocked as exc:
        # Catalog may require permission unavailable to existing read-only key.
        # Never invent candidate availability when discovery is unauthorized.
        result=summarize(pods,volumes,[])
        result["status"]="PARTIAL_CATALOG_UNAVAILABLE"
        result["catalog_error"]=str(exc)
        result["candidate_count"]=None
        return result
    return summarize(pods,volumes,data["dataCenters"])

def main():
    try:
        result=inventory(os.environ.get("RUNPOD_API_KEY",""))
        path=Path("output/runpod-readonly-inventory.json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(result,indent=2)+"\n")
        print("RUNPOD_STORAGE_DISCOVERY=READ_ONLY_SUCCESS")
        for key in ("storage_volume_count","existing_storage_gb","running_pods","candidate_count"):
            print(key.upper()+"="+str(result[key]))
        summary=os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary,"a") as f:
                f.write("RunPod Read-only storage discovery: SUCCESS\n\n")
                f.write("Existing network volumes: "+str(result["storage_volume_count"])+"\n\n")
                f.write("Available standard-storage + suitable GPU datacenters: "+str(result["candidate_count"])+"\n\n")
                f.write("No GPU or volume created. Proposed 100GB costs about $7/month.\n")
    except Blocked as exc:
        print("RUNPOD_STORAGE_DISCOVERY=BLOCKED_"+str(exc))
        return 1
    return 0

if __name__=="__main__":
    sys.exit(main())
