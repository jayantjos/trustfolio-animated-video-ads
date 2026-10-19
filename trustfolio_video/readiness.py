"""Read-only release readiness audit. It cannot publish, or touch the VPS.

production_ready is a review flag, NEVER action permission.
Social publishing remains separately disabled in trustfolio_video.publishing.
"""
import argparse
import json
from pathlib import Path

from .contract import validate,Blocked
from .educational import validate_master,load_master

EXTERNAL_RECEIPTS=(
 "retailer_image_commercial_rights",
 "verified_official_logo_art",
 "natural_hindi_voice_human_approval",
 "cartoon_visual_human_approval",
 "claims_editorial_review",
 "social_provider_oauth_verified",
 "explicit_owner_publish_permission",
 "idempotent_publication_ledger_review",
)

def source_audit(envelope, now=None):
    try:
        approved=validate(envelope,now=now)
    except (Blocked,KeyError,TypeError,ValueError) as exc:
        return {"state":"BLOCKED","reason":str(exc)[:1500],
                "source_sha256":envelope.get("response_sha256"),
                "individual_fresh_prices_verified":False}
    return {"state":"SOURCE_CONTRACT_ONLY_PASSED",
            "source_sha256":approved["source_sha256"],
            "individual_fresh_prices_verified":True,
            "warning":"Strict API price proof does not grant media asset rights."}

def video_audit(qa):
    if not isinstance(qa,dict):
        return {"state":"MISSING","reason":"No MP4 technical report"}
    passed=qa.get("status") in (
        "PRIVATE_HISTORICAL_PREMIUM_VIDEO_TECHNICAL_QA_PASSED",
        "HISTORICAL_DEMO_RENDERED_NOT_APPROVED_FOR_PUBLICATION",
    )
    disabled=qa.get("publish_enabled") is not True and qa.get("publishing_enabled") is not True
    return {"state":"TECHNICAL_QA_ONLY" if passed and disabled else "UNVERIFIED_OR_UNSAFE",
            "video_sha256":qa.get("video_sha256"),
            "audio_codec":qa.get("audio_codec"),
            "source_hash":qa.get("source_hash") or qa.get("source_sha256"),
            "publishing_enabled":not disabled}

def release_report(envelope,story=None,qa=None,receipts=None,now=None):
    supported=validate_master(load_master())
    source=source_audit(envelope,now=now)
    actual_products=((envelope.get("response") or {}).get("data") or {}).get("products") or []
    expected_ids=[p.get("id") for p in actual_products if isinstance(p,dict)]
    if isinstance(story,dict):
        identity=(story.get("ranked_source_ids")==expected_ids and
                  story.get("source_sha256")==envelope.get("response_sha256") and
                  story.get("publishing_enabled") is False and
                  story.get("campaign",{}).get("category") in supported)
    else:
        identity=False
    story_state={"state":"IDENTITY_ONLY_PASSED" if identity else "MISSING_OR_SOURCE_MISMATCH",
                 "rank_and_hash_match":identity}
    video=video_audit(qa)
    receipts=receipts if isinstance(receipts,dict) else {}
    missing=[key for key in EXTERNAL_RECEIPTS
             if not isinstance(receipts.get(key),dict)
             or receipts[key].get("status")!="externally_verified"
             or not isinstance(receipts[key].get("evidence_id"),str)
             or len(receipts[key]["evidence_id"])<8]
    blockers=[]
    if source["state"]=="BLOCKED":blockers.append("individual_price_freshness_proof")
    if not identity:blockers.append("authoritative_ranked_storyboard")
    if video["state"]!="TECHNICAL_QA_ONLY":blockers.append("real_h264_aac_video_qa")
    if missing:blockers.append("commercial_rights_voice_brand_and_external_approvals")
    # Publishing is intentionally not implemented for any provider in this repo.
    blockers.append("official_social_publish_adapter_and_idempotency_not_approved")
    return {"version":1,"status":"BLOCKED_NOT_PRODUCTION_APPROVED",
      "production_ready":False,"publishing_enabled":False,
      "critical_blockers":blockers,"source":source,"story":story_state,
      "video":video,
      "receipts":{"received":len(EXTERNAL_RECEIPTS)-len(missing),
                  "missing_or_unverified":missing,
                  "warning":"Typed receipt claims are not cryptographically signed"},
      "supported_backend_categories":len(supported),"disabled_future_slots":10,
      "social":{"instagram_reels":"OFF","facebook_reels":"OFF",
                "youtube_shorts":"OFF","linkedin":"OFF","x":"OFF"},
      "note":"Cannot be used as a production publishing authorization."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",required=True)
    ap.add_argument("--story")
    ap.add_argument("--video-qa")
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    envelope=json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    story=json.loads(Path(args.story).read_text(encoding="utf-8")) if args.story else None
    qa=json.loads(Path(args.video_qa).read_text(encoding="utf-8")) if args.video_qa else None
    report=release_report(envelope,story,qa)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("RELEASE_STATUS="+report["status"])
    for issue in report["critical_blockers"]:
        print("BLOCKER="+issue)
    print("PRODUCTION_PUBLISHING_ENABLED=false")

if __name__=="__main__":
    main()
