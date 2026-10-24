#!/usr/bin/env python3
"""RunPod owned Pod read-only watchdog.

GitHub scheduled jobs are best effort and cannot guarantee hourly execution.
A provider-side independent terminate-after is required before paid GPU use.
"""
import json,os,sys
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from scripts.runpod_video_pod_cleanup import validate_owned_pod,UnsafeCleanup

def owned_stale_pods(pods,*,now=None,minutes=40):
    now=now or datetime.now(timezone.utc)
    if not isinstance(pods,list):
        raise ValueError("INVALID_PROVIDER_POD_LIST")
    found=[]
    for pod in pods:
        if not isinstance(pod,dict):continue
        name=pod.get("name","")
        if not isinstance(name,str) or not name.startswith("trustfolio-video-"):
            continue
        job_id=name[len("trustfolio-video-"):]
        try:validate_owned_pod(pod,pod.get("id",""),job_id)
        except UnsafeCleanup:continue
        created=pod.get("createdAt")
        if not created:continue
        try:timestamp=datetime.fromisoformat(created.replace("Z","+00:00"))
        except (ValueError,AttributeError):continue
        if timestamp.tzinfo is None:continue
        age=(now-timestamp).total_seconds()/60
        if age>=minutes and pod.get("status") not in ("TERMINATED",):
            found.append({"pod_id":pod["id"],"job_id":job_id,
                          "age_minutes":round(age,1),"status":pod.get("status")})
    return found

def main():
    key=os.environ.get("RUNPOD_API_KEY","")
    if not key:
        print("WATCHDOG=READ_ONLY_KEY_MISSING")
        return 1
    request=Request("https://api.runpod.io/v2/pods",method="GET",
        headers={"Authorization":"Bearer "+key,"Accept":"application/json"})
    try:
        with urlopen(request,timeout=30) as resp:
            if resp.status!=200:raise ValueError("WRONG_HTTP_STATUS")
            body=resp.read(2000001)
        if len(body)>2000000:raise ValueError("RESPONSE_TOO_LARGE")
        raw=json.loads(body)
        pods=raw.get("pods")
        stale=owned_stale_pods(pods)
        print("WATCHDOG=READ_ONLY_SCAN_SUCCESS")
        print("OWNED_STALE_GPU_COUNT="+str(len(stale)))
        out={"status":"STALLED_GPU_ALERT_REQUIRES_OPERATOR" if stale else "NO_STALE_OWNED_PODS",
             "owned_stale_pods":stale,"terminated_pods":0,
             "independent_reaper_live":False}
        os.makedirs("output",exist_ok=True)
        with open("output/runpod-video-gpu-watchdog.json","w") as f:
            json.dump(out,f,indent=2)
        if stale:
            # Failure notifies GitHub checks, it is not a cleanup guarantee.
            print("WATCHDOG_ACTION=ALERT_ONLY_NO_WRITE_KEY")
            return 2
        return 0
    except Exception:
        print("WATCHDOG=API_UNAVAILABLE_OR_INVALID_ALERT_REQUIRED")
        return 1
if __name__=="__main__":sys.exit(main())
