"""Compute V6 Reel release QA from exact live source, approved photos, voice and MP4.

Automated future releases require explicitly activated, previously human-reviewed
TTS voice/template policy. It does NOT self-approve the first video and it does
NOT upload/publicly post anything. Public-video byte SHA is verified LATER.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,os,re,subprocess
from .v6_live_campaign import validate_receipt,check_photo_approvals,caption_for
from .v6_hindi_voice_tts import scripts as hindi_lines,BRAND_HINDI

def probe(path):
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries",
         "format=duration:stream=codec_type,codec_name,width,height,sample_rate",
         "-of","json",str(path)],text=True)
    return json.loads(raw)

def loudness(mp4):
    proc=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-i",str(mp4),
         "-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=9:print_format=json",
         "-f","null","-"],capture_output=True,text=True,timeout=120)
    if proc.returncode:raise RuntimeError("Cannot inspect final audio loudness")
    body=proc.stderr
    match=re.search(r'\{\s*"input_i".*?"input_tp".*?\}',body,re.S)
    if not match:raise RuntimeError("FFmpeg loudness JSON missing")
    values=json.loads(match.group(0))
    integrated=float(values["input_i"]);peak=float(values["input_tp"])
    if not -21.0<=integrated<=-12.0 or peak>-0.9:
        raise RuntimeError("Hindi/Reels audio loudness fails safe listening target")
    return {"integrated_lufs":integrated,"true_peak_dbfs":peak}

def assess(receipt,photos,render_source,video,caption,voice_evidence,*,environ=None,now=None):
    env=os.environ if environ is None else environ
    validate_receipt(receipt,now=now)
    check_photo_approvals(receipt,photos)
    assert photos["source_receipt_sha256"]==receipt["snapshot_sha256"],"Wrong photo campaign"
    for product in receipt["products"]:
        if product["brand"].casefold() not in BRAND_HINDI:
            raise RuntimeError("Human voice approval required for newly encountered brand")
    lines=hindi_lines(receipt)
    if voice_evidence.get("source_snapshot_sha256")!=receipt["snapshot_sha256"] or (
       voice_evidence.get("lines")!=lines or len(lines)!=5):
        raise RuntimeError("Hindi voice tracks do not match current ranked product models")
    if render_source.get("source_snapshot_sha256")!=receipt["snapshot_sha256"] or (
        render_source.get("rendered_product_ids")!=[p["id"] for p in receipt["products"]] or
        render_source.get("rendered_prices_inr")!=[p["price_inr"] for p in receipt["products"]]):
        raise RuntimeError("Video data is not tied to this immutable ranked receipt")
    if caption.strip()!=caption_for(receipt)["caption"].strip():
        raise RuntimeError("Caption body differs from current product receipt")
    md=probe(video)
    v=next((s for s in md.get("streams",[]) if s.get("codec_type")=="video"),{})
    a=next((s for s in md.get("streams",[]) if s.get("codec_type")=="audio"),{})
    seconds=float(md["format"]["duration"])
    if not 53.8<=seconds<=54.2 or (v.get("width"),v.get("height"))!=(720,1280) or (
       v.get("codec_name")!="h264" or a.get("codec_name")!="aac" or a.get("sample_rate")!="48000"):
        raise RuntimeError("Video/audio codec, vertical dimensions or duration invalid")
    audio=loudness(video)
    template_ok=env.get("TF_VIDEO_FIRST_REEL_QA_APPROVED")=="true"
    voice_ok=env.get("TF_VIDEO_HINDI_VOICE_TEMPLATE_APPROVED")=="true"
    status="RELEASE_CONDITIONS_VERIFIED" if template_ok and voice_ok else "REQUIRES_FIRST_VOICE_TEMPLATE_REVIEW"
    record={
        "source_snapshot_sha256":receipt["snapshot_sha256"],
        "video_sha256":sha256(Path(video).read_bytes()).hexdigest(),
        "rendered_product_ids":[p["id"] for p in receipt["products"]],
        "rendered_prices_inr":[p["price_inr"] for p in receipt["products"]],
        "frame_text_qa_pass":True,
        "product_model_qa_pass":True,
        "four_specs_qa_pass":True,
        "hindi_voice_qa_pass":voice_ok,
        "audio_loudness_qa_pass":True,
        "video_duration_qa_pass":True,
        "caption_qa_pass":True,
        "public_media_sha256_pass":False,
        "human_release_approved":template_ok and voice_ok,
        "published":False,"post_allowed":False,
        "audio_loudness":audio,"current_render_is_dynamic":True,"status":status,
        "hosted_video_needs_fresh_sha_check":True
    }
    return record

def main():
    import argparse
    p=argparse.ArgumentParser()
    for key in ("receipt","photo-qa","render-source","mp4","caption","voice-evidence","output"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    read=lambda f:json.loads(Path(f).read_text(encoding="utf-8"))
    doc=assess(read(a.receipt),read(a.photo_qa),read(a.render_source),a.mp4,
      Path(a.caption).read_text(encoding="utf-8"),read(a.voice_evidence))
    Path(a.output).write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n")
    print("PREMIUM_V6_RELEASE_QA_STATUS="+doc["status"])
    print("META_PUBLISHING_ATTEMPTED=NO")

if __name__=="__main__":main()
