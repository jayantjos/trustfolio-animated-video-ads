"""Nine-scene Wan2.2 GPU inference worker, private network-volume I/O only.

The paid-Pod controller MUST independently enforce a fresh approved spending
limit, GPU quotation, cloud provider terminateAfter, monitored logs, and a
separate reaper. This worker neither provisions Pods nor publishes ads.

Never use the original branded storyboard as an input plate: it contains fixed
sample product names and prices. The approved text-free plate manifest uses
original character poses while product facts remain editable at composition.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import time

try:
    from scripts.wan5_gpu_worker import (
        MODEL, WAN_SOURCE, MODEL_FILES, RenderError,
        verify_tokenizer_dir, check_video, sha256_file,
        generate_command, run_inference_streamed, gpu_check,
        verify_torch_cuda_kernel, atomic_json,
    )
except ModuleNotFoundError as missing_package:
    if missing_package.name != "scripts":
        raise
    from wan5_gpu_worker import (
        MODEL, WAN_SOURCE, MODEL_FILES, RenderError,
        verify_tokenizer_dir, check_video, sha256_file,
        generate_command, run_inference_streamed, gpu_check,
        verify_torch_cuda_kernel, atomic_json,
    )

ROOT=Path("/workspace")
INPUT_DIR=ROOT/"jobs"/"washing-9scene-v1"
OUTPUT_DIR=ROOT/"videos"/"private-qa"/"washing-9scene-v1"
MANIFEST=INPUT_DIR/"gpu-input.json"
# PRIVATE speed-recovery QA only: 49 native Wan frames at 8 solver steps.
# Frames are retimed to a 5-second MP4; NOT native 121-frame 30-step quality.
NATIVE_QA_FRAMES=49
NATIVE_QA_STEPS=8
PRESENTATION_SECONDS=5
NATIVE_WAN_FPS=24
MAX_BATCH_SECONDS=22*60
MAX_SCENE_SECONDS=9*60
SCENES=[f"scene{i:02d}" for i in range(1,10)]
SHA_RE=re.compile(r"[0-9a-f]{64}\Z")
ID_RE=re.compile(r"[A-Za-z0-9_-]{8,100}\Z")
MAX_PROMPT_CHARS=1600

def _sha(path):
    return sha256_file(path)

def validate_manifest(meta, *, root=ROOT, now=None):
    now=now or time.time()
    if meta.get("version")!=1 or meta.get("category")!="washing-machines":
        raise RenderError("NINE_SCENE_MANIFEST_WRONG_CATEGORY_OR_VERSION")
    state=meta.get("state")
    if state not in ("CLEAN_PLATES_USER_VISUALLY_APPROVED",
                     "MASKED_CANDIDATES_NONPUBLISHABLE_TECHNICAL_QA"):
        raise RenderError("UNRECOGNIZED_INPUT_PLATES")
    technical_qa=(state=="MASKED_CANDIDATES_NONPUBLISHABLE_TECHNICAL_QA")
    if technical_qa and meta.get("technical_render_only") is not True:
        raise RenderError("UNTRUSTED_CANDIDATE_MODE")
    if meta.get("private_qa") is not True or meta.get("published") is not False:
        raise RenderError("PUBLICATION_SCOPE_VIOLATION")
    if meta.get("paid_gpu_authorized") is not False:
        raise RenderError("MOTION_MANIFEST_CANNOT_AUTHORIZE_MONEY")
    if not SHA_RE.fullmatch(str(meta.get("motion_job_hash",""))):
        raise RenderError("MOTION_MANIFEST_HASH_REQUIRED")
    shots=meta.get("shots")
    if not isinstance(shots,list) or len(shots)!=9:
        raise RenderError("EXACT_NINE_GPU_SHOTS_REQUIRED")
    out=[]
    for i,scene in enumerate(shots):
        sid=SCENES[i]
        if scene.get("id")!=sid:
            raise RenderError("SCENE_ORDER_CHANGED_"+sid)
        filename=scene.get("plate_path")
        expected=(f"assets/candidates/washing-machines/{sid}.png"
                  if technical_qa else
                  f"assets/clean-plates/washing-machines/{sid}.png")
        if filename!=expected:
            raise RenderError("CLEAN_PLATE_PATH_NOT_ALLOWLISTED_"+sid)
        path=root/filename
        if not path.resolve().is_relative_to(root.resolve()):
            raise RenderError("INPUT_PATH_TRAVERSAL_"+sid)
        digest=scene.get("plate_sha256")
        if not SHA_RE.fullmatch(str(digest)):
            raise RenderError("PLATE_SHA_MISSING_"+sid)
        if path.is_file():
            if path.stat().st_size>10*1024*1024 or path.stat().st_size<50000:
                raise RenderError("PLATE_SIZE_INVALID_"+sid)
            if _sha(path)!=digest:
                raise RenderError("PLATE_SHA_CHANGED_"+sid)
        else:
            raise RenderError("CLEAN_PLATE_MISSING_"+sid)
        if technical_qa:
            if (scene.get("visual_qa_approved") is not False
                or scene.get("not_for_publication") is not True
                or scene.get("candidate_sha_verified") is not True):
                raise RenderError("TECHNICAL_CANDIDATE_NOT_CLEARLY_MARKED_"+sid)
        elif (scene.get("source_text_burned_in") is not False
              or scene.get("visual_qa_approved") is not True
              or scene.get("character_identity_approved") is not True):
            raise RenderError("VISUAL_QA_REQUIRED_"+sid)
        prompt=scene.get("prompt")
        if (not isinstance(prompt,str) or len(prompt)>MAX_PROMPT_CHARS
            or len(prompt)<80 or "\x00" in prompt
            or not any(word in prompt.lower() for word in ("animated","animate","cartoon","mascot"))):
            raise RenderError("MOTION_PROMPT_INVALID_"+sid)
        out.append((sid,path,digest,prompt))
    return out

def check_model():
    if not MODEL.is_dir() or not WAN_SOURCE.joinpath("generate.py").is_file():
        raise RenderError("PINNED_WAN_MODEL_OR_SOURCE_MISSING")
    for file,size in MODEL_FILES.items():
        p=MODEL/file
        if not p.is_file() or p.stat().st_size!=size:
            raise RenderError("PINNED_MODEL_ASSET_MISSING_OR_CHANGED")
    verify_tokenizer_dir(MODEL)
    gpu_check()
    verify_torch_cuda_kernel()

def infer_with_bounded_heartbeat(runner, command, *, cwd, env, timeout,
                                 checkpoint, sid, attempt, job_hash,
                                 heartbeat_seconds=20):
    """Pulse PRIVATE scene progress only while the bounded Wan process is alive.

    A pulse proves the worker is still awaiting inference, not that frames
    have completed. The child runner retains the hard per-scene timeout and
    process-group kill; the independent Pod TTL/reaper remain authoritative.
    """
    if timeout < 60 or timeout > MAX_SCENE_SECONDS:
        raise RenderError("INFERENCE_TIMEOUT_OUTSIDE_BOUNDED_LIMIT")
    sequence = 0
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(runner, command, cwd=cwd, env=env, timeout=timeout)
        while True:
            try:
                return future.result(timeout=heartbeat_seconds)
            except FutureTimeout:
                sequence += 1
                elapsed = time.monotonic() - started
                if elapsed > timeout + 15:
                    # Child runner is responsible for killpg on timeout.
                    print("WAN9_CHILD_TIMEOUT_WAITING_FOR_TERMINATION=" + sid,
                          flush=True)
                    continue
                atomic_json(checkpoint, {"scene_id":sid,"attempt_id":attempt,
                    "stage":"WAN_INFERENCE","time":time.time(),
                    "job_hash":job_hash,"sequence":sequence,
                    "elapsed_seconds":round(elapsed,1),
                    "completed_frames_claimed":False})
                print("WAN9_PRIVATE_GPU_WORKER_ALIVE=" + sid +
                      " SEQ=" + str(sequence), flush=True)


def retime_native_wan_to_five_seconds(source, destination, *, 
                                      command_runner=subprocess.run):
    """Validate real 49-frame Wan MP4; safely retime to 5s for private QA.

    Never label this output native 121-frame/30-step animation. The retimed
    clip is genuine model motion, but it is a lower-motion-fidelity pilot.
    """
    if source.resolve()==destination.resolve() or not source.is_file():
        raise RenderError("QA_RAW_MP4_MISSING_OR_OVERLAPS_FINAL")
    if source.stat().st_size < 10240:
        raise RenderError("QA_NATIVE_MP4_TOO_SMALL")
    probe=command_runner(["ffprobe","-v","error","-of","json",
        "-show_entries","format=duration:stream=codec_type,width,height,nb_frames,r_frame_rate",
        str(source)],capture_output=True,text=True,check=True,timeout=25)
    info=json.loads(probe.stdout)
    video=next((x for x in info.get("streams",[]) if x.get("codec_type")=="video"),None)
    if not video:
        raise RenderError("QA_NATIVE_MP4_VIDEO_MISSING")
    duration=float(info.get("format",{}).get("duration",0))
    frames=video.get("nb_frames")
    if (not 1.8<=duration<=2.35 or (frames not in (None,"N/A")
        and int(frames)!=NATIVE_QA_FRAMES) or
        int(video.get("height",0))<=int(video.get("width",0))):
        raise RenderError("QA_NATIVE_WAN_GEOMETRY_DURATION_OR_FRAMES_WRONG")
    raw_sha=_sha(source)
    staged=destination.with_name(destination.stem+".retime.pending.mp4")
    try:
        if staged.exists(): staged.unlink()
        # The 49 model-generated frames span 48 intervals and are stretched
        # over 120 intervals. Repeated frames are an explicitly disclosed
        # low-cost test, NOT full-rate independent model-generated frames.
        ratio=(PRESENTATION_SECONDS*NATIVE_WAN_FPS)/(NATIVE_QA_FRAMES-1)
        command_runner(["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
            "-y","-i",str(source),"-an",
            "-vf",f"setpts={ratio}*(PTS-STARTPTS),fps={NATIVE_WAN_FPS},format=yuv420p",
            "-c:v","libx264","-preset","veryfast","-crf","22",
            "-movflags","+faststart",str(staged)],
            capture_output=True,text=True,check=True,timeout=100)
        check_video(staged)
        staged.replace(destination)
        return {"native_model_frames":NATIVE_QA_FRAMES,
            "native_sampling_steps":NATIVE_QA_STEPS,
            "native_duration_seconds":round(duration,3),
            "retimed_output_seconds":PRESENTATION_SECONDS,
            "native_wan_sha256":raw_sha,
            "retimed_to_five_seconds":True,
            "is_original_native_121_frame_quality":False,
            "artificial_frames_used":True}
    finally:
        if staged.exists(): staged.unlink()


def run(*, input_path=MANIFEST, root=ROOT, outdir=OUTPUT_DIR,
        wall_seconds=MAX_BATCH_SECONDS, runner=run_inference_streamed,
        model_check=check_model):
    if os.environ.get("TRUSTFOLIO_PRIVATE_QA")!="yes":
        raise RenderError("PRIVATE_QA_ENV_NOT_ARMED")
    if os.environ.get("TRUSTFOLIO_WAN9_RENDER")!="yes":
        raise RenderError("NINE_SCENE_EXECUTION_NOT_ARMED")
    attempt=os.environ.get("TRUSTFOLIO_ATTEMPT_ID","")
    if not ID_RE.fullmatch(attempt):
        raise RenderError("FRESH_ATTEMPT_ID_REQUIRED")
    if not 60<=wall_seconds<=MAX_BATCH_SECONDS:
        raise RenderError("WORKER_MAX_WALL_EXCEEDED")
    if not input_path.resolve().is_relative_to(root.resolve()):
        raise RenderError("UNSAFE_MANIFEST_PATH")
    meta=json.loads(input_path.read_text(encoding="utf-8"))
    shots=validate_manifest(meta,root=root)
    model_check()
    outdir.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    rendered=[]
    for index,(sid,image,image_sha,prompt) in enumerate(shots):
        if time.monotonic()-started>=wall_seconds-100:
            print("GPU_BATCH_WALLCLOCK_GUARD_STOP="+sid,flush=True)
            break
        final=outdir/(sid+".motion.mp4")
        receipt_file=outdir/(sid+".motion.receipt.json")
        if receipt_file.exists():
            try:
                old=json.loads(receipt_file.read_text())
                if (old.get("sha256")==_sha(final)
                    and old.get("plate_sha256")==image_sha
                    and old.get("motion_job_hash")==meta["motion_job_hash"]
                    and old.get("status")=="GPU_MOTION_WRITTEN_AWAITING_S3_CONTROLLER_VERIFICATION"):
                    check_video(final)
                    print("WAN9_EXISTING_SCENE_REUSED="+sid,flush=True)
                    rendered.append(sid)
                    continue
            except (ValueError,OSError,KeyError,RenderError):
                pass
            raise RenderError("UNVERIFIED_OLD_SCENE_REFUSE_OVERWRITE_"+sid)
        pending=outdir/(sid+".pending.mp4")
        if pending.exists():
            pending.unlink()
        command=generate_command(pending,model=MODEL,image=image,code=WAN_SOURCE)
        command[command.index("--frame_num")+1]=str(NATIVE_QA_FRAMES)
        command[command.index("--sample_steps")+1]=str(NATIVE_QA_STEPS)
        print("WAN9_REAL_LOW_COST_NATIVE_FRAMES="+str(NATIVE_QA_FRAMES)+
              " SAMPLING_STEPS="+str(NATIVE_QA_STEPS)+
              " LOW_FIDELITY_PRIVATE_QA=true",flush=True)
        marker=command.index("--prompt")
        command[marker+1]=prompt
        command[command.index("--base_seed")+1]=str(20261024+index)
        checkpoint=outdir/(sid+".progress.json")
        atomic_json(checkpoint,{"scene_id":sid,"attempt_id":attempt,
            "stage":"WAN_INFERENCE","time":time.time(),"job_hash":meta["motion_job_hash"]})
        remaining=wall_seconds-(time.monotonic()-started)-75
        if remaining<90:
            print("GPU_BATCH_TIME_GUARD_SKIP="+sid,flush=True)
            break
        try:
            infer_with_bounded_heartbeat(runner,command,cwd=str(WAN_SOURCE),
                env={**os.environ,"PYTORCH_CUDA_ALLOC_CONF":"expandable_segments:True"},
                timeout=min(MAX_SCENE_SECONDS,int(remaining)),checkpoint=checkpoint,
                sid=sid,attempt=attempt,job_hash=meta["motion_job_hash"])
            retiming=retime_native_wan_to_five_seconds(pending,final)
            check_video(final)
            receipt={
                **retiming,
                "status":"GPU_MOTION_WRITTEN_AWAITING_S3_CONTROLLER_VERIFICATION",
                "scene_id":sid,"model":"Wan2.2-TI2V-5B",
                "motion_job_hash":meta["motion_job_hash"],
                "scene_source_reference_sha256":meta["shots"][index]["reference_sha256"],
                "plate_sha256":image_sha,
                "sha256":_sha(final),"bytes":final.stat().st_size,
                "s3_key":str(final.relative_to(root)),
                "private_qa":True,"public_publishing":False,
                "lip_sync_claimed":False,"attempt_id":attempt,
                "s3_get_sha256_verified":False,"pod_deleted_get_404":False,
                "source_is_unapproved_technical_candidate":
                    meta.get("state")=="MASKED_CANDIDATES_NONPUBLISHABLE_TECHNICAL_QA",
            }
            atomic_json(receipt_file,receipt)
            rendered.append(sid)
            print("WAN9_GPU_SCENE_WRITTEN="+sid,flush=True)
        finally:
            if pending.exists():
                pending.unlink()
    return {"state":"NINE_SCENE_PARTIAL_PRIVATE_GPU" if len(rendered)<9 else
                  "NINE_SCENE_GPU_FILES_WRITTEN_UNVERIFIED_BY_CONTROLLER",
            "scene_files_written_or_reused":rendered,
            "count":len(rendered),"published":False,
            "controller_must_s3_get_verify_and_delete_pod":True}

def main():
    try:
        result=run()
        print(json.dumps(result,sort_keys=True))
        return 0 if result["count"]==9 else 3
    except Exception as exc:
        # Do not leak provider tokens or untrusted upstream exception contents.
        print("WAN9_GPU_WORKER_ABORT="+type(exc).__name__,flush=True)
        return 2

if __name__=="__main__":
    sys.exit(main())
