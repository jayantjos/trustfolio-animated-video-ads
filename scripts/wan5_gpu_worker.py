#!/usr/bin/env python3
"""Genuine 5s Wan2.2-TI2V-5B PRIVATE QA GPU worker. Never publishes.

Must run ONLY inside a budget-bounded, auto-terminating RunPod GPU Pod.
Its output lives on the existing 100 GB mounted network volume; a separate
CPU controller must S3-GET and SHA256-check the MP4 before cleanup success.
This script does not create, delete or alter Pods / network volumes.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path("/workspace")
MODEL_SHA = "921dbaf3f1674a56f47e83fb80a34bac8a8f203e"
MODEL = ROOT / "models" / "Wan2.2-TI2V-5B" / MODEL_SHA
CHARACTER_KEY = "assets/characters/shared/pink_kurta_lady_v1.png"
IMAGE = ROOT / CHARACTER_KEY
IMAGE_SHA = "7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"
IMAGE_BYTES = 2484010
JOB_ID = "wan5-laundry-first-20261021"
OUTDIR = ROOT / "videos" / "private-qa" / JOB_ID
OUTPUT = OUTDIR / "scene01.mp4"
RECEIPT = OUTDIR / "scene01.receipt.json"
WAN_SOURCE = Path("/opt/Wan2.2")
PROMPT = ("Animate this exact approved premium 3D cartoon Indian woman wearing a "
          "pink kurta in her original sunlit tropical laundry courtyard; huge "
          "overflowing laundry basket. The woman blinks, raises eyebrows, gently "
          "turns her head and reacts to the clothes with natural hand gestures. "
          "Preserve the identical face, hairstyle, outfit, courtyard, framing, "
          "body proportions, textures and colorful cinematic cartoon quality. "
          "Subtle fluent cinematic motion, no new people, no extra fingers, "
          "no morphing, no redesign, no text, no logos, no lip-sync.")

# Bytes pinned to approved official model manifest; avoid relying on file names
# existing without actual weights. Complete SHA checks happened during S3 stage.
MODEL_FILES = {
    "config.json": 251,
    "Wan2.2_VAE.pth": 2818839170,
    "diffusion_pytorch_model-00001-of-00003.safetensors": 9825014472,
    "diffusion_pytorch_model-00002-of-00003.safetensors": 9995661736,
    "diffusion_pytorch_model-00003-of-00003.safetensors": 178558176,
    "models_t5_umt5-xxl-enc-bf16.pth": 11361920418,
    "diffusion_pytorch_model.safetensors.index.json": 72865,
    "configuration.json": 43,
    "README.md": 15935,
}

TOKENIZER_FILES = {
    "tokenizer.json": (17_500_000,"6e197b4d3dbd71da14b4eb255f4fa91c9c1f2068b20a2de2472967ca3d22602b"),
    "spiece.model": (4_800_000,"e3909a67b780650b35cf529ac782ad2b6b26e6d1f849d3fbb6a872905f452458"),
    "tokenizer_config.json":(150_000,None),
    "special_tokens_map.json":(30_000,None),
}
FAILURE = OUTDIR / "scene01.failure.json"

class RenderError(RuntimeError):
    pass

def sha256_file(path, chunk=4 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def verify_tokenizer_dir(root):
    # The original 9 large checkpoint objects were verified but the official
    # model requires FOUR additional tokenizer files under google/umt5-xxl/.
    for name,(max_bytes,digest) in TOKENIZER_FILES.items():
        file=root / "google" / "umt5-xxl" / name
        if not file.is_file():
            raise RenderError("WAN_TOKENIZER_MISSING_"+name.replace(".","_"))
        size=file.stat().st_size
        if not 10 <= size <= max_bytes:
            raise RenderError("WAN_TOKENIZER_SIZE_INVALID_"+name.replace(".","_"))
        if digest and sha256_file(file)!=digest:
            raise RenderError("WAN_TOKENIZER_SHA256_MISMATCH_"+name.replace(".","_"))
        if name.endswith(".json"):
            try:
                with open(file,"r",encoding="utf-8") as fh:
                    value=json.load(fh)
                if not isinstance(value,dict):
                    raise ValueError("Expected JSON object")
            except (OSError,ValueError,UnicodeError):
                raise RenderError("WAN_TOKENIZER_JSON_INVALID_"+name.replace(".","_")) from None
    return True

def ensure_approved_files(image=IMAGE, model=MODEL, code=WAN_SOURCE):
    if not image.is_file() or image.stat().st_size != IMAGE_BYTES:
        raise RenderError("APPROVED_HERO_MISSING_OR_SIZE_WRONG")
    if sha256_file(image) != IMAGE_SHA:
        raise RenderError("APPROVED_HERO_SHA_MISMATCH")
    if not (code / "generate.py").is_file():
        raise RenderError("WAN2_CODE_MISSING")
    for name, size in MODEL_FILES.items():
        path = model / name
        if not path.is_file() or path.stat().st_size != size:
            raise RenderError("VERIFIED_MODEL_SHARD_NOT_MOUNTED_" + name)
    verify_tokenizer_dir(model)
    return True

def gpu_check(runner=subprocess.run):
    p = runner(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
               capture_output=True, text=True, timeout=20, check=True)
    first = p.stdout.splitlines()[0].strip()
    if not first.isdigit() or int(first) < 23000:
        raise RenderError("GPU_MIN_24GB_NOT_VERIFIED")
    return int(first)

def generate_command(dest, model=MODEL, image=IMAGE, code=WAN_SOURCE):
    if not dest.is_absolute() or dest.suffix != ".mp4":
        raise RenderError("BAD_MP4_DESTINATION")
    return [sys.executable, str(code / "generate.py"),
            "--task", "ti2v-5B",
            "--size", "704*1280",
            "--frame_num", "121",
            "--ckpt_dir", str(model),
            "--offload_model", "True",
            "--convert_model_dtype",
            "--t5_cpu", "--image", str(image),
            "--sample_steps", "30",
            "--base_seed", "42",
            "--prompt", PROMPT,
            "--save_file", str(dest)]

def check_video(path, runner=subprocess.run):
    if not path.is_file() or path.stat().st_size < 10240:
        raise RenderError("GPU_RENDER_MP4_MISSING_OR_TOO_SMALL")
    p = runner(["ffprobe", "-v", "error", "-print_format", "json",
               "-show_entries", "format=duration:stream=codec_type,width,height,nb_frames",
               str(path)], capture_output=True, text=True, check=True, timeout=30)
    payload = json.loads(p.stdout)
    video = next((s for s in payload.get("streams", [])
                  if s.get("codec_type") == "video"), None)
    duration = float(payload.get("format", {}).get("duration", 0))
    if not video or not 4.8 <= duration <= 5.3:
        raise RenderError("NOT_A_REAL_FIVE_SECOND_VIDEO")
    if int(video.get("height", 0)) <= int(video.get("width", 0)):
        raise RenderError("NOT_PORTRAIT_VIDEO")
    return round(duration, 3)

def atomic_json(path, result):
    temp = path.with_suffix(".json.tmp")
    with open(temp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp, path)

def render(*, image=IMAGE, model=MODEL, code=WAN_SOURCE,
           outdir=OUTDIR, runner=subprocess.run, seconds=2400):
    if os.environ.get("TRUSTFOLIO_PRIVATE_QA") != "yes":
        raise RenderError("PRIVATE_QA_ENV_NOT_ARMED")
    if os.environ.get("TRUSTFOLIO_GPU_JOB_ID") != JOB_ID:
        raise RenderError("UNAPPROVED_PAID_GPU_JOB_ID")
    if not 60 <= seconds <= 2400:
        raise RenderError("RENDER_WALL_CLOCK_BOUND_INVALID")
    ensure_approved_files(image, model, code)
    gpu_check(runner)
    outdir.mkdir(parents=True, exist_ok=True)
    final = outdir / "scene01.mp4"
    pending = outdir / "scene01.pending.mp4"
    if pending.exists():
        pending.unlink()
    try:
        runner(generate_command(pending, model, image, code),
               cwd=str(code), timeout=seconds, check=True,
               env={**os.environ, "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
        duration = check_video(pending, runner)
        digest = sha256_file(pending)
        os.replace(pending, final)
        report = {
            "status": "VOLUME_MP4_WRITTEN_PENDING_S3_GET_VERIFICATION",
            "job_id": JOB_ID, "s3_key": str(final.relative_to(ROOT)),
            "sha256": digest, "bytes": final.stat().st_size,
            "seconds": duration, "model": "Wan2.2-TI2V-5B",
            "character_sha256": IMAGE_SHA,
            "gpu_pod_destroyed": False,
            "social_publishing": False, "lip_sync_claimed": False,
        }
        atomic_json(outdir / "scene01.receipt.json", report)
        print("TRUSTFOLIO_WAN5=VOLUME_MP4_PENDING_S3_VERIFY", flush=True)
        print("WAN5_MP4_SHA256=" + digest, flush=True)
        print("WAN5_MP4_BYTES=" + str(final.stat().st_size), flush=True)
        return report
    finally:
        if pending.exists():
            pending.unlink()

def write_failure_receipt(reason,returncode=None):
    # Diagnostic receipt lives on the EXISTING volume, never raw traceback,
    # prompts or credentials. Controller can retrieve it via read-only S3.
    safe=re.sub(r"[^A-Z0-9_]", "_",str(reason).upper())[:115]
    result={"status":"FAILED_PRIVATE_WAN5","job_id":JOB_ID,
            "failure_reason":safe,"model":"Wan2.2-TI2V-5B",
            "social_publishing":False,
            "return_code":int(returncode) if isinstance(returncode,int) else None}
    try:
        OUTDIR.mkdir(parents=True,exist_ok=True)
        atomic_json(FAILURE,result)
    except (OSError,ValueError):
        print("WAN5_FAILURE_RECEIPT=UNAVAILABLE",flush=True)

def main():
    try:
        render()
        return 0
    except subprocess.TimeoutExpired:
        reason="GPU_INFERENCE_TIMEOUT"
        print("TRUSTFOLIO_WAN5=BLOCKED_"+reason,flush=True)
        write_failure_receipt(reason)
    except subprocess.CalledProcessError as exc:
        reason="GPU_INFERENCE_OR_TOOLS_FAILED"
        print("TRUSTFOLIO_WAN5=BLOCKED_"+reason,flush=True)
        write_failure_receipt(reason,exc.returncode)
    except (RenderError, ValueError) as exc:
        reason=str(exc)
        print("TRUSTFOLIO_WAN5=BLOCKED_"+reason,flush=True)
        write_failure_receipt(reason)
    except Exception:
        reason="UNEXPECTED_ERROR"
        print("TRUSTFOLIO_WAN5=BLOCKED_"+reason,flush=True)
        write_failure_receipt(reason)
    return 1

if __name__ == "__main__":
    sys.exit(main())
