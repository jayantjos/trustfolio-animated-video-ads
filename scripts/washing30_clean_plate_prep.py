"""Create NINE private I2V plate candidates from approved user storyboard art.

Not GPU render inputs until visual QA. Original source contains baked product
logos, reference prices and brand-specific faces; deterministic cropping and
blur cannot certify all text is removed. Do NOT auto-publish these plates.
"""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image,ImageOps,ImageFilter,ImageDraw

from trustfolio_video.washing30 import verify_reference_images

FRAME=(720,1280)
# All coordinates are pixels in the uploaded 1448x1086 user-owned reference art.
CROPS={
    1:(45,95,685,995), # match startled lead, remove right speech bubble
    2:(120,400,1320,860), # same 5 mascots, exclude heading
    3:(127,214,918,873), # matching sunglasses/thumbnails, exclude price
    4:(140,214,920,878),
    5:(140,224,928,875),
    6:(150,216,930,865),
    7:(172,228,915,885),
    8:(134,408,1290,780), # ranking group without original podium labels
    9:(0,100,627,875), # matching happy lady, screen/CTA composed later
}
# Optical mask (relative to each crop) hides the brand logo/control panel band
# while preserving the face and animated arms. These remain QA CANDIDATES.
HIDE_HEADS={3:(0,0,790,100),4:(0,0,780,86),5:(0,0,788,75),
            6:(0,0,780,96),7:(0,0,745,90)}
def make(output_root):
    srcs=verify_reference_images()
    root=Path(output_root);root.mkdir(exist_ok=True,parents=True)
    details=[]
    for number in range(1,10):
        source=Path(srcs[number-1]["path"])
        im=Image.open(source).convert("RGB")
        if im.size!=(1448,1086):
            raise ValueError("FIXED_VISUAL_REFERENCE_DIMENSIONS_CHANGED")
        background=ImageOps.fit(im,FRAME,method=Image.Resampling.LANCZOS)
        background=background.filter(ImageFilter.GaussianBlur(48))
        background=Image.blend(background,Image.new("RGB",FRAME,(52,21,116)),0.35)
        foreground=im.crop(CROPS[number])
        if number in HIDE_HEADS:
            left,top,right,bottom=HIDE_HEADS[number]
            # Optical inpaint is a visual DRAFT; no one may claim it is guaranteed text-free.
            soft=foreground.filter(ImageFilter.GaussianBlur(25))
            foreground.paste(soft.crop((left,top,right,bottom)),(left,top),Image.new("L",(right-left,bottom-top),200))
        if number in (2,8):
            wide=ImageOps.contain(foreground,(690,820),Image.Resampling.LANCZOS)
            xy=((FRAME[0]-wide.width)//2,(FRAME[1]-wide.height)//2)
        else:
            wide=ImageOps.contain(foreground,(670,1000),Image.Resampling.LANCZOS)
            xy=((FRAME[0]-wide.width)//2,(FRAME[1]-wide.height)//2)
        # Mask the original hard edge to keep a coherent stage, not a pasted rectangle.
        alpha=Image.new("L",wide.size,255)
        edge=ImageDraw.Draw(alpha)
        edge.rounded_rectangle((0,0,wide.width-1,wide.height-1),radius=30,fill=255)
        alpha=alpha.filter(ImageFilter.GaussianBlur(12))
        background.paste(wide,xy,alpha)
        output=root/f"scene{number:02d}.plate-candidate.png"
        background.save(output,optimize=True)
        details.append({"scene_id":f"scene{number:02d}",
                        "visual_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
                        "source_reference_sha256":srcs[number-1]["sha256"],
                        "path":str(output),"bytes":output.stat().st_size,
                        "width":FRAME[0],"height":FRAME[1],
                        "status":"CREATIVE_PLATE_CANDIDATE_NOT_YET_CLEARED_FOR_GPU",
                        "contains_no_baked_brand_guaranteed":False,
                        "expression_visual_qa_approved":False})
    info={"version":1,"scenes":details,"num_scenes":9,
          "all_assets_user_owned_reference":True,
          "new_gpu_authorized":False,"gpu_pods_created":0,
          "publish":False,"pipeline_stage":"CREATIVE_REVIEW_NOT_GPU_APPROVED",
          "requires_visual_check_for_reference_labels":True}
    (root/"plate-manifest.json").write_text(json.dumps(info,indent=2)+"\n")
    return info

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",default="output/washing30-clean-plate-candidates")
    args=p.parse_args();r=make(args.output)
    print("CLEAN_PLATE_CANDIDATES="+str(r["num_scenes"]))
    print("READY_TO_GPU=false")
