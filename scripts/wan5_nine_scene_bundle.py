"""Package exactly nine visual-QA approved images into immutable Wan input bundle.

This CPU-only command never purchases GPU time or reads any secret.
If the current preview crops still contain old text, it MUST refuse.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
from trustfolio_video.clean_gpu_gate import check_gate
from trustfolio_video.contract import Blocked
from trustfolio_video.wan5_nineshot import verified_plan

def package(story_path,plates_manifest,out_root):
    story=json.loads(Path(story_path).read_text(encoding="utf-8"))
    gpu=verified_plan(story)
    clean=check_gate(story_path,plates_manifest)
    base=Path(out_root)
    folder=base/"assets/clean-plates/washing-machines"
    folder.mkdir(parents=True,exist_ok=True)
    records=[]
    for i,(plate,shot) in enumerate(zip(clean["clean_plates"],gpu["shots"]),1):
        sid=f"scene{i:02d}"
        if plate["scene_id"]!=sid or shot["scene_id"]!=sid:
            raise Blocked("SCENE_ORDER_MISMATCH")
        path=Path(plate["clean_plate_path"])
        output=folder/(sid+".png")
        shutil.copyfile(path,output)
        digest=hashlib.sha256(output.read_bytes()).hexdigest()
        if digest!=plate["clean_plate_sha256"]:
            raise Blocked("APPROVED_IMAGE_CHANGED_DURING_COPY")
        records.append({
            "id":sid,
            "plate_path":f"assets/clean-plates/washing-machines/{sid}.png",
            "plate_sha256":digest,
            "reference_sha256":shot["source_storyboard_sha256"],
            "source_text_burned_in":False,
            "visual_qa_approved":True,
            "character_identity_approved":True,
            "prompt":shot["motion_prompt"],
        })
    payload={
        "version":1,"category":"washing-machines",
        "state":"CLEAN_PLATES_USER_VISUALLY_APPROVED",
        "motion_job_hash":gpu["motion_job_hash"],
        "private_qa":True,"paid_gpu_authorized":False,"published":False,
        "shots":records,
    }
    f=base/"jobs/washing-9scene-v1/gpu-input.json"
    f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("WAN9_APPROVED_CPU_BUNDLE="+str(f))
    print("WAN9_PAID_GPU_ALLOCATED=false")
    return f

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--story",required=True)
    parser.add_argument("--clean-plate-manifest",required=True)
    parser.add_argument("--output",default="output/wan9-approved-inputs")
    args=parser.parse_args()
    package(args.story,args.clean_plate_manifest,args.output)

if __name__=="__main__":main()
