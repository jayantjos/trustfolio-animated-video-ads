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
from scripts.wan5_live_log_guard import scan_container_logs

GRAPHQL="https://api.runpod.io/graphql"
NAME="trustfolio-video-"+JOB_ID
IMAGE="ghcr.io/jayantjos/trustfolio-wan5-worker@sha256:b93f263e6013a38a493ff6e2657cc22bbf839f46f325379616e4e9ee6222f0b6"
S3_BUCKET=VOLUME
S3_HERO="assets/characters/shared/pink_kurta_lady_v1.png"
RECEIPT="videos/private-qa/"+JOB_ID+"/scene01.receipt.json"
FAILURE_RECEIPT="videos/private-qa/"+JOB_ID+"/scene01.failure.json"
MP4="videos/private-qa/"+JOB_ID+"/scene01.mp4"
PROGRESS="videos/private-qa/"+JOB_ID+"/scene01.progress.json"
# $0.89/h initially. Even $1.50/h over 38 minutes is < $1.
POD_PROVIDER_TTL_MINUTES=38
# This image uses PyTorch 2.6 + CUDA 12.4. Blackwell sm_120 GPUs
# require CUDA 12.8+; accepting them would waste the paid test on a CUDA
# architecture crash. Only schedule a supported Ada RTX 4090 (24 GiB).
# Fail closed when that GPU is unavailable rather than gambling credits.
GPU_PREFERENCE=("NVIDIA GeForce RTX 4090",)
OWN_POLL_MAX_MINUTES=30
LOG_UNAVAILABLE_STARTUP_SECONDS=600
LOG_UNAVAILABLE_AFTER_READY_SECONDS=90
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

def kill_owned_pods(key, requester=safe_api, sleep=time.sleep, expected_pod_id=None):
    # Handles ambiguous network errors during CREATE where the response might
    # be lost but billing already started. Never touch any other Pod.
    existing=find_owned_pods(key,requester)
    if len(existing)>1:raise PilotError("MULTIPLE_PILOT_PODS_MANUAL_ESCALATION")
    if not existing:return "NO_OWNED_GPU_POD"
    pid=validate_target(existing[0])
    if expected_pod_id is not None and pid!=expected_pod_id:
        raise PilotError("POD_ID_CHANGED_REFUSE_UNRELATED_DELETE")
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
                      connect_timeout=5,read_timeout=10,
                      retries={"total_max_attempts":1,"mode":"standard"}))

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

def verify_hindi_inputs(s3):
    raw=get_object(s3,"assets/audio/washing-machines/wan5-exact-dialogue.json",8192)
    if not raw:
        raise PilotError("HINDI_LISTENING_APPROVAL_MANIFEST_MISSING")
    meta=json.loads(raw)
    from scripts.wan5_gpu_worker import DIALOGUE
    if meta.get("text")!=DIALOGUE or meta.get("listening_qa_passed") is not True:
        raise PilotError("EXACT_HINDI_LISTENING_QA_REQUIRED")
    key=meta.get("s3_key", "")
    if not re.fullmatch(r"assets/audio/washing-machines/hindi_neural_v1/[A-Za-z0-9_.-]+[.]mp3",key):
        raise PilotError("UNAPPROVED_AUDIO_KEY")
    data=get_object(s3,key,5*1024*1024)
    if not data or hashlib.sha256(data).hexdigest()!=meta.get("sha256"):
        raise PilotError("HINDI_AUDIO_READBACK_MISMATCH")

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
                   {"key":"TRUSTFOLIO_GPU_JOB_ID","value":JOB_ID},
                   {"key":"TRUSTFOLIO_ATTEMPT_ID","value":os.environ.get("TRUSTFOLIO_ATTEMPT_ID", "")}]}

def polling_for_mp4(s3,write_key,pod_id,read_key=None,
                    deadline_seconds=OWN_POLL_MAX_MINUTES*60,
                    interval=15,sleep=time.sleep,now=time.monotonic,
                    log_scanner=scan_container_logs, attempt=None, wall_now=time.time):
    """Real-time cost guard: S3 receipt + exact Pod ownership + live SSE errors.

    Any fatal traceback classification aborts immediately. If log visibility is
    absent for longer than a bounded grace interval, fail closed rather than
    continue billing an unmonitored GPU. The caller's finally DELETEs the
    owned Pod; provider TTL and main-branch reaper remain independent backups.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,80}",str(pod_id)):
        raise PilotError("MONITOR_POD_ID_INVALID")
    read_key=read_key or write_key
    started=now()
    last_log_seen=started
    ever_seen_logs=False
    last_fingerprint=None
    last_sequence=0
    while now()-started<deadline_seconds:
        try:r=get_object(s3,RECEIPT,64000)
        except PilotError:r=None
        if r is not None:
            try:receipt=json.loads(r)
            except (ValueError,TypeError):
                raise PilotError("CORRUPTED_GPU_RECEIPT") from None
            if attempt and (receipt.get("attempt_id") != attempt or
                    receipt.get("audio_verified") is not True or
                    receipt.get("hindi_dialogue") != "अरे बाप रे! इतने सारे कपड़े? अब कौन धोएगा?"):
                raise PilotError("WRONG_ATTEMPT_OR_HINDI_AUDIO_UNVERIFIED")
            return verify_mp4_s3(s3,receipt)
        try:failure=get_object(s3,FAILURE_RECEIPT,8192)
        except PilotError:failure=None
        if failure:
            try:bad=json.loads(failure)
            except (ValueError,TypeError):
                raise PilotError("GPU_WORKER_FAILURE_RECEIPT_CORRUPT") from None
            if (bad.get("status")=="FAILED_PRIVATE_WAN5" and bad.get("job_id")==JOB_ID
                    and (not attempt or bad.get("attempt_id")==attempt)):
                code=str(bad.get("failure_reason","UNKNOWN"))
                if not re.fullmatch(r"[A-Z0-9_]{1,115}",code):
                    raise PilotError("GPU_WORKER_BAD_FAILURE_CODE")
                stage=bad.get("last_worker_stage")
                if stage in (
                    "STARTUP", "VALIDATE_AND_RENDER", "VERIFY_AUDIO_AND_MODEL",
                    "CUDA_RUNTIME_PROBE", "WAN_INFERENCE", "HINDI_MUX_AND_DECODE_QA", "COMPLETE"
                ):
                    print("PILOT_WORKER_LAST_STAGE="+stage,flush=True)
                # The RunPod live-log endpoint can be unavailable during
                # container startup. Expose ONLY fixed-field diagnostics from
                # the private volume receipt; never dump raw child stdout,
                # traceback text, paths or a credentials-containing object.
                diag=bad.get("subprocess_diagnostics")
                if isinstance(diag,dict):
                    safe_types={
                        "UNKNOWN", "RuntimeError", "ValueError",
                        "AssertionError", "TypeError", "IndexError", "KeyError",
                        "ImportError", "ModuleNotFoundError",
                        "FileNotFoundError", "OSError", "MemoryError",
                        "SystemError", "EOFError", "PermissionError",
                        "NotImplementedError", "UnicodeDecodeError",
                        "AttributeError", "RecursionError", "SafetensorError",
                    }
                    kind=diag.get("python_exception_type")
                    if kind in safe_types:
                        print("PILOT_WORKER_PYTHON_EXCEPTION_CLASS="+kind,flush=True)
                    count=diag.get("subprocess_output_tail_bytes")
                    if type(count) is int and 0<=count<=32768:
                        print("PILOT_WORKER_CAPTURED_OUTPUT_BYTES="+str(count),flush=True)
                    fingerprint=diag.get("subprocess_output_tail_sha256")
                    if isinstance(fingerprint,str) and re.fullmatch(r"[0-9a-f]{64}",fingerprint):
                        print("PILOT_WORKER_OUTPUT_SHA256="+fingerprint,flush=True)
                    traceback_flag=diag.get("traceback_marker_present")
                    if type(traceback_flag) is bool:
                        print("PILOT_WORKER_TRACEBACK_MARKER="+str(traceback_flag).upper(),flush=True)
                    safe_marker_names={
                        "CUDA_OOM_TEXT", "HOST_OOM_TEXT",
                        "TORCH_DISTRIBUTED_ERROR_TEXT", "NATIVE_CRASH_TEXT",
                        "MODEL_SHAPE_TEXT", "TOKENIZER_ERROR_TEXT"
                    }
                    markers=diag.get("safe_error_markers")
                    if isinstance(markers,list) and len(markers)<=6:
                        for m in markers:
                            if isinstance(m,str) and m in safe_marker_names:
                                print("PILOT_WORKER_SAFE_ERROR_MARKER="+m,flush=True)
                    last_safe_frame=diag.get("upstream_last_safe_frame")
                    _official_frames=(
                        "generate.py", "wan/textimage2video.py", "wan/modules/model.py",
                        "wan/modules/t5.py", "wan/modules/vae2_2.py", "wan/utils/utils.py",
                        "wan/utils/fm_solvers.py", "wan/utils/fm_solvers_unipc.py",
                    )
                    if isinstance(last_safe_frame,str):
                        frame_file, sep, frame_line=last_safe_frame.rpartition(":")
                        if (sep and frame_file in _official_frames and
                                frame_line.isdecimal() and
                                1<=int(frame_line)<=2500 and len(frame_line)<=4):
                            print("PILOT_WORKER_LAST_UPSTREAM_FRAME="+last_safe_frame,flush=True)
                    signal=diag.get("process_termination_signal")
                    if type(signal) is int and 1<=signal<=64:
                        print("PILOT_WORKER_TERMINATION_SIGNAL="+str(signal),flush=True)
                if type(bad.get("return_code")) is int and -255<=bad["return_code"]<=255:
                    print("PILOT_WORKER_EXIT_CODE="+str(bad["return_code"]),flush=True)
                raise PilotError("GPU_WORKER_FAILED_"+code)
        owned=find_owned_pods(write_key)
        if len(owned)!=1:
            raise PilotError("GPU_POD_DISAPPEARED_OR_DUPLICATED")
        pod=owned[0]
        if validate_target(pod)!=pod_id:
            raise PilotError("GPU_POD_IDENTITY_CHANGED")
        if pod.get("status") in ("EXITED","TERMINATED","FAILED","ERROR"):
            raise PilotError("GPU_POD_EXITED_WITHOUT_MP4")
        # S3 progress survives a broken log endpoint. A replayed/stale heartbeat
        # cannot keep billing alive; Pod RUNNING alone never counts as progress.
        progress_alive=False
        if attempt:
            try:
                raw=get_object(s3,PROGRESS,8192)
                hb=json.loads(raw) if raw else {}
                sequence=hb.get("sequence",0)
                age=wall_now()-float(hb.get("updated_at",0))
                progress_alive=(hb.get("job_id")==JOB_ID and
                    hb.get("attempt_id")==attempt and isinstance(sequence,int) and
                    sequence>last_sequence and -5<=age<=60)
                if progress_alive:
                    last_sequence=sequence
            except (PilotError,ValueError,TypeError):
                progress_alive=False
        observation=log_scanner(read_key,pod_id)
        error=observation.get("error", "")
        if re.fullmatch(r"(?:HTTP_[0-9]{3}|NETWORK_OR_STREAM_ERROR)",error):
            print("PILOT_LOG_SOURCE_ERROR="+error,flush=True)
        fatal=observation.get("fatal")
        if fatal:
            # Only a constant enum is printed, never raw logs or credentials.
            print("PILOT_LIVE_LOG_FATAL="+fatal,flush=True)
            raise PilotError("GPU_FATAL_LOG_"+fatal)
        fingerprint=observation.get("fingerprint")
        new_logs=bool(observation.get("available") and fingerprint and fingerprint!=last_fingerprint)
        if new_logs:
            last_fingerprint=fingerprint
        if progress_alive or new_logs:
            last_log_seen=now()
            ever_seen_logs=True
        else:
            grace=(LOG_UNAVAILABLE_AFTER_READY_SECONDS
                   if ever_seen_logs else LOG_UNAVAILABLE_STARTUP_SECONDS)
            if now()-last_log_seen>=grace:
                print("PILOT_LIVE_LOG_WATCHDOG=LOST_VISIBILITY",flush=True)
                raise PilotError("GPU_LOG_VISIBILITY_TIMEOUT_ABORT")
        print("PILOT_WATCHDOG_HEARTBEAT=ACTIVE",flush=True)
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
    # Historical request files are not authorization for another billed attempt.
    attempt=os.environ.get("TRUSTFOLIO_ATTEMPT_ID", "")
    if (not re.fullmatch(r"[A-Za-z0-9_-]{5,100}",attempt) or
        os.environ.get("TRUSTFOLIO_NEXT_ATTEMPT_APPROVED") != attempt):
        raise PilotError("FRESH_PAID_ATTEMPT_APPROVAL_REQUIRED")
    # Immutable, CI-tested overlay digest; never accept an arbitrary image.
    tested_image=os.environ.get("TRUSTFOLIO_TESTED_WORKER_IMAGE", "")
    if tested_image != IMAGE:
        raise PilotError("UNTESTED_WORKER_IMAGE_REFUSED")
    s3=make_s3()
    verified=None
    registry_id=None
    pod_id=None
    create_attempted=False
    cleanup_result="NOT_NEEDED"
    report={"status":"NOT_STARTED","video_rendered":False,"gpu_pod_deleted":False}
    try:
        cost=check_cost_and_availability(read_key)
        print("PILOT_GPU_TYPE="+cost["gpu_type"],flush=True)
        print("PILOT_GPU_STOCK_HINT="+cost["stock"],flush=True)
        print("PILOT_GPU_QUOTE_USD_HR="+cost["rate_usd_per_hour"],flush=True)
        print("PILOT_GPU_MAX_COST_UNDER_1_USD="+cost["max_gpu_usd_at_38m"],flush=True)
        verify_hero(s3)
        verify_hindi_inputs(s3)
        check_fresh_output(s3)
        if find_owned_pods(write_key):
            raise PilotError("ALREADY_EXISTING_PILOT_POD_PREVENT_DUPLICATE")
        registry_id=create_registry(write_key,github_token)
        payload=make_graphql_payload(registry_id,gpu_id=cost["gpu_type"])
        print("PILOT_PROVIDER_TERMINATE_AFTER="+payload["terminateAfter"],flush=True)
        print("PILOT_CREATING_REAL_GPU=TRUE",flush=True)
        create_attempted=True
        pod=graphql_create(write_key,payload)
        pod_id=str(pod["id"])
        print("PILOT_GPU_CREATED_ID="+pod_id,flush=True)
        if pod.get("name")!=NAME or pod.get("imageName")!=IMAGE:
            raise PilotError("CREATED_GPU_POD_NAME_OR_IMAGE_MISMATCH")
        try:
            actual_rate=Decimal(str(pod.get("costPerHr")))
        except Exception:
            raise PilotError("CREATED_POD_RATE_UNVERIFIED") from None
        if (not actual_rate.is_finite() or actual_rate<=0 or
            actual_rate>MAX_ACCEPTED_RATE_USD_PER_HR or
            actual_rate*POD_PROVIDER_TTL_MINUTES/60>=Decimal("1")):
            raise PilotError("CREATED_POD_RATE_OUTSIDE_BUDGET")
        verified=polling_for_mp4(s3,write_key,pod_id,read_key=read_key,attempt=attempt)
        print("PILOT_MP4_SHA256_VERIFIED="+verified["sha256"],flush=True)
        report={**verified,"video_rendered":True,"gpu_pod_deleted":False,
                "quote_usd_hr":cost["rate_usd_per_hour"]}
        return report
    except PilotError as exc:
        report["status"]="FAILED_"+str(exc)[:110]
        raise
    finally:
        # Even ambiguous create errors or failed inference MUST attempt a scoped
        # clean-up before exiting; confirmation is GET 404.
        try:
            cleanup_result=(kill_owned_pods(write_key,expected_pod_id=pod_id)
                            if create_attempted else "NO_CREATE_ATTEMPT")
            report["gpu_pod_deleted"]=cleanup_result in (
                "NO_CREATE_ATTEMPT","NO_OWNED_GPU_POD","DELETE_GET_404_CONFIRMED","ALREADY_REMOVED")
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
        report["create_attempted"]=create_attempted
        report["cleanup_result"]=cleanup_result
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

