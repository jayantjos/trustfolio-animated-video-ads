"""TrustFolio per-video GPU lifecycle controller, fail-closed before paid launch.

This stage is a tested lifecycle engine with injectable API and worker.
It deliberately DOES NOT provide live GPU creation or a usable rendering worker.
Without a vetted container image, provider-side termination TTL, reaper and a
separate budget approval it is unsafe to launch an actual billed Pod.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

VOLUME = "1bch597yrz"
DATACENTER = "EU-RO-1"
MAX_MINUTES = 60
GPU = "NVIDIA GeForce RTX 4090"
JOB_FORMAT = re.compile(r"[a-z0-9][a-z0-9_-]{7,79}\Z")

class GPUBlocked(RuntimeError):
    pass

def exact_money(x):
    try:
        d=Decimal(str(x))
        if not d.is_finite(): raise ValueError()
        return d
    except (ValueError, InvalidOperation, TypeError):
        raise GPUBlocked("COST_NOT_VERIFIED") from None

def assert_safe(p, *, allow_live=False):
    if p.get("network_volume_id")!=VOLUME or p.get("region")!=DATACENTER:
        raise GPUBlocked("WRONG_EXISTING_VOLUME_OR_REGION")
    if p.get("max_concurrent_pods")!=1 or not 1<=p.get("max_gpu_lifetime_minutes",0)<=MAX_MINUTES:
        raise GPUBlocked("CONCURRENCY_OR_TIME_CAP_INVALID")
    if p.get("publishing_enabled") is not False or p.get("keep_s3_volume_after_delete") is not True:
        raise GPUBlocked("PUBLISH_OR_STORAGE_POLICY_INVALID")
    for flag in ("must_provider_auto_terminate","must_independent_reaper",
                 "must_always_terminate_in_finally","must_confirm_pod_deleted_after_render"):
        if p.get(flag) is not True: raise GPUBlocked("SAFETY_GUARD_MISSING_"+flag)
    if allow_live:
        for flag in ("paid_gpu_instance_provisioning_enabled","gpu_hourly_price_verified",
                     "pod_api_write_key_connected","separate_cron_vps_deploy_completed",
                     "provider_auto_terminate_verified","independent_reaper_live_verified",
                     "worker_container_real_inference_verified"):
            if p.get(flag) is not True: raise GPUBlocked("NOT_READY_"+flag)
        if exact_money(p.get("gpu_spending_approved_usd",0))<=0:
            raise GPUBlocked("NO_GPU_BUDGET_APPROVED")
        if exact_money(p.get("max_gpu_cost_usd",0))<=0:
            raise GPUBlocked("MAX_COST_CAP_MISSING")
        if exact_money(p["max_gpu_cost_usd"])>exact_money(p["gpu_spending_approved_usd"]):
            raise GPUBlocked("GPU_CAP_OVER_APPROVAL")
    return True

def make_pod_request(job,p,*,quoted_usd_per_hour):
    assert_safe(p,allow_live=True)
    if not isinstance(job,dict) or not JOB_FORMAT.fullmatch(str(job.get("job_id",""))):
        raise GPUBlocked("JOB_ID_INVALID")
    if (job.get("paid_gpu_authorized") is not True or job.get("gpu_started") is not False
        or job.get("social_publishing_enabled") is not False):
        raise GPUBlocked("JOB_NOT_APPROVED_FOR_PRIVATE_GPU")
    if job.get("render_eligibility")!="ALL_ASSETS_VERIFIED_FOR_PRIVATE_RENDER":
        raise GPUBlocked("RENDER_ASSETS_NOT_READY")
    quote=exact_money(quoted_usd_per_hour)
    if quote<=0:raise GPUBlocked("QUOTE_NOT_POSITIVE")
    bound=quote*Decimal(p["max_gpu_lifetime_minutes"])/Decimal(60)
    if bound>exact_money(p["max_gpu_cost_usd"]):
        raise GPUBlocked("MAX_LIFETIME_QUOTE_EXCEEDS_APPROVED_CAP")
    # Require an actual immutable worker release, not a generic idle PyTorch image.
    image=p.get("worker_image","")
    if not isinstance(image,str) or not re.fullmatch(r"[\w./-]+@sha256:[0-9a-f]{64}",image):
        raise GPUBlocked("PINNED_GPU_WORKER_NOT_VERIFIED")
    return {
        "name":"trustfolio-video-"+job["job_id"],
        "image":image,
        "gpu":{"id":GPU,"count":1},
        "disk":30,"cloud":"SECURE",
        "dataCenterIds":[DATACENTER],
        "mounts":{"network":[{"volumeId":VOLUME,"path":"/workspace"}]},
        "ports":[],
        "env":{"TRUSTFOLIO_JOB_ID":job["job_id"],
               "TRUSTFOLIO_JOB_SHA256":job["idempotency_sha256"]},
    }

def validate_created_pod(pod, request):
    if not isinstance(pod,dict) or not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",str(pod.get("id",""))):
        raise GPUBlocked("CREATED_POD_ID_UNKNOWN_EMERGENCY_RECONCILE")
    if pod.get("name")!=request["name"] or pod.get("dataCenterId")!=DATACENTER:
        raise GPUBlocked("CREATED_POD_WRONG_NAME_OR_REGION")
    if pod.get("mounts",{}).get("network")!=request["mounts"]["network"]:
        raise GPUBlocked("CREATED_POD_VOLUME_MISMATCH")
    if pod.get("gpu")!=request["gpu"]:
        raise GPUBlocked("CREATED_GPU_MISMATCH")
    return pod["id"]

def run_job(job,p,api,worker,s3_checker,*,quote):
    """ONLY for an explicitly injected provider/worker with tested guards.

    Independent provider TTL/reaper required by policy: finally alone does not
    survive process death, and GitHub timeout is not a billing stop mechanism.
    """
    spec=make_pod_request(job,p,quoted_usd_per_hour=quote)
    pod_id=None
    artifacts_verified=False
    cleanup_error=None
    try:
        # api.create must be idempotent and perform name reconciliation on timeout.
        pod=api.create(spec)
        pod_id=validate_created_pod(pod,spec)
        api.wait_until_running(pod_id,max_seconds=600)
        result=worker.render(pod_id,job)
        # Worker must write a persistent MP4 and immutable receipt first.
        if not isinstance(result,dict) or result.get("status")!="S3_MP4_COMPLETE":
            raise GPUBlocked("WORKER_NO_FINAL_S3_RECEIPT")
        if result.get("job_id")!=job["job_id"]:
            raise GPUBlocked("WORKER_JOB_MISMATCH")
        uri=result.get("s3_key","")
        if not isinstance(uri,str) or not uri.startswith("videos/private-qa/"+job["job_id"]+"/"):
            raise GPUBlocked("UNAPPROVED_MP4_DESTINATION")
        if not uri.endswith(".mp4") or not re.fullmatch("[0-9a-f]{64}",str(result.get("sha256",""))):
            raise GPUBlocked("MP4_HASH_INVALID")
        if result.get("bytes",0)<10240 or not s3_checker.check_sha256(uri,result["sha256"],result["bytes"]):
            raise GPUBlocked("REMOTE_MP4_HASH_NOT_VERIFIED")
        artifacts_verified=True
        return {"status":"VIDEO_MP4_VERIFIED_PENDING_LIPSYNC_HUMAN_QA",
                "pod_id":pod_id,"video":uri,"sha256":result["sha256"],
                "auto_publish":False}
    finally:
        if pod_id:
            # Emergency termination is mandatory on failure, success termination
            # after MP4 verification. No media gets published here.
            try:
                api.terminate_and_confirm_absent(pod_id,
                    job_id=job["job_id"],emergency=not artifacts_verified)
            except Exception as exc:
                raise GPUBlocked("CRITICAL_POD_CLEANUP_UNCONFIRMED_MANUAL_ATTENTION") from exc

def dry_run(p):
    assert_safe(p)
    blockers=[]
    if not p.get("paid_gpu_instance_provisioning_enabled"):
        blockers.append("PAID_GPU_CREATION_DISABLED")
    if exact_money(p.get("gpu_spending_approved_usd",0))<=0:
        blockers.append("GPU_BUDGET_NOT_APPROVED")
    for key in ("provider_auto_terminate_verified","independent_reaper_live_verified",
                "worker_container_real_inference_verified","separate_cron_vps_deploy_completed",
                "pod_api_write_key_connected"):
        if p.get(key) is not True:blockers.append(key.upper()+"_PENDING")
    return {"status":"DRY_RUN_NO_GPU_CREATED","network_volume_id":VOLUME,
            "region":DATACENTER,"test_only":True,
            "workflow":"VPS_CRON -> LIVE_VERIFY -> CREATE -> GPU_RENDER -> S3_SHA256 -> DELETE -> CONFIRM_ABSENT",
            "remaining_blockers":blockers,"publishing_enabled":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--policy",default="config/runpod_gpu_one_shot_policy.json")
    p.add_argument("--output",default="output/gpu-lifecycle-dryrun.json")
    args=p.parse_args()
    pcy=json.loads(Path(args.policy).read_text())
    result=dry_run(pcy)
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print("TRUSTFOLIO_GPU_LIFECYCLE="+result["status"])
    print("GPU_POD_CREATED=false")
    return 0
if __name__=="__main__":sys.exit(main())
