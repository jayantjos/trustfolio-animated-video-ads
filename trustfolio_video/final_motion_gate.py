"""Final nine-Wan scene gate: factual media provenance, voice, lipsync and freshness.

No payment, pod operations, editing or social publication here.
"""
from datetime import datetime,timezone
import hashlib,json,re
from pathlib import Path

from .contract import Blocked
from .wan5_nineshot import verified_plan

def verify_final_motion_inputs(story, receipts, files, qa):
    """Validate all 9 genuine GPU clips before any final-render designation.

    receipts: list of scene-scoped S3 readback verified metadata
    files: dict scene_id => local downloaded MP4 path, used for SHA readback
    qa: separately signed-off audio/lipsync visual-review result
    """
    planned=verified_plan(story)
    errors=[]
    if not isinstance(receipts,list) or len(receipts)!=9:
        errors.append("REQUIRE_NINE_GPU_RECEIPTS")
    if not isinstance(files,dict) or len(files)!=9:
        errors.append("REQUIRE_NINE_ACTUAL_MP4_FILES")
    receipts=receipts if isinstance(receipts,list) else []
    files=files if isinstance(files,dict) else {}
    names=[shot["scene_id"] for shot in planned["shots"]]
    by_id={}
    for receipt in receipts:
        if not isinstance(receipt,dict):
            errors.append("RECEIPT_SCHEMA_INVALID")
            continue
        sid=receipt.get("scene_id")
        if sid in by_id:
            errors.append("DUPLICATE_SCENE_RECEIPT")
        by_id[sid]=receipt
    for shot in planned["shots"]:
        sid=shot["scene_id"]
        rec=by_id.get(sid)
        if not rec:
            errors.append(sid+"_NO_GPU_RECEIPT")
            continue
        expected_sha=rec.get("sha256")
        path=files.get(sid)
        if (rec.get("model")!="Wan2.2-TI2V-5B"
            or rec.get("source_campaign_id")!=planned["campaign_id"]
            or rec.get("motion_job_hash")!=planned["motion_job_hash"]
            or rec.get("scene_source_reference_sha256")!=shot["source_storyboard_sha256"]
            or rec.get("private_qa") is not True
            or rec.get("lip_sync_claimed") is not False):
            errors.append(sid+"_UNTRUSTED_GPU_PROVENANCE")
            continue
        if (rec.get("s3_get_sha256_verified") is not True
            or rec.get("pod_deleted_get_404") is not True
            or rec.get("public_publishing") is not False):
            errors.append(sid+"_MISSING_REMOTE_VERIFY_OR_CLEANUP")
            continue
        if (not re.fullmatch(r"[a-f0-9]{64}",str(expected_sha))
            or not isinstance(rec.get("bytes"),int)
            or rec["bytes"]<10000
            or rec["bytes"]>200*1024*1024
            or not isinstance(path,(str,Path))
            or not Path(path).is_file()):
            errors.append(sid+"_MEDIA_MISSING")
            continue
        f=Path(path)
        if f.stat().st_size!=rec["bytes"]:
            errors.append(sid+"_LENGTH_MISMATCH")
            continue
        hasher=hashlib.sha256()
        with f.open("rb") as inp:
            for chunk in iter(lambda:inp.read(1024*1024),b""):
                hasher.update(chunk)
        if hasher.hexdigest()!=expected_sha:
            errors.append(sid+"_CONTENT_HASH_MISMATCH")
    if set(by_id)!=set(names):
        errors.append("SCENE_ID_SET_MISMATCH")
    if not isinstance(qa,dict):
        errors.append("HUMAN_QA_MISSING")
        qa={}
    if qa.get("hindi_narration_human_listening_approved") is not True:
        errors.append("HUMAN_HINDI_QA_REQUIRED")
    if qa.get("scene01_lipsync_verified") is not True or qa.get("scene09_lipsync_verified") is not True:
        errors.append("LEAD_CHARACTER_LIPSYNC_QA_REQUIRED")
    if qa.get("all_nine_motion_consistency_approved") is not True:
        errors.append("NINE_SHOT_VISUAL_QA_REQUIRED")
    if qa.get("cta_readable_and_final_two_seconds") is not True:
        errors.append("CTA_VISUAL_QA_REQUIRED")
    if qa.get("no_fake_claims_or_baked_sample_prices") is not True:
        errors.append("FACTUAL_OVERLAY_VISUAL_QA_REQUIRED")
    return {"status":"FINAL_RENDER_MEDIA_INPUTS_VERIFIED_PRIVATE_QA" if not errors else "FINAL_3D_VIDEO_NOT_READY",
            "missing_requirements":errors,
            "expected_scenes":9,"verified_scenes":9 if not errors else sum(
                1 for x in names if not any(err.startswith(x+"_") for err in errors)),
            "published":False,"publish_allowed":False,
            "gpu_pod_created_by_this_check":False,
            "model":"Wan2.2-TI2V-5B","campaign_id":planned["campaign_id"]}
