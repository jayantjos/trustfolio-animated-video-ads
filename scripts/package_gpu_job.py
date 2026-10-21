#!/usr/bin/env python3
"""Portable GPU input bundle; never provisions a GPU or publishes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED

class BundleError(ValueError):
    pass

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1048576), b""):
            digest.update(part)
    return digest.hexdigest()

def safe_asset(root, relative):
    path = PurePosixPath(relative)
    if not relative.startswith("assets/") or path.is_absolute() or ".." in path.parts:
        raise BundleError("Unsafe asset path: " + relative)
    root = Path(root).resolve()
    file = (root / relative).resolve()
    if not file.is_relative_to(root):
        raise BundleError("Asset escapes root: " + relative)
    return file

def prepare(pilot_path, asset_root, audio=None):
    pilot = json.loads(Path(pilot_path).read_text(encoding="utf-8"))
    if pilot.get("category") != "washing-machines" or pilot.get("production_publishing") is not False:
        raise BundleError("Only nonpublishing washing-machine pilot is permitted")
    scenes = pilot["scene_blueprint"]
    if sum(int(s["seconds"]) for s in scenes) != pilot["total_seconds"]:
        raise BundleError("Invalid story duration")
    ranks = next((s.get("rank_order") for s in scenes if s.get("kind") == "five_authoritative_products"), None)
    if ranks != [5, 4, 3, 2, 1]:
        raise BundleError("Top 5 order changed")
    image_paths = sorted({pilot["canonical_image"]} | {s["image_asset"] for s in scenes})
    files, missing = [], []
    for relative in image_paths:
        file = safe_asset(asset_root, relative)
        if not file.is_file():
            missing.append(relative)
            continue
        digest = sha256(file)
        if relative == pilot["canonical_image"] and digest != pilot["canonical_image_sha256"]:
            raise BundleError("Approved hero image SHA256 mismatch")
        files.append({"path": relative, "sha256": digest, "bytes": file.stat().st_size})
    mp3 = Path(audio) if audio else None
    if mp3 is None or not mp3.is_file():
        missing.append("audio/hi-IN.mp3")
    elif mp3.suffix.lower() != ".mp3" or mp3.stat().st_size == 0:
        raise BundleError("Audio must be nonempty MP3")
    manifest = {
        "schema_version": 1, "category": "washing-machines",
        "character_id": pilot["character_id"], "duration_seconds": pilot["total_seconds"],
        "model_code_url": pilot["video_model"]["code_repository"],
        "model_weights_url": pilot["video_model"]["model_repository"],
        "min_gpu_vram_gb": pilot["video_model"]["required_gpu_vram_gb"],
        "assets": files,
        "audio": {"path": "audio/hi-IN.mp3", "sha256": sha256(mp3)} if mp3 and mp3.is_file() else None,
        "missing_required_inputs": missing,
        "status": "INPUTS_PENDING" if missing else "INPUTS_VERIFIED_NO_GPU_RENDER",
        "gpu_provisioned": False, "video_generated": False,
        "lip_sync_verified": False, "publishing_enabled": False,
    }
    return pilot, manifest

def make_bundle(pilot_path, asset_root, audio, output):
    pilot, manifest = prepare(pilot_path, asset_root, audio)
    if manifest["missing_required_inputs"]:
        raise BundleError("Missing inputs: " + ", ".join(manifest["missing_required_inputs"]))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("pilot.json", json.dumps(pilot, ensure_ascii=False, indent=2))
        archive.writestr("job.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for item in manifest["assets"]:
            archive.write(safe_asset(asset_root, item["path"]), item["path"])
        archive.write(audio, "audio/hi-IN.mp3")
    return manifest

def main():
    parser = argparse.ArgumentParser(description="CPU-only GPU input packager")
    parser.add_argument("--pilot", default="config/pilots/washing-machines.json")
    parser.add_argument("--asset-root", default=".")
    parser.add_argument("--audio")
    parser.add_argument("--output", default="output/washing-gpu-plan.json")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.plan_only:
            _, manifest = prepare(args.pilot, args.asset_root, args.audio)
            dest = Path(args.output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            manifest = make_bundle(args.pilot, args.asset_root, args.audio, args.output)
    except (BundleError, OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps({"output": args.output, "status": manifest["status"],
                      "missing": manifest["missing_required_inputs"],
                      "publishing_enabled": False}, ensure_ascii=False))

if __name__ == "__main__":
    main()
