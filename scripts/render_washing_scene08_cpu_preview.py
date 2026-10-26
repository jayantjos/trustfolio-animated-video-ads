#!/usr/bin/env python3
"""CPU-only Stage 8 website-parity *visual QA*, never a live-priced publishing render.

The approved 40s master has three visible podiums. Ranks 1-3 appear first,
then 4-5 on the same wing podiums. Photos are real image inputs, not AI shapes.
Website-listed prices are never advertised as current marketplace live prices.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from trustfolio_flow.live import amount,campaign,sha

EXPECTED_SHA256="2d58880dc27c04c245ff95a10b53ba009538badd04f314062275149c9b5bb48c"
W,H,FPS,N=720,1280,24,96
STANDS={1:(360,667,350),2:(141,920,258),3:(577,925,258),
        4:(141,920,258),5:(577,925,258)}

def verify(master,doc,photos,allow_candidates=False):
    if hashlib.sha256(Path(master).read_bytes()).hexdigest()!=EXPECTED_SHA256:
        raise ValueError("Original master SHA256 mismatch")
    if (doc.get("source")!="trustfolio_website_display" or doc.get("publishable") is not False
            or doc.get("pricing_verification")!="WEBSITE_LISTED_ONLY"):
        raise ValueError("Preview only; site display source receipt required")
    p=doc.get("products")
    if not isinstance(p,list) or len(p)!=5: raise ValueError("Exactly 5 source products required")
    spec=campaign(doc["category"],doc["budget_inr"],doc["mode"],doc.get("brand",""))
    if sha({"spec":spec,"products":p})!=doc.get("snapshot_sha256"):
        raise ValueError("Tampered source receipt")
    owners={};seen=set();conflicts=[]
    for rank,row in enumerate(p,1):
        if (row.get("rank")!=rank or row.get("id") in seen
                or amount(row.get("price_inr"))>doc["budget_inr"]):
            raise ValueError("Invalid source ranks / duplicate ID / budget")
        seen.add(row["id"])
        url=row.get("image_url")
        if url in owners and owners[url]["brand"].casefold()!=row["brand"].casefold():
            conflicts.append([owners[url]["rank"],rank])
        owners[url]=row
        if not (Path(photos)/("rank_%02d.png"%rank)).is_file():
            raise ValueError("Missing product photo rank %d"%rank)
    if conflicts and not allow_candidates:
        raise ValueError("CROSS_BRAND_PHOTO_BLOCKED: model-specific source correction QA required")
    return conflicts

def cutout(path):
    origin=np.asarray(Image.open(path).convert("RGBA"))
    rgb,old_alpha=origin[:,:,:3],origin[:,:,3]
    paper=((rgb.min(axis=2)>247)&(old_alpha>0)).astype("uint8")
    _,labels,_,_=cv2.connectedComponentsWithStats(paper,8)
    border=set(np.unique(np.r_[labels[0,:],labels[-1,:],labels[:,0],labels[:,-1]]))
    border.discard(0)
    a=np.where(np.isin(labels,list(border)),0,old_alpha).astype("uint8")
    a=cv2.GaussianBlur(a,(3,3),.5)
    y,x=np.where(a>30)
    if len(x)==0: raise ValueError("Missing appliance silhouette")
    return Image.fromarray(np.dstack([rgb,a]),"RGBA").crop(
        (max(0,x.min()-3),max(0,y.min()-3),min(rgb.shape[1],x.max()+4),min(rgb.shape[0],y.max()+4)))

def ease(t):
    t=max(0,min(1,t))
    return t*t*(3-2*t)

def center(draw,x,y,value,font,fill):
    box=draw.textbbox((0,0),value,font=font)
    draw.text((int(x-(box[2]-box[0])/2),y),value,font=font,fill=fill)

def show_product(canvas,photo,rank,opacity):
    if opacity<=0: return
    x,bottom,_=STANDS[rank]
    a=photo.copy()
    a.putalpha(a.getchannel("A").point(lambda v:int(v*opacity)))
    px=int(x-a.width/2);py=bottom-a.height
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    dr=ImageDraw.Draw(layer)
    rx=max(26,int(a.width*.48))
    dr.ellipse((x-rx,bottom-13,x+rx,bottom+13),
               fill=(6,2,25,int(105*opacity)))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(11)))
    canvas.alpha_composite(a,(px,py))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for a in ("master","receipt","photos","output"):p.add_argument("--"+a,required=True)
    p.add_argument("--allow-model-photo-candidates",action="store_true",
       help="Unreleased QA ONLY, use model-specific photo candidates if website source is wrong")
    v=p.parse_args()
    master,output=Path(v.master),Path(v.output)
    doc=json.loads(Path(v.receipt).read_text(encoding="utf-8"))
    conflicts=verify(master,doc,v.photos,v.allow_model_photo_candidates)
    output.parent.mkdir(parents=True,exist_ok=True)
    photos={}
    for rank in range(1,6):
        a=cutout(Path(v.photos)/("rank_%02d.png"%rank))
        mh=STANDS[rank][2]
        nw=int(mh*a.width/a.height)
        nw=min(nw,235 if rank==1 else 194)
        nh=int(nw*a.height/a.width)
        if nh>mh:nh=mh;nw=int(mh*a.width/a.height)
        photos[rank]=a.resize((nw,nh),Image.Resampling.LANCZOS)
    bold=ImageFont.truetype("/usr/share/fonts/truetype/lato/Lato-Bold.ttf",28)
    pricefont=ImageFont.truetype("/usr/share/fonts/truetype/lato/Lato-Bold.ttf",26)
    regular=ImageFont.truetype("/usr/share/fonts/truetype/lato/Lato-Regular.ttf",16)
    headline=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",39)
    topfont=ImageFont.truetype("/usr/share/fonts/truetype/lato/Lato-Regular.ttf",22)
    silent=output.with_name(output.stem+"_silent.mp4")
    process=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}",
        "-framerate",str(FPS),"-i","pipe:0","-an","-c:v","libx264",
        "-preset","veryfast","-crf","18","-pix_fmt","yuv420p",str(silent)],
        stdin=subprocess.PIPE)
    cap=cv2.VideoCapture(str(master))
    cap.set(cv2.CAP_PROP_POS_MSEC,28000)
    try:
        for i in range(N):
            ok,frame=cap.read()
            if not ok:raise ValueError("Missing original source stage frame")
            t=i/FPS
            base=Image.fromarray(cv2.cvtColor(cv2.resize(frame,(W,H),
                interpolation=cv2.INTER_CUBIC),cv2.COLOR_BGR2RGB)).convert("RGBA")
            dr=ImageDraw.Draw(base)
            center(dr,360,98,"TRUSTFOLIO",topfont,(245,234,248,240))
            center(dr,360,136,"BEST FIVE",headline,(252,221,163,245))
            center(dr,360,193,
                   "WASHING MACHINES  •  UNDER ₹"+format(doc["budget_inr"],","),
                   regular,(240,232,255,240))
            vis={1:ease((t-.15)/.48),
                 2:ease((t-.38)/.42)*(1-ease((t-1.81)/.42)),
                 3:ease((t-.62)/.42)*(1-ease((t-1.81)/.42)),
                 4:ease((t-2.31)/.45),
                 5:ease((t-2.47)/.45)}
            for rank in (1,2,3,4,5):
                alpha=vis[rank]
                show_product(base,photos[rank],rank,alpha)
                if rank==1:show=ease((t-.6)/.35)
                elif rank in (2,3):show=alpha*ease((t-({2:.73,3:.97}[rank]))/.33)
                else:show=alpha*ease((t-({4:2.57,5:2.73}[rank]))/.36)
                if show:
                    x=STANDS[rank][0]
                    y=834 if rank==1 else 948
                    dr=ImageDraw.Draw(base)
                    brand=doc["products"][rank-1]["brand"].upper()
                    price=int(float(doc["products"][rank-1]["price_inr"]))
                    center(dr,x,y,"#%d  %s"%(rank,brand),bold,(252,224,174,int(255*show)))
                    center(dr,x,y+41,"₹"+format(price,","),pricefont,
                           (252,250,240,int(255*show)))
            dr=ImageDraw.Draw(base)
            center(dr,360,1220,"WEBSITE-LISTED PRICES  •  VISUAL QA ONLY",
                regular,(250,239,226,210))
            process.stdin.write(np.asarray(base.convert("RGB")).tobytes())
    finally:
        cap.release()
        if process.stdin:process.stdin.close()
    if process.wait():raise ValueError("FFmpeg failed to encode stage preview")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
       "-i",str(silent),"-ss","28","-t","4","-i",str(master),
       "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
       "-b:a","160k","-shortest",str(output)],check=True)
    output.with_suffix(".qa.json").write_text(json.dumps({
       "publishable":False,"visual_qa_only":True,"live_price_verified":False,
       "category":doc["category"],"budget_inr":doc["budget_inr"],
       "snapshot_sha256":doc["snapshot_sha256"],
       "website_cross_brand_source_image_conflicts":conflicts,
       "external_model_candidates_unapproved":v.allow_model_photo_candidates,
       "source_master_sha256":EXPECTED_SHA256,
       "no_social_publish":True},indent=2)+"\n")
    print("SCENE_08_VISUAL_PREVIEW_CREATED="+str(output))
    print("LIVE_PRICE_VERIFIED=NO; PUBLISHING_ALLOWED=NO")
if __name__=="__main__":main()
