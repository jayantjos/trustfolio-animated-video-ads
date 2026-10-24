"""Read-only export of 8 authentic Wan2.2 motion MP4s from existing RunPod volume."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import boto3
from botocore.config import Config

BUCKET = "1bch597yrz"
PREFIX = "videos/private-qa/washing-9scene-v1/"
ROOT = Path("output/wan9-render-export")


def download(client, key, limit):
    obj = client.get_object(Bucket=BUCKET, Key=key)
    n = int(obj.get("ContentLength", -1))
    if n <= 0 or n > limit:
        raise RuntimeError("S3_INVALID_LENGTH")
    try:
        data = obj["Body"].read(limit + 1)
    finally:
        obj["Body"].close()
    if len(data) != n:
        raise RuntimeError("S3_INCOMPLETE_READ")
    return data


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-of", "json",
        "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
        str(path)], check=True, capture_output=True, text=True, timeout=30)
    info = json.loads(p.stdout)
    videos = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if len(videos) != 1:
        raise RuntimeError("MISSING_VIDEO_STREAM")
    stream = videos[0]
    duration = float(info["format"]["duration"])
    if not (4.75 <= duration <= 5.35 and stream.get("codec_name") in ("h264", "hevc") and
            int(stream["height"]) > int(stream["width"])):
        raise RuntimeError("NOT_A_VERIFIED_5S_PORTRAIT_VIDEO")
    return {"duration": duration, "width": stream["width"], "height": stream["height"],
            "codec": stream["codec_name"]}


def export():
    access, secret = os.getenv("RUNPOD_S3_ACCESS_KEY_ID"), os.getenv("RUNPOD_S3_SECRET_ACCESS_KEY")
    if not access or not secret:
        raise RuntimeError("PRIVATE_S3_CREDENTIALS_MISSING")
    s3 = boto3.client("s3", endpoint_url="https://s3api-eu-ro-1.runpod.io",
        region_name="eu-ro-1", aws_access_key_id=access, aws_secret_access_key=secret,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    clips_dir = ROOT / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    scene_info = []
    for i in range(1, 9):
        sid = f"scene{i:02d}"
        rc = json.loads(download(s3, PREFIX + sid + ".motion.receipt.json", 30000))
        if (rc.get("scene_id") != sid or
            rc.get("status") != "GPU_MOTION_WRITTEN_AWAITING_S3_CONTROLLER_VERIFICATION" or
            rc.get("model") != "Wan2.2-TI2V-5B" or rc.get("private_qa") is not True or
            rc.get("public_publishing") is not False):
            raise RuntimeError("UNTRUSTED_GPU_CLIP_RECEIPT_" + sid)
        data = download(s3, PREFIX + sid + ".motion.mp4", 200_000_000)
        digest = hashlib.sha256(data).hexdigest()
        if digest != rc.get("sha256") or len(data) != rc.get("bytes"):
            raise RuntimeError("GPU_CLIP_SHA_MISMATCH_" + sid)
        dest = clips_dir / (sid + ".motion.mp4")
        dest.write_bytes(data)
        detail = probe(dest)
        detail.update({"scene": sid, "sha256": digest, "bytes": len(data),
                       "native_frames": rc.get("native_model_frames"),
                       "low_cost_retimed": rc.get("retimed_to_five_seconds")})
        scene_info.append(detail)
        print("WAN9_VERIFIED_EXPORTED=" + sid, flush=True)
    # Re-encode to normalize scene boundaries and ensure the combined MP4 is seekable.
    # Originals are preserved byte-for-byte in the separate artifact.
    listing = ROOT / "join.txt"
    listing.write_text("ffconcat version 1.0\n" + "".join(
        "file 'clips/scene" + f"{i:02d}" + ".motion.mp4'\n"
        for i in range(1, 9)), encoding="utf-8")
    video = ROOT / "TrustFolio-WAN2.2-Rendered-8-Scenes-SILENT.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-safe", "0", "-f", "concat", "-i", str(listing),
        "-map", "0:v:0", "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(video)], check=True, timeout=240)
    p = subprocess.run(["ffprobe", "-v", "error", "-of", "json",
        "-show_entries", "format=duration:stream=codec_type,width,height",
        str(video)], check=True, capture_output=True, text=True, timeout=30)
    meta = json.loads(p.stdout)
    duration = float(meta["format"]["duration"])
    if not 37.5 <= duration <= 43.5:
        raise RuntimeError("COMBINED_EIGHT_CLIP_DURATION_WRONG")
    record = {"authentic_wan_motion_scenes": 8, "scene09_missing": True,
        "preview_audio": "none", "final_ad": False, "publication_approved": False,
        "paid_gpu_pods_created": 0, "motion_preview_seconds": duration,
        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "scenes": scene_info}
    (ROOT / "provenance.json").write_text(json.dumps(record, indent=2) + "\n",
        encoding="utf-8")
    print("WAN9_SILENT_MP4_EXPORTED_TRUE", flush=True)
    print("WAN9_TOTAL_VERIFIED_SCENES=8", flush=True)
    print("WAN9_NO_PAID_GPU_CREATED=true", flush=True)


if __name__ == "__main__":
    export()
