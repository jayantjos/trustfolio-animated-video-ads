#!/usr/bin/env python3
"""Safety-scoped independent RunPod Pod reaper, one TrustFolio pilot only.

This runs from DEFAULT branch on a best-effort 5-minute schedule. It only
DELETEs the exact verified TrustFolio GPU Pod mounted to its known 100GB
EU-RO-1 volume when either its logs show a fatal error or it exceeds the
35-minute stale threshold. No other Pod or any
volume will be touched. The provider-native auto-terminate TTL is separately
mandatory for paid creation; Actions scheduling is best-effort, not a hard TTL.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.wan5_live_log_guard import scan_container_logs

BASE="https://api.runpod.io/v2/pods"
NAME="trustfolio-video-wan5-laundry-first-20261021"
VOLUME="1bch597yrz"
DATACENTER="EU-RO-1"
STALE_MINUTES=35

class ReaperBlock(RuntimeError): pass

def request_json(key,path="",method="GET",opener=urlopen):
    if not key or "\n" in key or "\r" in key:
        raise ReaperBlock("POD_WRITE_API_KEY_MISSING")
    if not path == "" and not re.fullmatch(r"/[A-Za-z0-9_-]{5,80}",path):
        raise ReaperBlock("UNSAFE_POD_ID")
    if method=="DELETE" and not path:
        raise ReaperBlock("REFUSE_DELETE_LIST")
    if method not in ("GET","DELETE"):
        raise ReaperBlock("UNSAFE_HTTP_METHOD")
    req=Request(BASE+path,headers={
        "Authorization":"Bearer "+key,"Accept":"application/json"},method=method)
    try:
        with opener(req,timeout=25) as r:
            if r.status==204:return {"http_status":204}
            if r.status not in (200,202):
                raise ReaperBlock("RUNPOD_HTTP_UNEXPECTED")
            b=r.read(2000001)
            if len(b)>2000000:raise ReaperBlock("PODS_RESPONSE_TOO_BIG")
            return json.loads(b) if b.strip() else {"http_status":r.status}
    except HTTPError as exc:
        if exc.code==404:return {"deleted":True}
        raise ReaperBlock("RUNPOD_HTTP_"+str(exc.code)) from None
    except (URLError,ValueError,TimeoutError,OSError):
        raise ReaperBlock("RUNPOD_REQUEST_UNAVAILABLE") from None

def valid_target(pod,now=None,min_age_minutes=STALE_MINUTES):
    now=now or datetime.now(timezone.utc)
    if not isinstance(pod,dict) or pod.get("name")!=NAME:
        return False
    pid=pod.get("id","")
    if not isinstance(pid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",pid):
        raise ReaperBlock("TARGET_ID_INVALID")
    if pod.get("dataCenterId")!=DATACENTER:
        raise ReaperBlock("TARGET_DATACENTER_MISMATCH")
    mounts=pod.get("mounts",{})
    if not isinstance(mounts,dict) or mounts.get("network")!=[
        {"volumeId":VOLUME,"path":"/workspace"}]:
        raise ReaperBlock("TARGET_NETWORK_VOLUME_MISMATCH")
    stamp=pod.get("createdAt")
    if not isinstance(stamp,str):
        raise ReaperBlock("TARGET_CREATED_TIMESTAMP_MISSING")
    try:
        dt=datetime.fromisoformat(stamp.replace("Z","+00:00"))
    except ValueError:raise ReaperBlock("TARGET_CREATED_TIMESTAMP_INVALID") from None
    if dt.tzinfo is None:
        raise ReaperBlock("TARGET_TIMESTAMP_NOT_TIMEZONE_AWARE")
    minutes=(now-dt).total_seconds()/60
    if minutes<0:
        raise ReaperBlock("TARGET_CLOCK_SKEW")
    return minutes>=min_age_minutes

def scan(key,client=request_json,sleep=time.sleep,now=None,apply=False,
         log_scanner=scan_container_logs):
    body=client(key,"","GET")
    pods=body.get("pods")
    if not isinstance(pods,list):
        raise ReaperBlock("POD_LIST_SHAPE_INVALID")
    matches=[x for x in pods if isinstance(x,dict) and x.get("name")==NAME]
    if len(matches)>1:
        raise ReaperBlock("DUPLICATE_VIDEO_JOB_PODS_ALERT")
    if not matches:
        return {"status":"NO_TARGET_POD","pod_deleted":False}
    pod=matches[0]
    # Exact name alone is never enough to inspect, stop or destroy a Pod.
    valid_target(pod,now,min_age_minutes=0)
    stale=valid_target(pod,now)
    fatal=None
    if not stale:
        observed=log_scanner(key,pod["id"])
        fatal=observed.get("fatal")
    if not stale and not fatal:
        return {"status":"TARGET_NOT_STALE_OR_UNVERIFIED",
                "pod_deleted":False}
    reason="FATAL" if fatal else "STALE"
    if not apply:
        return {"status":"WOULD_DELETE_"+reason+"_OWNED_POD",
                "pod_deleted":False}
    pid=pod["id"]
    # Re-GET identity, region, volume, mount and age BEFORE any DELETE.
    fresh=client(key,"/"+pid,"GET")
    if fresh.get("deleted"):
        return {"status":"ALREADY_TERMINATED","pod_deleted":True}
    min_age=0 if fatal else STALE_MINUTES
    if fresh.get("id")!=pid or not valid_target(
            fresh,now,min_age_minutes=min_age):
        raise ReaperBlock("RECHECK_DID_NOT_MATCH_TARGET")
    client(key,"/"+pid,"DELETE")
    for attempt in range(7):
        current=client(key,"/"+pid,"GET")
        if current.get("deleted"):
            return {"status":reason+"_GPU_POD_DELETED_AND_404_CONFIRMED",
                    "pod_deleted":True,
                    "log_failure_class":fatal}
        if attempt<6:sleep(3)
    raise ReaperBlock("CRITICAL_DELETE_SENT_NOT_CONFIRMED")

def main():
    try:
        key=os.environ.get("RUNPOD_POD_WRITE_KEY","")
        apply=os.environ.get("TRUSTFOLIO_WAN5_REAPER_APPLY")=="yes"
        result=scan(key,apply=apply)
        os.makedirs("output",exist_ok=True)
        with open("output/wan5-independent-reaper.json","w") as f:
            json.dump({**result,"volume_preserved":True,
                       "other_pods_untouched":True},f,indent=2)
        print("TRUSTFOLIO_WAN5_REAPER="+result["status"])
        print("NETWORK_VOLUME_PRESERVED=true")
        return 0
    except ReaperBlock as exc:
        print("TRUSTFOLIO_WAN5_REAPER=BLOCKED_"+str(exc))
        return 1
if __name__=="__main__":sys.exit(main())
