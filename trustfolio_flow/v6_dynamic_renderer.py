#!/usr/bin/env python3
"""Re-render Premium V6 at 54 s using ONE current, five-ID TrustFolio receipt.

Fixed 40s original animated story supplies moving footage; V6 approved
reference supplies unchanged final cartoon CTA + 54s original ambience.
Regenerates EVERY scene containing price/product/specification text.
No poster PNG, product ranking or price is hardcoded in this renderer.
No Meta publishing. All five accurate photo model approvals required.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from trustfolio_flow.v6_live_campaign import validate_receipt,check_photo_approvals

W,H,FPS=720,1280,24
GOLD=(255,224,167,255);CREAM=(252,244,229,255)
PURPLE=(66,43,112,255);PALE=(230,217,251,255)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SERIF="/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"

def f(sz,bold=True,serif=False):
    return ImageFont.truetype(SERIF if serif else BOLD if bold else FONT,sz)

def text(im,xy,value,size,color,anchor="lt",bold=True):
    ImageDraw.Draw(im).text(xy,str(value),font=f(size,bold),fill=color,anchor=anchor,
                            stroke_width=1,stroke_fill=(20,8,40,110))

def fit(text_value,max_width,size=30,max_lines=2):
    probe=ImageDraw.Draw(Image.new("RGB",(10,10)))
    words=str(text_value).split();rows=[];current=""
    for word in words:
        newer=(current+" "+word).strip()
        if current and probe.textbbox((0,0),newer,font=f(size))[2]>max_width:
            rows.append(current);current=word
        else:current=newer
    if current:rows.append(current)
    if len(rows)>max_lines:
        rows=rows[:max_lines]
        while probe.textbbox((0,0),rows[-1]+"…",font=f(size))[2]>max_width and rows[-1]:
            rows[-1]=rows[-1][:-1]
        rows[-1]+="…"
    return rows

def overlay():
    return Image.new("RGBA",(W,H),(0,0,0,0))

def price(p):return "₹"+format(int(round(float(p["price_inr"]))),",")

def glass_glow(canvas,x,y,r=95,color=(181,142,235),alpha=42):
    layer=overlay();ImageDraw.Draw(layer).ellipse((x-r,y-r,x+r,y+r),fill=(*color,alpha))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(r//2)))

def note(canvas,label,y=1230):
    text(canvas,(W//2,y),label,15,PALE,"mt",False)

def spec_rows(im,product,x=490,y=270,spacing=112,show_four=True):
    from trustfolio_flow.v6_live_campaign import source_specs
    specs=source_specs(product)
    if not show_four:specs=specs[:2]
    for index,row in enumerate(specs):
        ty=y+index*spacing
        label=row["label"].upper()
        val=row["value"].upper()
        text(im,(x,ty),label,17,CREAM,"mt",False)
        if len(val)>13:
            words=fit(val,205,size=25,max_lines=2)
            for i,word in enumerate(words):text(im,(x,ty+29+i*28),word,25,PURPLE,"mt")
        else:text(im,(x,ty+33),val,32,PURPLE,"mt")
        ImageDraw.Draw(im).line((x-98,ty+79,x+98,ty+79),fill=(117,83,176,135),width=2)

def photo_png(photo_file,expected_sha):
    p=Path(photo_file)
    if sha256(p.read_bytes()).hexdigest()!=expected_sha:
        raise ValueError("Photo bytes do not match approved review manifest")
    img=Image.open(p).convert("RGBA")
    if min(img.size)<200:raise ValueError("Image too small for premium visual")
    if img.getchannel("A").getextrema()==(255,255):
        # Opaque rectangular backgrounds create non-premium false composites.
        raise ValueError("Image must be model-reviewed and cut out with transparent alpha")
    box=img.getchannel("A").getbbox()
    if not box:raise ValueError("Empty appliance alpha mask")
    return img.crop(box)

def product_sprite(im,p,photo,center_x,bottom_y,height=310,width=240):
    obj=photo.copy();obj.thumbnail((width,height),Image.Resampling.LANCZOS)
    layer=overlay();x=int(center_x-obj.width/2);y=int(bottom_y-obj.height)
    shadow=overlay()
    ImageDraw.Draw(shadow).ellipse((x,bottom_y-10,x+obj.width,bottom_y+14),
                                     fill=(12,5,38,100))
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
    layer.alpha_composite(obj,(x,y))
    im.alpha_composite(layer)

def info_overlay(p,rank,x,y,wide=False):
    canvas=overlay()
    text(canvas,(x,y),f"#{rank}  {p['brand'].upper()}",24 if not wide else 28,GOLD,"mt")
    text(canvas,(x,y+40),price(p),30 if not wide else 38,CREAM,"mt")
    return canvas

def make_assets(receipt,photos,workdir,preview_watermark=False):
    workdir=Path(workdir);workdir.mkdir(parents=True,exist_ok=True)
    prods=receipt["products"]
    pngs=[]
    for p,review in zip(prods,photos["products"]):
        candidate=workdir/"photos"/("rank_%02d.png"%p["rank"])
        pngs.append(photo_png(candidate,review["image_sha256"]))
    assets={}
    a=overlay()
    text(a,(495,64),"THE SMARTER WASH",25,PURPLE,"mt")
    first=prods[0];spec_rows(a,first,x=525,y=160,spacing=106,show_four=False)
    assets["spec_a"]=a
    a=overlay()
    text(a,(515,95),"FOUR REAL FEATURES",26,PURPLE,"mt")
    spec_rows(a,first,x=520,y=198,spacing=127,show_four=True)
    assets["spec_b"]=a
    a=overlay()
    text(a,(535,87),"TRUSTFOLIO",25,PURPLE,"mt")
    text(a,(533,137),"BUDGET",22,PURPLE,"mt",False)
    text(a,(535,174),"₹"+format(receipt["budget_inr"],","),46,PURPLE,"mt")
    text(a,(535,230),"TOP FIVE PICKS",23,PURPLE,"mt")
    assets["budget"]=a
    for wave,name in (([1,2,3],"top3"),([1,4,5],"top5")):
        a=overlay()
        text(a,(360,88),"THE BEST FIVE",42,GOLD,"mt")
        text(a,(360,149),"WASHING MACHINES   ·   UNDER ₹"+format(receipt["budget_inr"],","),20,PALE,"mt")
        layouts={1:(360,712,375,290),2:(139,959,258,194),3:(574,959,258,194),
                 4:(139,959,258,194),5:(574,959,258,194)}
        for rank in wave:
            p=prods[rank-1];x,b,h,w=layouts[rank]
            glass_glow(a,x,b-185,115,(155,116,236),48)
            product_sprite(a,p,pngs[rank-1],x,b,h,w)
            a.alpha_composite(info_overlay(p,rank,x,760 if rank==1 else 1013))
        text(a,(360,1188),"FIVE VERIFIED-RANK PRODUCTS · ₹"+format(receipt["budget_inr"],","),18,PALE,"mt")
        assets[name]=a
    a=overlay();p,q=prods[:2]
    text(a,(360,88),"THE SMART COMPARISON",35,GOLD,"mt")
    text(a,(360,153),"TOP TWO  ·  SAME BUDGET",21,PALE,"mt")
    for idx,(p,x) in enumerate(((p,165),(q,550))):
        glass_glow(a,x,580,140,(128,92,226),31)
        product_sprite(a,p,pngs[idx],x,747,315,225)
        text(a,(x,818),f"#{idx+1} {p['brand'].upper()}",26,GOLD,"mt")
        text(a,(x,860),price(p),30,CREAM,"mt")
        from trustfolio_flow.v6_live_campaign import source_specs
        for n,row in enumerate(source_specs(p)[:2]):
            text(a,(x,938+n*74),row["label"].upper(),16,PALE,"mt",False)
            text(a,(x,961+n*74),row["value"].upper()[:19],22,CREAM,"mt")
    assets["compare"]=a
    base=extract_stage_base=workdir/"stage_original.png"
    # The architectural background is a genuine frame from the approved original.
    # FFmpeg extracts one stage frame without using model/price pixels from V6 reference.
    return assets,pngs,base

def get_stage(master,path):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    "-ss","29.1","-i",str(master),"-frames:v","1",
                    "-vf",f"scale={W}:{H}",str(path)],check=True)

def make_spotlights(receipt,cutouts,stage_image,workdir):
    stage=Image.open(stage_image).convert("RGBA")
    prods=receipt["products"];out=[]
    from trustfolio_flow.v6_live_campaign import source_specs
    for idx,p in enumerate(prods,1):
        im=stage.copy()
        tint=Image.new("RGBA",(W,H),(24,12,68,35));im.alpha_composite(tint)
        glass_glow(im,360,545,245,(158,112,251),48)
        text(im,(360,75),"T R U S T F O L I O",20,GOLD,"mt")
        text(im,(360,129),f"PICK {idx:02d} / 05",42,CREAM,"mt")
        ImageDraw.Draw(im).line((175,190,545,190),fill=(244,213,164,210),width=2)
        title_lines=fit(p["title"],625,size=27,max_lines=2)
        for n,line in enumerate(title_lines):
            text(im,(360,215+n*41),line,27,CREAM,"mt")
        product_sprite(im,p,cutouts[idx-1],360,775,400,315)
        text(im,(360,819),price(p),49,GOLD,"mt")
        text(im,(360,887),p["platform"].upper(),20,PALE,"mt")
        for n,s in enumerate(source_specs(p)):
            y=951+n*68
            text(im,(50,y),s["label"].upper(),20,PALE,"lt",False)
            label=s["value"].upper()
            for x,val in enumerate(fit(label,305,size=25,max_lines=1)):
                text(im,(672,y-1),val,25,CREAM,"rt")
            ImageDraw.Draw(im).line((50,y+49,670,y+49),fill=(204,183,239,94),width=1)
        filepath=Path(workdir)/f"product_spotlight_{idx:02d}.png"
        im.convert("RGB").save(filepath)
        out.append(filepath)
    return out

def sh(cmd):
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)

def encode(receipt,photo_manifest,master,approved_v6,photo_folder,output,*,now=None):
    validate_receipt(receipt,now=now)
    check_photo_approvals(receipt,photo_manifest)
    if photo_manifest.get("source_receipt_sha256") != receipt["snapshot_sha256"]:
        raise ValueError("Photo review is for another campaign snapshot")
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    master=Path(master);approved_v6=Path(approved_v6)
    if not master.is_file() or not approved_v6.is_file():
        raise FileNotFoundError("Both original 40s cartoon video and approved V6 artistic reference required")
    with tempfile.TemporaryDirectory(prefix="tfv6_render_") as td:
        tmp=Path(td)
        (tmp/"photos").mkdir()
        for i in range(1,6):
            import shutil
            shutil.copyfile(Path(photo_folder)/f"rank_{i:02d}.png",tmp/"photos"/f"rank_{i:02d}.png")
        overlays,cutouts,stage_image=make_assets(receipt,photo_manifest,tmp)
        get_stage(master,stage_image)
        keys=["spec_a","spec_b","budget","top3","top5","compare"]
        for k in keys:overlays[k].save(tmp/(k+".png"))
        paths=[tmp/(k+".png") for k in keys]
        forty=tmp/"forty.mp4"
        inputs=["-i",str(master)]
        for p in paths:inputs.extend(["-loop","1","-framerate","24","-i",str(p)])
        times=[(12,16),(16,20),(24,28),(28,30),(30,32),(32,36)]
        graph="[0:v]scale=720:1280,format=rgba[v0];"
        prev="v0"
        for i,(start,end) in enumerate(times,1):
            nxt=f"v{i}"
            graph+=f"[{prev}][{i}:v]overlay=enable='between(t,{start},{end})':shortest=1[{nxt}];"
            prev=nxt
        graph+=f"[{prev}]format=yuv420p[vout]"
        sh(["ffmpeg","-hide_banner","-loglevel","error","-y",*inputs,"-filter_complex",graph,
            "-map","[vout]","-an","-r","24","-t","40","-c:v","libx264",
            "-threads","4","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",str(forty)])
        stills=make_spotlights(receipt,cutouts,stage_image,tmp)
        inputs=[]
        for path in stills:
            inputs+=["-loop","1","-framerate","24","-t","2.8","-i",str(path)]
        graph=";".join(f"[{i}:v]scale=720:1280,format=yuv420p,"
              "fade=t=in:st=0:d=0.12,fade=t=out:st=2.66:d=0.12,"
              f"setpts=PTS-STARTPTS[v{i}]" for i in range(5))
        graph+=";"+"".join(f"[v{i}]" for i in range(5))+"concat=n=5:v=1:a=0[v]"
        focus=tmp/"five_showcase.mp4"
        sh(["ffmpeg","-hide_banner","-loglevel","error","-y",*inputs,"-filter_complex",graph,
            "-map","[v]","-an","-c:v","libx264","-threads","4","-preset","veryfast",
            "-crf","21","-r","24","-pix_fmt","yuv420p",str(focus)])
        graph=("[0:v]trim=start=0:end=32,setpts=PTS-STARTPTS[a];"
             "[1:v]setpts=PTS-STARTPTS[b];"
             "[0:v]trim=start=32:end=36,setpts=PTS-STARTPTS[c];"
             "[2:v]trim=start=50:end=54,setpts=PTS-STARTPTS[d];"
             "[a][b][c][d]concat=n=4:v=1:a=0[v]")
        sh(["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-i",str(forty),"-i",str(focus),"-i",str(approved_v6),
            "-filter_complex",graph,"-map","[v]","-map","2:a:0",
            "-c:v","libx264","-threads","4","-preset","veryfast","-crf","21",
            "-pix_fmt","yuv420p","-r","24","-c:a","copy",
            "-movflags","+faststart","-t","54",str(output)])
    audit={
        "state":"VISUAL_RENDER_DONE_NOT_PUBLISH_APPROVED",
        "source_snapshot_sha256":receipt["snapshot_sha256"],
        "rendered_product_ids":[p["id"] for p in receipt["products"]],
        "rendered_prices_inr":[p["price_inr"] for p in receipt["products"]],
        "photo_evidence_sha256":[p["image_sha256"] for p in photo_manifest["products"]],
        "voiceover_status":"NOT_ADDED_TO_FIVE_PRODUCT_SHOWCASE",
        "post_allowed":False,
        "video_sha256":sha256(output.read_bytes()).hexdigest()}
    output.with_suffix(".qa.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DYNAMIC_V6_54S_RENDERED="+str(output))
    print("PRODUCT_HINDI_VO_NOT_COMPLETE=YES; SOCIAL_POSTS=0")
    return audit

def main():
    p=argparse.ArgumentParser()
    for key in ("receipt","photo-qa","photo-dir","master","v6-reference","output"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    receipt=json.loads(Path(a.receipt).read_text(encoding="utf-8"))
    photos=json.loads(Path(a.photo_qa).read_text(encoding="utf-8"))
    encode(receipt,photos,a.master,a.v6_reference,a.photo_dir,a.output)

if __name__=="__main__":main()
