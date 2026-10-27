#!/usr/bin/env python3
"""Verify the user-approved V6 54-second artistic reference uploaded to GitHub."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/"masters/washing-machines/v6_54s_art_direction.json").read_text())
p=ROOT/manifest["expected_video_path"]
if not p.is_file():
    sys.exit("V6_MP4_MISSING: Upload user-approved 54s file to "+str(p.relative_to(ROOT)))
digest=hashlib.sha256(p.read_bytes()).hexdigest()
if digest!=manifest["file_sha256"] or p.stat().st_size!=manifest["size_bytes"]:
    sys.exit("V6_SOURCE_MISMATCH: File not same visual master approved by user")
metadata=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries",
    "format=duration:stream=codec_type,codec_name,width,height,sample_rate,channels",
    "-of","json",str(p)],text=True))
vid=next((x for x in metadata.get("streams",[]) if x.get("codec_type")=="video"),{})
aud=next((x for x in metadata.get("streams",[]) if x.get("codec_type")=="audio"),{})
duration=float(metadata["format"]["duration"])
if (not 53.9<=duration<=54.1 or (vid.get("width"),vid.get("height"))!=(720,1280)
        or vid.get("codec_name")!="h264" or aud.get("codec_name")!="aac"
        or aud.get("sample_rate")!="48000"):
    sys.exit("V6_MEDIA_FORMAT_INVALID: Unexpected codec, dimensions, sampling rate or duration")
print("APPROVED_VISUAL_V6_GITHUB_BINARY_SHA256=PASS")
print("V6_54S_AUDIO_VIDEO_FORMAT_QA=PASS")
print("V6_IS_STATIC_ART_REFERENCE_NOT_VERIFIED_LIVE_CAMPAIGN=YES")
