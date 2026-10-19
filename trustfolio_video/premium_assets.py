"""Strict premium CGI asset intake/readiness audit. No network access, no publishing.

Treat low-poly Blender concepts as diagnostic-only. The required upgrade is
five genuine, individually identifiable approved product character rigs,
licensed cinematic backgrounds, correct TrustFolio logo, PBR, natural Hindi
dialogue and human scene-by-scene approval. This module only validates receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"config"/"premium_asset_requirements_20.json"
REFERENCE=ROOT/"config"/"approved_premium_3d_visual_contract.json"
MASTER=ROOT/"config"/"category_education_30.json"
VALID_SUFFIX={".glb",".gltf",".blend",".fbx",".obj",".png",".webp",".jpg",
              ".jpeg",".hdr",".exr",".wav",".flac",".mp3",".ogg",".json"}
HOSTS={"polyhaven.com","www.polyhaven.com","blendkit.com","www.blendkit.com",
       "kenney.nl","www.kenney.nl","trustfolio.in","www.trustfolio.in"}
MAX_FILE_BYTES=600_000_000
HASH=re.compile(r"^[0-9a-f]{64}$")
PROVENANCE_FIELDS={
 "file","sha256","source_url","license_name","license_url",
 "commercial_use_verified","license_verified_at","rightsholder",
 "asset_model_version","pixel_or_mesh_quality_human_approved",
}

class AssetBlocked(ValueError):pass

def master():
    return json.loads(MASTER.read_text(encoding="utf8"))

def lock():
    return json.loads(REFERENCE.read_text(encoding="utf8"))

def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf8"))

def check_20_registry(state=None):
    state=state if state is not None else manifest()
    approved=lock()
    verified={s["backend_slug"] for s in master()["slots"] if s["enabled"]}
    slots=state.get("slots")
    if not isinstance(slots,list) or len(slots)!=20:
        raise AssetBlocked("Premium asset manifest must contain exactly 20 supported categories")
    order=[s.get("category_slug") for s in slots]
    if order!=approved["category_order"] or set(order)!=verified:
        raise AssetBlocked("Premium worlds cannot invent/reorder backend categories")
    if any(s.get("automatic_publishing_enabled") is not False for s in slots):
        raise AssetBlocked("Publication is forbidden in asset staging")
    if any(s.get("human_premium_reference_approved") is True and not
           s.get("complete_high_fidelity_scene") for s in slots):
        raise AssetBlocked("No low-poly demo can be declared premium")
    return slots

def check_receipt(receipt,storage_root,*,allowed_hosts=HOSTS):
    """Read local file only. Reject symlinks/traversal and incomplete rights."""
    if not isinstance(receipt,dict) or not PROVENANCE_FIELDS.issubset(receipt):
        raise AssetBlocked("Missing or incomplete commercial asset provenance")
    file=receipt["file"]
    if not isinstance(file,str) or len(file)>256 or not file:
        raise AssetBlocked("Invalid asset path")
    relative=Path(file)
    if relative.is_absolute() or ".." in relative.parts:
        raise AssetBlocked("Asset path may not escape controlled staging directory")
    base=Path(storage_root).resolve()
    target=(base/relative).resolve()
    if not target.is_relative_to(base) or not target.is_file() or target.is_symlink():
        raise AssetBlocked("Asset is missing, a symlink or outside staging directory")
    if target.suffix.casefold() not in VALID_SUFFIX:
        raise AssetBlocked("Asset file extension is not permitted")
    if target.stat().st_size<=0 or target.stat().st_size>MAX_FILE_BYTES:
        raise AssetBlocked("Asset file empty or too large")
    if not isinstance(receipt["sha256"],str) or not HASH.fullmatch(receipt["sha256"]):
        raise AssetBlocked("Invalid SHA256")
    actual=hashlib.sha256()
    with target.open("rb") as stream:
        for piece in iter(lambda:stream.read(1024*1024),b""):
            actual.update(piece)
    if actual.hexdigest()!=receipt["sha256"]:
        raise AssetBlocked("Asset content checksum mismatch")
    for key in ("source_url","license_url"):
        u=urlsplit(receipt[key])
        if u.scheme!="https" or (u.hostname or "").lower() not in allowed_hosts:
            raise AssetBlocked("Unapproved license/provenance URL")
    if receipt.get("commercial_use_verified") is not True or receipt.get("pixel_or_mesh_quality_human_approved") is not True:
        raise AssetBlocked("Rights or visual quality not independently verified")
    if not all(isinstance(receipt[k],str) and receipt[k].strip()
               for k in ("license_name","rightsholder","asset_model_version","license_verified_at")):
        raise AssetBlocked("Missing license/rightsholder/version or verification date")
    return {
        "file":file,"sha256":receipt["sha256"],"rights_confirmed":True,
        "human_art_asset_approved":True,
        "size_bytes":target.stat().st_size,
    }

def readiness_summary(storage_root=None, *,require_product_ids=None):
    state=manifest()
    slots=check_20_registry(state)
    per=[]
    for row in slots:
        missing=[r for r in state["required_asset_slots"]
                 if r not in {x.get("role") for x in row.get("asset_receipts",[]) if isinstance(x,dict)}]
        blocked=[]
        for receipt in row.get("asset_receipts",[]):
            if not storage_root:
                blocked.append("asset_storage_not_connected")
                break
            try:
                check_receipt(receipt,storage_root)
            except AssetBlocked as exc:
                blocked.append(str(exc))
        if row.get("complete_high_fidelity_scene") is not True:
            blocked.append("no_finished_reference_quality_PBR_CGI_scene")
        if row.get("five_verified_product_3d_characters_ready") is not True:
            blocked.append("five_real_ranked_SKU_characters_unverified")
        if row.get("natural_hindi_dialogue_ready") is not True:
            blocked.append("human_approved_Hindi_voice_missing")
        if row.get("human_premium_reference_approved") is not True:
            blocked.append("visual_reference_quality_NOT_APPROVED")
        if row.get("logo_and_photo_rights_verified") is not True:
            blocked.append("official_logo_and_photo_license_missing")
        if row.get("source_fresh_price_verified") is not True:
            blocked.append("individual_fresh_retailer_price_proof_missing")
        if require_product_ids is not None:
            ids=row.get("source_product_ids")
            if ids != require_product_ids:
                blocked.append("ranked_source_product_ID_binding_not_proven")
        per.append({
            "category_slug":row["category_slug"],
            "status":"BLOCKED_NO_PREMIUM_PUBLICATION",
            "missing_asset_roles":missing,
            "blocking_requirements":sorted(set(blocked)),
            "technical_3d_concept_exists":bool(row.get("technical_environment_available")),
            "premium_approved":False,
            "publishing_enabled":False,
        })
    return {
      "version":1,"status":"PREMIUM_ART_DIRECTION_GATES_BLOCKED",
      "verified_backend_categories":len(per),"unsupported_future_categories":10,
      "technically_renderable_concepts":sum(p["technical_3d_concept_exists"] for p in per),
      "premium_product_ads_approved":0,
      "publishing_enabled":False,
      "why":"Current assets are simple diagnostic geometry, not licensed photo-faithful polished CGI. Hindi voice/retailer sources/logo and artistic approval missing.",
      "asset_library_candidates":[s["source"] for s in state["asset_sources"]],
      "categories":per
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--asset-root",type=Path)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    summary=readiness_summary(args.asset_root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PREMIUM_REFERENCE_QUALITY_APPROVED=false")
    print("ELIGIBLE_PUBLISHING_CATEGORIES=0")
    print("TWENTY_CATEGORY_ASSET_GAPS_EXPORTED="+str(args.output))

if __name__=="__main__":main()
