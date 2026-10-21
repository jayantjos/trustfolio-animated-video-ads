#!/usr/bin/env python3
"""CPU-only TrustFolio final Wan render readiness gate.

Reads S3 object headers; does not start GPU or publish.
Fail-closed on absent art/audio; reports blockers without pretending final MP4.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

MODEL_MANIFEST = "config/wan_verified_model_manifest.json"
CHARACTER = "assets/characters/shared/pink_kurta_lady_v1.png"
HERO_SHA = "7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"
HERO_SIZE = 2484010
BUCKET = "1bch597yrz"
S3_ENDPOINT = "https://s3api-eu-ro-1.runpod.io"

AUDIO_RECEIPTS = "config/hindi_neural_verified_receipts.json"

REQUIRED_SCENES = (
    "assets/locations/washing-machines/scene02.png",
    "assets/locations/washing-machines/showroom.png",
    "assets/locations/washing-machines/cta.png",
)

def load_manifest():
    m = json.loads(Path(MODEL_MANIFEST).read_text(encoding="utf-8"))
    assert m["expected_total_bytes"] == 34180083066
    assert m["storage"]["bucket"] == BUCKET
    assert len(m["objects"]) == 9
    return m

def get_s3():
    import boto3
    from botocore.config import Config
    a = os.environ.get("RUNPOD_S3_ACCESS_KEY_ID", "")
    b = os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY", "")
    if not (a and b):
        raise RuntimeError("S3_CREDS_MISSING")
    return boto3.client("s3", region_name="eu-ro-1", endpoint_url=S3_ENDPOINT,
        aws_access_key_id=a, aws_secret_access_key=b,
        config=Config(signature_version="s3v4", s3={"addressing_style":"path"},
                      connect_timeout=20, read_timeout=60,
                      retries={"max_attempts":3,"mode":"standard"}))

def head_or_none(client, key):
    from botocore.exceptions import ClientError
    try:
        return client.head_object(Bucket=BUCKET, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404","NotFound","NoSuchKey"):
            return None
        raise RuntimeError("S3_HEAD_DENIED_OR_FAILED") from None

def audit(client, m, approved_qa=False):
    blockers=[]
    seen=[]
    for obj in m["objects"]:
        key=m["storage"]["prefix"] + obj["name"]
        h=head_or_none(client,key)
        if h is None or int(h["ContentLength"]) != obj["bytes"]:
            blockers.append("MODEL_MISSING_OR_WRONG_SIZE:"+obj["name"])
        else:
            seen.append(obj["name"])
    hero=head_or_none(client,CHARACTER)
    hero_uploaded=bool(hero and int(hero.get("ContentLength",0))==HERO_SIZE
          and hero.get("Metadata",{}).get("sha256","")==HERO_SHA)
    if not hero_uploaded: blockers.append("MASTER_CHARACTER_NOT_VERIFIED_ON_S3")
    # Support audio metadata SHA-256 from staging workflow. Read-only HEAD is not lip-sync QA.
    audios=[]
    receipts=json.loads(Path(AUDIO_RECEIPTS).read_text(encoding="utf-8"))
    if len(receipts["clips"])!=3 or receipts["human_listening_qa_passed"] is not False:
        raise ValueError("NEURAL_AUDIO_RECEIPTS_INVALID")
    for clip in receipts["clips"]:
        name=clip["id"]
        key=clip["s3_key"]
        if not key.startswith("assets/audio/washing-machines/hindi_neural_v1/") or not key.endswith(clip["sha256"][:16]+".mp3"):
            raise ValueError("AUDIO_RECEIPT_PATH_MISMATCH")
        h=head_or_none(client,key)
        if (h is None or int(h.get("ContentLength",0)) != clip["bytes"]
            or h.get("Metadata",{}).get("sha256","")!=clip["sha256"]):
            blockers.append("NEURAL_AUDIO_NOT_STAGED:"+name)
        else:
            audios.append(name)
    locations=[]
    for key in REQUIRED_SCENES:
        h=head_or_none(client,key)
        if h and int(h.get("ContentLength",0))>10000:
            locations.append(key)
        else:
            blockers.append("SCENE_ART_NOT_STAGED:"+key.rsplit("/",1)[-1])
    if not approved_qa:
        blockers.append("HUMAN_HINDI_VOICE_AND_VISUAL_QA_PENDING")
    blockers.extend([
        "LIVE_TOP_5_VALIDATION_NOT_RUN",
        "GPU_RATE_AND_TIMEOUT_LIMIT_NOT_APPROVED",
        "REAL_WAN_MOTION_AND_LIPSYNC_NOT_RENDERED",
    ])
    return {
      "status":"GPU_RENDER_BLOCKED" if blockers else "READY_FOR_CONTROLLED_GPU_QA",
      "model_files_verified":len(seen),"model_files_required":len(m["objects"]),
      "master_original_character_on_s3":hero_uploaded,
      "neural_audio_clips_staged":len(audios),
      "location_art_files_staged":len(locations),
      "location_art_files_required":len(REQUIRED_SCENES),
      "blockers":blockers,"gpu_created":False,"published":False,
      "billing_note":"100GB existing Standard network volume continues to accrue storage charges"
    }

def main():
    try:
        report=audit(get_s3(),load_manifest())
        out=Path("output/washing-final-readiness.json")
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(report,indent=2)+"\n")
        print("WASHING_RENDER_STATUS="+report["status"])
        print("WAN_MODEL_FILES="+str(report["model_files_verified"])+"/"+str(report["model_files_required"]))
        print("STAGED_HINDI_CLIPS="+str(report["neural_audio_clips_staged"])+"/3")
        print("MASTER_PINK_LADY_S3="+str(report["master_original_character_on_s3"]).lower())
        print("SCENES_ON_S3="+str(report["location_art_files_staged"])+"/3")
        for b in report["blockers"]:
            print("PENDING="+b)
        return 0 if report["model_files_verified"]==report["model_files_required"] else 1
    except Exception:
        print("WASHING_RENDER_STATUS=UNVERIFIED_API_OR_CONFIGURATION_ERROR")
        return 1
if __name__=="__main__":
    sys.exit(main())
