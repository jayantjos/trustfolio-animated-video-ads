"""Fail-closed physical GPU input gate for nine Wan2.2 scenes.

Motion art must be clean, human-checked and free of old brand/price/rank text.
Do not confuse machine character design with real ranked product photographs.
Cost approval and provider watchdogs are a completely separate second gate.
"""
import hashlib
import json
import struct
from pathlib import Path
from .contract import Blocked
from .wan5_nineshot import verified_plan

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()

def validate_clean_plates(story, plate_manifest, *, root=None):
    motion=verified_plan(story)
    if plate_manifest.get("version")!=1 or plate_manifest.get("num_scenes")!=9:
        raise Blocked("Nine clean plates required")
    if plate_manifest.get("new_gpu_authorized") is not False:
        raise Blocked("Plate workflow cannot approve paid GPU")
    assets=plate_manifest.get("scenes")
    if not isinstance(assets,list) or len(assets)!=9:
        raise Blocked("Clean plate manifest has incorrect count")
    approved=[]
    for index,record in enumerate(assets):
        scene_id=f"scene{index+1:02d}"
        if record.get("scene_id")!=scene_id:
            raise Blocked(scene_id+":MISMATCHED_SCENE")
        if record.get("expression_visual_qa_approved") is not True:
            raise Blocked(scene_id+":EXPRESSION_VISUAL_QA_REQUIRED")
        if record.get("contains_no_baked_brand_guaranteed") is not True:
            raise Blocked(scene_id+":BAKED_BRAND_TEXT_NOT_CLEARED")
        if record.get("character_identity_match_approved") is not True:
            raise Blocked(scene_id+":ORIGINAL_CHARACTER_IDENTITY_UNCONFIRMED")
        if record.get("status")!="CLEAN_TEXT_FREE_PLATE_HUMAN_QA_APPROVED":
            raise Blocked(scene_id+":CLEAN_IMAGE_APPROVAL_MISSING")
        path=Path(record.get("path") or "")
        if root is not None:
            root=Path(root).resolve()
            path=(root/path.name).resolve()
            if not path.is_relative_to(root):
                raise Blocked(scene_id+":UNSAFE_FILE_PATH")
        if (not path.is_file() or not 50000<=path.stat().st_size<=8000000
            or not isinstance(record.get("visual_sha256"),str)
            or sha256(path)!=record["visual_sha256"]):
            raise Blocked(scene_id+":CLEAN_PLATE_FILE_OR_SHA_UNVERIFIED")
        with path.open("rb") as inp:
            header=inp.read(24)
        if (header[:8]!=bytes((137,80,78,71,13,10,26,10))
            or header[12:16]!=b"IHDR"
            or struct.unpack(">II",header[16:24])!=(720,1280)):
            raise Blocked(scene_id+":CLEAN_PLATE_PNG_720X1280_REQUIRED")
        # Reject truncated or maliciously malformed PNG rather than accepting a
        # forged 24-byte IHDR header. Actual image bytes must fully decode.
        from PIL import Image
        try:
            with Image.open(path) as verified_image:
                if verified_image.format!="PNG" or verified_image.size!=(720,1280):
                    raise ValueError("wrong image")
                verified_image.verify()
        except (ValueError,OSError,SyntaxError):
            raise Blocked(scene_id+":CLEAN_PLATE_PIXELS_FAILED_PNG_DECODER") from None
        approved.append({
            "scene_id":scene_id,
            "clean_plate_path":str(path),
            "clean_plate_sha256":record["visual_sha256"],
            "reference_sha256":motion["shots"][index]["source_storyboard_sha256"],
            "prompt":motion["shots"][index]["motion_prompt"],
            "seconds":motion["shots"][index]["generated_base_seconds"],
        })
    return {
        "status":"CLEAN_WAN_I2V_PLATES_VERIFIED_NO_GPU_CREATED",
        "motion_job_hash":motion["motion_job_hash"],
        "clean_plates":approved,
        "model":"Wan2.2-TI2V-5B",
        "paid_gpu_authorized":False,
        "gpu_pods_created":0,
        "published":False,
    }

def check_gate(story_path,manifest_path,*,root=None):
    story=json.loads(Path(story_path).read_text(encoding="utf8"))
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf8"))
    return validate_clean_plates(story,manifest,root=root)
