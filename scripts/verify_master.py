#!/usr/bin/env python3
"""Offline SHA256, duration and video metadata check for the Washing Machine visual master."""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "masters/washing-machines/manifest.json").read_text(encoding="utf-8"))
path = ROOT / manifest["target_path"]
if not path.is_file():
    print("NOT UPLOADED: expected actual MP4 binary at", path.relative_to(ROOT))
    sys.exit(2)
sha = hashlib.sha256()
with path.open("rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        sha.update(block)
actual = sha.hexdigest()
if actual != manifest["sha256"] or path.stat().st_size != manifest["size_bytes"]:
    print("FAIL: MP4 SHA256 or byte size differs from user-approved source")
    sys.exit(1)
try:
    raw = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", str(path)], text=True)
    probe = json.loads(raw)
    duration = float(probe["format"]["duration"])
    streams = probe.get("streams", [])
    video = next(x for x in streams if x["codec_type"] == "video")
    if abs(duration - 40) > 0.1 or (video["width"], video["height"]) != (360, 640):
        raise ValueError("Unexpected video size or duration")
except (FileNotFoundError, subprocess.CalledProcessError, ValueError, KeyError, StopIteration) as exc:
    print("FAIL: ffprobe metadata verification:", exc)
    sys.exit(1)
print("VERIFIED: exact 40-second user-approved visual master MP4", actual)
