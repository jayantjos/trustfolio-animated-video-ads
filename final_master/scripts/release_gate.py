"""Release gate: no social publishing until the exact five-product video passes QA.
Offline and deterministic. Never auto-approve generated mouth motion or SKU photos.
"""
from __future__ import annotations
import argparse, json, hashlib, pathlib

def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def check(products, audio_dir, video_qa):
    failures=[]
    rows=products.get("products",[])
    if len(rows)!=5 or [x.get("rank") for x in rows]!=[1,2,3,4,5]:
        failures.append("five exact ordered product ranks required")
    ids=[x.get("product_id") for x in rows]
    if len(ids)!=len(set(ids)) or any(not x for x in ids):
        failures.append("duplicate or missing product identities")
    snap=products.get("snapshot_sha256")
    if not isinstance(snap,str) or len(snap)!=64:
        failures.append("missing snapshot identity")
    for i,row in enumerate(rows,1):
        proof_path=pathlib.Path(audio_dir)/f"rank_{i:02d}.json"
        wav_path=pathlib.Path(audio_dir)/f"rank_{i:02d}.wav"
        if not proof_path.is_file() or not wav_path.is_file():
            failures.append(f"rank {i}: missing original voice artifact")
            continue
        try: proof=json.loads(proof_path.read_text())
        except (OSError,ValueError):
            failures.append(f"rank {i}: broken voice receipt");continue
        if proof.get("rank")!=i or proof.get("product_id")!=row.get("product_id"):
            failures.append(f"rank {i}: voice product identity mismatch")
        if proof.get("source_snapshot_sha256")!=snap:
            failures.append(f"rank {i}: different Top5 data snapshot")
        if proof.get("wav_sha256")!=sha(wav_path):
            failures.append(f"rank {i}: WAV checksum mismatch")
        if proof.get("seconds",100)>9.7 or not proof.get("fits_ten_seconds",False):
            failures.append(f"rank {i}: narration exceeds original chapter")
        if proof.get("voice_approved") is not True:
            failures.append(f"rank {i}: character voice listening QA missing")
    for row in rows:
        if row.get("price_label")!="LIVE" or row.get("live_price_status")!="ok":
            failures.append(f"rank {row.get('rank')}: non-live or unverified price")
        if not row.get("image_url","").startswith("https://"):
            failures.append(f"rank {row.get('rank')}: missing retailer photo source")
    duration=video_qa.get("duration_seconds")
    if not isinstance(duration,(float,int)) or duration<=0 or duration>95:
        failures.append("invalid natural-duration video")
    if video_qa.get("all_required_scenes_present") is not True:
        failures.append("required original scenes or product chapters missing")
    for name in ("exact_dynamic_photos","dynamic_text_replacement","lip_sync_verified",
                 "background_sound_preserved","original_character_position_preserved",
                 "cta_qr_verified","product_photo_model_identity_verified"):
        if video_qa.get(name) is not True:
            failures.append(name+" not independently verified")
    if video_qa.get("source_snapshot_sha256")!=snap:
        failures.append("video and voice live snapshots disagree")
    return {"publish_allowed":not failures,"failures":failures,"budget_inr":products.get("budget_inr"),
      "source_snapshot_sha256":snap}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--products",required=True)
    a.add_argument("--audios",required=True)
    a.add_argument("--video-qa",required=True)
    a.add_argument("--out",required=True)
    args=a.parse_args()
    p=json.loads(pathlib.Path(args.products).read_text())
    q=json.loads(pathlib.Path(args.video_qa).read_text())
    result=check(p,args.audios,q)
    pathlib.Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("PUBLISH_ALLOWED="+str(result["publish_allowed"]).lower())
    for failure in result["failures"]:print("BLOCKED:",failure)
    if not result["publish_allowed"]:raise SystemExit(2)
if __name__=="__main__":main()
