"""Independent hard-stop observer for ONE exact TrustFolio nine-scene private Pod.

Runs on GitHub DEFAULT branch every five minutes, independent of feature
branch controller. Never deletes the protected 100GB network volume.
Provider-native terminateAfter 30 minutes is separately mandatory.
"""
import json,os,re,sys,time
from datetime import datetime,timezone
from scripts.wan5_independent_reaper import request_json, ReaperBlock, valid_target as original_check
from scripts.wan5_live_log_guard import scan_container_logs

NAME="trustfolio-video-wan9-multiscene-private-qa-20261024"
MAX_AGE_MINUTES=27
VOLUME="1bch597yrz"
REGION="EU-RO-1"

def owned(pod,*,now=None,min_age=0):
    now=now or datetime.now(timezone.utc)
    if not isinstance(pod,dict) or pod.get("name")!=NAME:
        return False
    if pod.get("dataCenterId")!=REGION:
        raise ReaperBlock("WAN9_REAPER_WRONG_REGION")
    mounts=pod.get("mounts",{})
    if not isinstance(mounts,dict) or mounts.get("network")!=[{"volumeId":VOLUME,"path":"/workspace"}]:
        raise ReaperBlock("WAN9_REAPER_WRONG_PROTECTED_MOUNT")
    pid=pod.get("id")
    if not isinstance(pid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",pid):
        raise ReaperBlock("WAN9_REAPER_POD_ID_INVALID")
    created=pod.get("createdAt")
    try:
        at=datetime.fromisoformat(created.replace("Z","+00:00"))
        if at.tzinfo is None:raise ValueError()
        age=(now-at).total_seconds()/60
    except (AttributeError,TypeError,ValueError):
        raise ReaperBlock("WAN9_REAPER_POD_AGE_UNVERIFIED") from None
    if age < -0.2:raise ReaperBlock("WAN9_REAPER_CLOCK_SKEW")
    return age >= min_age

def reap(api_key,*,client=request_json,now=None,apply=False,
         log_scanner=scan_container_logs,sleep=time.sleep):
    now=now or datetime.now(timezone.utc)
    allpods=client(api_key,"","GET")
    pods=allpods.get("pods")
    if not isinstance(pods,list):raise ReaperBlock("WAN9_REAPER_BAD_LIST")
    matches=[x for x in pods if isinstance(x,dict) and x.get("name")==NAME]
    if not matches:
        return {"status":"NO_WAN9_POD","deleted":False}
    if len(matches)!=1:raise ReaperBlock("WAN9_MULTIPLE_PODS_REQUIRES_MANUAL")
    pod=matches[0]
    owned(pod,now=now,min_age=0)
    stale=owned(pod,now=now,min_age=MAX_AGE_MINUTES)
    fatal=False
    if not stale:
        try:
            info=log_scanner(api_key,pod["id"])
            fatal=bool(info.get("fatal"))
        except Exception:
            fatal=False
    if not stale and not fatal:
        return {"status":"WAN9_POD_AGE_UNDER_LIMIT","deleted":False}
    reason="STALE" if stale else "FATAL"
    if not apply:
        return {"status":"WOULD_TERMINATE_"+reason,"deleted":False}
    pid=pod["id"]
    latest=client(api_key,"/"+pid,"GET")
    if latest.get("deleted"):
        return {"status":"WAN9_ALREADY_DELETED","deleted":True}
    if latest.get("id")!=pid or not owned(latest,now=now,min_age=0 if fatal else MAX_AGE_MINUTES):
        raise ReaperBlock("WAN9_IDENTITY_CHANGED_REFUSE_DELETE")
    client(api_key,"/"+pid,"DELETE")
    for step in range(9):
        state=client(api_key,"/"+pid,"GET")
        if state.get("deleted"):
            return {"status":"WAN9_"+reason+"_POD_DELETED_AND_404_CONFIRMED",
                    "deleted":True,"network_volume_preserved":True}
        if step<8:sleep(2)
    raise ReaperBlock("WAN9_POD_DELETE_GET404_NOT_CONFIRMED")

def main():
    try:
        key=os.environ.get("RUNPOD_POD_WRITE_KEY","")
        result=reap(key,apply=os.environ.get("TRUSTFOLIO_WAN9_REAPER_APPLY")=="yes")
        os.makedirs("output",exist_ok=True)
        with open("output/wan9-independent-reaper.json","w") as fp:
            json.dump({**result,"network_volume_preserved":True},fp,indent=2)
        print("WAN9_INDEPENDENT_REAPER="+result["status"])
        return 0
    except ReaperBlock as ex:
        print("WAN9_INDEPENDENT_REAPER=BLOCKED_"+str(ex))
        return 1
if __name__=="__main__":sys.exit(main())
