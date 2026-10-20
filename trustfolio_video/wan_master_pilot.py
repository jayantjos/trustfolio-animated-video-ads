"""TrustFolio APPROVED-MASTER image-to-video GPU adapter, private QA ONLY.

Source scenes: user-supplied originals, SHA-locked. Output from AI image-to-video
will still require human reference-match and exact actual retailer-product
validation; it is not a production ad. No stock videos, generic box mascots,
price/rank invented by AI, social publishing or paid API integrations.

Compatible upstream: Wan-Video/Wan2.2 @ 1ea34ff48f87168174e12956e200b1d908b1c5ff
Wan2.2-TI2V-5B: requires >=24GB CUDA VRAM, model weights supplied separately.
Wan-Animate-14B is inappropriate without a real pose/face driving video.
LivePortrait default InsightFace models are restricted for commercial use.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

WAN_SHA="1ea34ff48f87168174e12956e200b1d908b1c5ff"
STORY_SHA="2a2af14bae1c5c3f49cec647b1d67b1016e01db98a48ed54374bcdd56d642a1e"
PARADE_SHA="bcc90bf85a9c2f4fee8b57b0c02b78e5b80f4c8a184b5d528ccb21a1ca934e0c"
MASTER_SHA="c5ce062090f34ab414a125d91c3ad39ff81f37a8ad4e629726e5ced0f3458ba1"
MODEL="Wan2.2-TI2V-5B"
PROMPTS={
  "lady":"Original same high-detail colorful 3D cartoon woman wearing bright pink kurta stands in sunny tropical Indian laundry village, facing a mountain of laundry. Her hair flows gently, head turns, fingers grip hair in surprise, eyes blink and mouth moves in an understandable Hindi reaction. Camera slowly pushes in with true body and hair movement. Keep facial identity, exact costume, color palette and original cinematic environment. No logos, no prices, no text, no additional characters. Family safe, coherent expression, physically grounded cartoon action.",
  "washer":"One original large friendly washing machine in the sunny tropical Indian laundry village, preserve the SAME glossy body, drum, face, hands, shoes and identity as source artwork. The machine walks naturally with independently moving shoes and arms, turns to respond to the lady, blinks and mouths dialogue, bubbly wash effect in scene, rich PBR lighting and contact shadows. One continuous movie shot with consistent geometry, no text, no invented logos, no product claims, no prices. No extra limbs, no deforming appliance.",
}

def file_hash(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def guard_file(path,expected):
    p=Path(path).resolve(strict=True)
    if not p.is_file() or file_hash(p)!=expected:
        raise ValueError("Source image hash does not match approved Master Theme: "+p.name)
    return p

def prepare(story,parade,master,out):
    """Extract ONLY the two character reference areas, never sample offer captions."""
    from PIL import Image,ImageOps,ImageFilter,ImageDraw,ImageFont
    story=guard_file(story,STORY_SHA)
    parade=guard_file(parade,PARADE_SHA)
    master=guard_file(master,MASTER_SHA)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    # Source crop areas omit illustrative 'rank', product prices and heading.
    refs=[
      ("lady",story,(9,53,212,339),"woman_with_pink_kurta"),
      ("washer",parade,(258,704,659,1312),"front_load_3d_cartoon_mascot"),
    ]
    shots=[]
    for name,source,rect,role in refs:
        image=Image.open(source).convert("RGB").crop(rect)
        # Maintain center subject, without writing unverifiable SKU text.
        image=ImageOps.fit(image,(704,1280),method=Image.Resampling.LANCZOS,centering=(.5,.47))
        path=out/(name+"-approved-master-character.png")
        image.save(path,optimize=True)
        shots.append({
            "scene_id":name,"character_role":role,
            "approved_source_sha256":file_hash(source),
            "approved_source_path_hint":source.name,
            "extraction_rect":list(rect),
            "image_file":path.name,"image_sha256":file_hash(path),
            "generation_prompt":PROMPTS[name],
            "required_identity_match":"HUMAN_VISUAL_REVIEW_PENDING",
            "dialogue_and_lipsync":"SEPARATE_HINDI_VOICE_TIMING_QA_REQUIRED",
            "commercial_licensing":"PENDING_EXTERNAL_AD_RIGHTS_EVIDENCE",
        })
    manifest={
       "schema_version":1,
       "mode":"PRIVATE_QA_REFERENCE_ANIMATION_NOT_PRODUCT_AD",
       "approved_master_sha256":file_hash(master),
       "style_frozen":True,
       "category":"washing-machines",
       "source_story":"approved user cinematic storyboard, illustrative-only characters",
       "camera":"2 independent full-screen image-to-video cinematic shots",
       "model":MODEL,
       "wan_upstream_commit_required":WAN_SHA,
       "gpu_min_vram_gb":24,
       "paid_api_allowed":False,
       "publishing_enabled":False,
       "no_price_or_rank_claims":True,
       "narration_model":"NOT_YET_RENDERED",
       "shots":shots,
    }
    (out/"motion-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return manifest

def cuda_report():
    result={"cuda_available":False,"max_total_vram_gb":0.0,"minimum_required_vram_gb":24}
    try:
        import torch
        if torch.cuda.is_available():
            devices=[round(torch.cuda.get_device_properties(i).total_memory/(1024**3),2)
                for i in range(torch.cuda.device_count())]
            result.update(cuda_available=True,max_total_vram_gb=max(devices),
                          detected_device_vram_gb=devices)
    except (ImportError,RuntimeError):
        pass
    result["gpu_meets_requirement"]=result["max_total_vram_gb"]>=24
    return result

def secure_real_run(manifest_dir,wan_dir,weights_dir,output_dir,*,acknowledge=False):
    """Run only preinstalled, pinned open-source code on an authorized LOCAL GPU.

    Does NOT git clone, install scripts, auto-download large weights or use paid
    providers. Process is blocked before any inference if requirements missing.
    """
    if not acknowledge:raise RuntimeError("GPU render requires explicit --allow-local-gpu")
    cap=cuda_report()
    if not cap["gpu_meets_requirement"]:
        raise RuntimeError("Model needs >=24GB CUDA VRAM; insufficient GPU; NO fake MP4 created.")
    wan=Path(wan_dir).resolve(strict=True)
    weights=Path(weights_dir).resolve(strict=True)
    manifest_dir=Path(manifest_dir).resolve(strict=True)
    if not wan.is_dir() or not (wan/"generate.py").is_file():
        raise RuntimeError("An audited local Wan2.2 source checkout is required")
    commit=subprocess.run(["git","-C",str(wan),"rev-parse","HEAD"],
                          capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    if commit!=WAN_SHA:raise RuntimeError("Unverified Wan2.2 code revision; refuse")
    if not weights.is_dir() or not any(weights.rglob("*.safetensors")):
        raise RuntimeError("Local model weights missing; no automatic checkpoint download")
    data=json.loads((manifest_dir/"motion-manifest.json").read_text(encoding="utf8"))
    if data.get("publishing_enabled") or data.get("mode")!="PRIVATE_QA_REFERENCE_ANIMATION_NOT_PRODUCT_AD":
        raise RuntimeError("Production/publishing context refused")
    shots=data.get("shots",[])
    if len(shots)!=2 or {x["scene_id"] for x in shots}!={"lady","washer"}:
        raise RuntimeError("Unexpected character shot manifest")
    target=Path(output_dir).resolve()
    target.mkdir(parents=True,exist_ok=True)
    evidence=[]
    for shot in shots:
        img=guard_file(manifest_dir/shot["image_file"],shot["image_sha256"])
        dst=target/(shot["scene_id"]+"-raw-wan-demo.mp4")
        cmd=[sys.executable,str(wan/"generate.py"),
             "--task","ti2v-5B","--size","704*1280",
             "--ckpt_dir",str(weights),"--offload_model","True",
             "--convert_model_dtype","--t5_cpu",
             "--image",str(img),"--prompt",shot["generation_prompt"],
             "--save_file",str(dst)]
        start=datetime.now(timezone.utc).isoformat()
        subprocess.run(cmd,cwd=wan,check=True,timeout=7200)
        if not dst.exists() or dst.stat().st_size<100000:
            raise RuntimeError("WAN render did not produce real encoded footage")
        probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams",
             "-show_format","-of","json",str(dst)],timeout=20))
        v=next((s for s in probe["streams"] if s["codec_type"]=="video"),None)
        if not v or int(v["width"])<600 or float(probe["format"]["duration"])<2:
            raise RuntimeError("Render technical QA failed")
        evidence.append({"scene":shot["scene_id"],"model":MODEL,"upstream_sha":WAN_SHA,
          "source_image_sha256":shot["image_sha256"],
          "render_file":dst.name,"video_sha256":file_hash(dst),
          "gpu_vram_gb":cap["max_total_vram_gb"],
          "real_ai_inference_executed":True,"started_utc":start,
          "human_appearance_approved":False,"natural_hindi_approved":False,
          "publishing_enabled":False})
    (target/"gpu-inference-qa.json").write_text(json.dumps(evidence,indent=2)+"\n")
    return evidence

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--action",choices=("check","prepare","render"),default="check")
    a.add_argument("--lady-art")
    a.add_argument("--machine-art")
    a.add_argument("--master-art")
    a.add_argument("--output-dir",default="out/wan-qa")
    a.add_argument("--manifest-dir")
    a.add_argument("--wan-dir")
    a.add_argument("--weights-dir")
    a.add_argument("--allow-local-gpu",action="store_true")
    arg=a.parse_args()
    if arg.action=="check":
        report=cuda_report()
        report["wan_model"]=MODEL;report["inference_executed"]=False
        report["production_approved"]=False;report["publishing_enabled"]=False
        print(json.dumps(report,indent=2));return
    if arg.action=="prepare":
        for f in (arg.lady_art,arg.machine_art,arg.master_art):
            if not f:raise ValueError("All three approved source artworks must be present")
        data=prepare(arg.lady_art,arg.machine_art,arg.master_art,arg.output_dir)
        print(json.dumps({"prepared_character_shots":len(data["shots"]),
                          "mode":data["mode"],"publishing_enabled":False},indent=2));return
    if not all((arg.manifest_dir,arg.wan_dir,arg.weights_dir)):
        raise ValueError("--manifest-dir, --wan-dir, --weights-dir required for real GPU inference")
    secure_real_run(arg.manifest_dir,arg.wan_dir,arg.weights_dir,arg.output_dir,
                     acknowledge=arg.allow_local_gpu)

if __name__=="__main__":main()
