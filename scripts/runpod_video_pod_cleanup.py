#!/usr/bin/env python3
"""Fail-closed ownership-scoped RunPod GPU Pod terminator.

No Pod is touched in default dry-run. Actual DELETE requires a separately
scoped key, exact expected Pod name and network-volume identity, an explicit
apply flag and a private operator-enable flag. This is not yet a deployed
independent reaper. The API response shape must be smoke-tested read-only first.
"""
import argparse,json,os,re,sys,time
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from urllib.parse import quote

BASE="https://api.runpod.io/v2/pods/"
VOLUME="1bch597yrz"
class UnsafeCleanup(RuntimeError):pass
def validate_owned_pod(pod,pod_id,job_id):
    if (not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",pod_id)
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{7,79}",job_id)):
        raise UnsafeCleanup("POD_OR_JOB_ID_INVALID")
    if not isinstance(pod,dict) or pod.get("id")!=pod_id:
        raise UnsafeCleanup("POD_ID_MISMATCH")
    if pod.get("name")!="trustfolio-video-"+job_id:
        raise UnsafeCleanup("NOT_OWNED_VIDEO_JOB_POD")
    mounts=pod.get("mounts")
    mount=(mounts or {}).get("networkVolume") if isinstance(mounts,dict) else None
    mount_id=mount.get("id") if isinstance(mount,dict) else None
    # Alternate standard response form (read-only API verification required).
    bound=pod.get("networkVolumeId") or mount_id
    if bound != VOLUME:
        raise UnsafeCleanup("WRONG_OR_UNVERIFIED_NETWORK_VOLUME")
    return True

def request_json(key,pod_id,method,open_request=urlopen):
    if not isinstance(key,str) or not key.strip() or "\n" in key or "\r" in key:
        raise UnsafeCleanup("SEPARATE_POD_WRITE_KEY_MISSING")
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",pod_id):
        raise UnsafeCleanup("POD_ID_INVALID")
    request=Request(BASE+quote(pod_id,safe=""),method=method,headers={
        "Authorization":"Bearer "+key,"Accept":"application/json"})
    try:
        with open_request(request,timeout=25) as resp:
            if resp.status==204:
                return {"http_status":204}
            if resp.status not in (200,202):
                raise UnsafeCleanup("UNEXPECTED_POD_API_STATUS")
            contents=resp.read(131073)
            if len(contents)>131072:
                raise UnsafeCleanup("POD_API_TOO_LARGE")
            return json.loads(contents) if contents.strip() else {"http_status":resp.status}
    except HTTPError as exc:
        if exc.code==404:return {"deleted":True,"http_status":404}
        raise UnsafeCleanup("POD_API_HTTP_"+str(exc.code)) from None
    except (URLError,TimeoutError,ValueError,OSError):
        raise UnsafeCleanup("POD_API_ERROR_MANUAL_DASHBOARD_INSPECTION_REQUIRED") from None

def cleanup(pod_id,job_id,key,*,apply=False,forced_after_failure=False,artifact_verified=False,requester=request_json,sleep=time.sleep):
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",pod_id):
        raise UnsafeCleanup("POD_ID_INVALID")
    if not apply:
        return {"status":"DRY_RUN_NO_POD_TOUCHED","pod_id":pod_id,
                "network_volume_preserved":True}
    if os.environ.get("TRUSTFOLIO_POD_DELETE_ARMED")!="yes":
        raise UnsafeCleanup("LIVE_TERMINATION_FLAG_DISABLED")
    if not (forced_after_failure or artifact_verified):
        raise UnsafeCleanup("MP4_MUST_BE_VERIFIED_UNLESS_EMERGENCY_CLEANUP")
    existing=requester(key,pod_id,"GET")
    if existing.get("deleted"):
        return {"status":"ALREADY_TERMINATED","pod_id":pod_id,
                "network_volume_preserved":True}
    validate_owned_pod(existing,pod_id,job_id)
    # DELETE ONLY THE VIDEO POD. Never call /network-volumes DELETE.
    requester(key,pod_id,"DELETE")
    for i in range(6):
        state=requester(key,pod_id,"GET")
        if state.get("deleted"):
            return {"status":"GPU_POD_TERMINATED_AND_GET_404_CONFIRMED",
                    "pod_id":pod_id,"network_volume_preserved":True}
        if i<5:sleep(2)
    raise UnsafeCleanup("DELETE_SENT_BUT_POD_STILL_VISIBLE_ALERT_OPERATOR")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pod-id",default="uncreated")
    p.add_argument("--job-id",default="not-created")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--emergency-after-render-failure",action="store_true")
    p.add_argument("--mp4-s3-sha-verified",action="store_true")
    args=p.parse_args()
    try:
        result=cleanup(args.pod_id,args.job_id,os.environ.get("RUNPOD_POD_WRITE_KEY",""),
            apply=args.apply,forced_after_failure=args.emergency_after_render_failure,
            artifact_verified=args.mp4_s3_sha_verified)
        print("RUNPOD_GPU_CLEANUP="+result["status"])
        print("NETWORK_VOLUME_PRESERVED=true")
        return 0
    except UnsafeCleanup as exc:
        print("RUNPOD_GPU_CLEANUP=BLOCKED_"+str(exc))
        return 1
if __name__=="__main__":sys.exit(main())
