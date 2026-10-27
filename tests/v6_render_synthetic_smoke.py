"""One-time synthetic 54s integration test using user's TWO uploaded verified masters.

Never fetches real prices, uses invented toy rectangle products in test only.
Video has no real ad value, no audio narration and is NEVER publishable.
"""
import json,hashlib,tempfile
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageDraw
from trustfolio_flow.live import normalize_live,campaign
from trustfolio_flow.v6_dynamic_renderer import encode

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"assets/video/washing-machines/trustfolio_washing_40s_visual_master_v1.mp4"
B=ROOT/"assets/video/washing-machines/trustfolio_washing_v6_54s_approved_visual_master.mp4"

def run():
    now=datetime.now(timezone.utc)
    payload={"category":"washing-machines","products":[]};live=[]
    tmp=Path("handoff/synthetic_v6_engine_test");tmp.mkdir(parents=True,exist_ok=True)
    photo_dir=tmp/"photos";photo_dir.mkdir(exist_ok=True)
    entries=[]
    for rank in range(1,6):
        pid=f"{rank:024x}"
        p={"rank":rank,"id":pid,"title":f"SYNTHETIC TEST MODEL {rank} 8 kg 5 Star",
           "brand":f"TEST{rank}","platform":"amazon","price_inr":19000+rank,
           "main_image":f"https://m.media-amazon.com/images/I/test-{rank}.jpg",
           "specifications":{"Capacity":"8 kg","Load Type":"Top Load",
              "Energy Rating":"5 Star","Automation Type":"Fully Automatic"},
           "in_stock":True,"is_active":True}
        payload["products"].append(p)
        live.append({"id":pid,"deleted":False,"live":{"status":"ok","price_inr":19000+rank,
            "checked_at":now.isoformat()}})
        im=Image.new("RGBA",(500,500),(0,0,0,0))
        ImageDraw.Draw(im).rectangle((130,95,371,460),fill=(25*rank,45,90,255))
        ImageDraw.Draw(im).text((150,140),f"TEST {rank}",fill="white")
        file=photo_dir/f"rank_{rank:02d}.png";im.save(file)
        entries.append({"rank":rank,"id":pid,"image_url":p["main_image"],
          "image_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
          "model_identity_ok":True,"product_photo_ok":True,"commercial_usage_ok":True})
    receipt=normalize_live(payload,live,spec=campaign("washing-machines",25000),now=now)
    manifest={"source_receipt_sha256":receipt["snapshot_sha256"],"products":entries}
    outfile=tmp/"synthetic_visual_only.mp4"
    audit=encode(receipt,manifest,A,B,photo_dir,outfile,now=now)
    assert audit["post_allowed"] is False
    import subprocess
    # Mark fake dataset indelibly before artifact upload.
    marked=tmp/"synthetic_not_for_posting.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-i",str(outfile),"-vf","drawtext=text='SYNTHETIC TEST ONLY - NEVER POST':fontcolor=white:fontsize=25:"
        "box=1:boxcolor=red@0.78:boxborderw=10:x=(w-text_w)/2:y=42",
        "-c:v","libx264","-preset","veryfast","-crf","25","-c:a","copy",str(marked)],check=True)
    print("V6_REAL_VIDEO_ENGINE_END_TO_END_CPU_SMOKE=PASS")
    print("MEDIA_FOR_SOCIAL_POSTING=DISABLED")
    print("VIDEO="+str(marked))
if __name__=="__main__":run()
