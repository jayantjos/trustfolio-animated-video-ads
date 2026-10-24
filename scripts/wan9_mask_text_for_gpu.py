"""Produce 9 portrait Wan reference-animation plates from user-provided story art.

Machine characters, expressions and laundry-world backgrounds remain from the
originals. Dynamic rank, company names, prices and speech text are omitted.
CPU masking alone cannot establish *human* visual QA; never automatically mark
any render plate as fully approved or start billable GPU from this script.
"""
import argparse, hashlib, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw
from trustfolio_video.washing30 import verify_reference_images

CROPS={
1:(15,280,900,1015),2:(0,480,1448,960),3:(195,220,980,905),
4:(235,265,930,910),5:(190,260,995,922),6:(200,272,975,907),
7:(286,150,962,950),8:(0,490,1448,1040),9:(18,245,815,980)}
LOGOS={
2:[(55,462,318,574),(362,479,580,591),(603,477,820,586),
   (863,478,1092,586),(1163,469,1415,574),
   (91,555,274,603),(376,559,539,608),(619,556,802,608),
   (905,553,1040,610),(1181,561,1328,608)],
3:[(380,264,515,308)],
4:[(550,265,790,327)],
5:[(428,270,550,335)],
6:[(440,263,662,333)],
7:[(480,207,555,260)],
8:[(48,380,290,525),(342,365,580,526),(595,364,820,525),
   (846,368,1100,525),(1140,346,1415,520),
   (75,526,255,595),(365,522,544,589),(607,514,797,591),
   (867,510,1050,593),(1170,520,1380,598)],
}
WORDS={
1:[(665,265,900,420)],
3:[(875,213,1010,505),(105,855,1020,1086)],
4:[(845,245,1060,490),(150,864,1100,1086)],
5:[(783,245,1050,488),(95,883,1050,1086)],
6:[(780,255,1050,485),(95,878,1100,1086)],
7:[(775,162,1080,412),(35,893,1175,1086),(0,150,470,390)],
9:[(590,225,1020,500),(0,815,1025,1086)]
}
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean_one(source,number):
    source=Image.open(source).convert("RGB")
    if source.size!=(1448,1086):raise ValueError("STORY_IMAGE_GEOMETRY_CHANGED")
    array=np.array(source)
    if number in LOGOS:
        mask=np.zeros((1086,1448),dtype=np.uint8)
        for left,top,right,bottom in LOGOS[number]:
            cv2.rectangle(mask,(left,top),(right,bottom),255,-1)
        source=Image.fromarray(cv2.cvtColor(cv2.inpaint(cv2.cvtColor(array,cv2.COLOR_RGB2BGR),mask,2,cv2.INPAINT_TELEA),cv2.COLOR_BGR2RGB))
    if number in WORDS:
        current=np.array(source)
        mask=np.zeros((1086,1448),dtype=np.uint8)
        for left,top,right,bottom in WORDS[number]:
            cv2.rectangle(mask,(left,top),(right,bottom),255,-1)
        blurry=cv2.GaussianBlur(current,(0,0),35)
        alpha=cv2.GaussianBlur(mask,(0,0),15).astype(np.float32)/255
        source=Image.fromarray((current*(1-alpha[:,:,None])+blurry*alpha[:,:,None]).astype("uint8"))
    if number in (2,8):
        draw=ImageDraw.Draw(source)
        for left,top,right,bottom in LOGOS[number]:
            draw.rounded_rectangle((left,top,right,bottom),radius=10,fill=(245,244,242))
    if number==9:
        draw=ImageDraw.Draw(source)
        draw.polygon([(527,400),(704,429),(685,790),(507,766)],fill=(250,250,248))
    bg=ImageOps.fit(source,(720,1280),Image.Resampling.LANCZOS)
    bg=bg.filter(ImageFilter.GaussianBlur(46))
    actor=source.crop(CROPS[number])
    actor.thumbnail((720,760 if number in (2,8) else 1100),Image.Resampling.LANCZOS)
    bg.paste(actor,((720-actor.width)//2,(1280-actor.height)//2))
    return bg

def main(root="output/wan9-text-masked-candidate"):
    refs=verify_reference_images()
    base=Path(root);base.mkdir(parents=True,exist_ok=True)
    entries=[]
    for i,reference in enumerate(refs,1):
        scene=f"scene{i:02d}"
        path=base/(scene+".png")
        clean_one(reference["path"],i).save(path,optimize=True)
        if not 50000<=path.stat().st_size<=8000000:
            raise ValueError("CANDIDATE_PNG_INVALID_SIZE_"+scene)
        if Image.open(path).size!=(720,1280):
            raise ValueError("CANDIDATE_PNG_INVALID_GEOMETRY_"+scene)
        entries.append({
            "scene_id":scene,"path":path.as_posix(),
            "visual_sha256":sha(path),
            "source_reference_sha256":reference["sha256"],
            "status":"TEXT_MASKED_CANDIDATE_NEEDS_VISUAL_QA",
            "expression_visual_qa_approved":False,
            "contains_no_baked_brand_guaranteed":False,
            "character_identity_match_approved":False,
        })
    cols=3
    contact=Image.new("RGB",(750,1290),"white")
    for i in range(1,10):
        thumbnail=Image.open(base/f"scene{i:02d}.png").resize((240,420))
        contact.paste(thumbnail,(((i-1)%cols)*250,((i-1)//cols)*430))
    contact.save(base/"contact-sheet.jpg",quality=88)
    data={"version":1,"num_scenes":9,"new_gpu_authorized":False,
          "scenes":entries,"gpu_pods_created":0,"status":"VISUAL_REVIEW_REQUIRED"}
    (base/"plate-manifest.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print("WAN9_TEXT_MASKED_CANDIDATE_IMAGES=9")
    print("WAN9_GPU_READY=false")
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="output/wan9-text-masked-candidate")
    a=p.parse_args()
    main(a.out)
