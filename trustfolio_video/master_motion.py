"""Private 8-second cinematic MASTER REFERENCE motion-blocking proof.

Inputs are user-approved illustrated artwork and PREVIOUSLY generated offline
Hindi demo audio. Not an accurate original SKU/retailer ad, not skeletal 3D,
not human-reviewed Hindi and never publishable. This intentionally replaces
the rejected low-poly scene style with the actual high-fidelity reference art.

Usage: python -m trustfolio_video.master_motion \
 --master-illustration /path/trustfolio_s_tropical_washing_machine_parade.png \
 --brand-reference /path/trustfolio_s_top_5_washing_machines.png \
 --speech-demo /path/trustfolio_previous_hindi_demo.mp4 \
 --output out/master-style-8sec-private.mp4
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

SHA_MASTER="bcc90bf85a9c2f4fee8b57b0c02b78e5b80f4c8a184b5d528ccb21a1ca934e0c"
SHA_BRAND="c5ce062090f34ab414a125d91c3ad39ff81f37a8ad4e629726e5ced0f3458ba1"
W,H=600,1066
PURPLE=(49,7,141,250)
NAVY=(17,10,72,255)
GOLD=(255,220,42,255)
WHITE=(255,255,255,255)
CHAR_POLYGONS={
 "fifth":[(15,485),(84,490),(276,516),(304,584),(299,690),(274,750),(212,795),(57,759),(2,730),(0,606)],
 "fourth":[(680,543),(701,508),(750,551),(826,548),(922,530),(941,598),(933,726),(887,771),(719,787),(658,748),(644,608)],
 "third":[(1,789),(187,755),(247,811),(242,992),(221,1071),(170,1115),(53,1098),(2,1050)],
 "second":[(682,756),(744,713),(883,718),(935,764),(937,991),(886,1068),(720,1074),(644,1024),(664,860)],
 "hero":[(292,685),(383,676),(475,690),(609,709),(660,785),(651,978),(677,1055),(647,1195),(577,1310),(470,1297),(385,1240),(315,1231),(261,1150),(260,950),(235,852),(245,778)],
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def input_lock(master,brand):
    if sha(master)!=SHA_MASTER or sha(brand)!=SHA_BRAND:
        raise ValueError("User-approved MASTER illustrations changed: do not silently substitute another visual style.")
    if Image.open(master).size!=(941,1672) or Image.open(brand).size!=(1024,1536):
        raise ValueError("Unexpected approved reference geometry")

def face_layers(art):
    actors={}
    sx=W/art.width;sy=H/art.height
    for key,points in CHAR_POLYGONS.items():
        xs=[x for x,y in points];ys=[y for x,y in points]
        bbox=(max(0,min(xs)-6),max(0,min(ys)-6),min(art.width,max(xs)+6),min(art.height,max(ys)+6))
        sprite=art.crop(bbox).convert("RGBA")
        mask=Image.new("L",sprite.size,0)
        draw=ImageDraw.Draw(mask)
        draw.polygon([(x-bbox[0],y-bbox[1]) for x,y in points],fill=255)
        sprite.putalpha(mask.filter(ImageFilter.GaussianBlur(2.5)))
        dims=(max(1,int(sprite.width*sx)),max(1,int(sprite.height*sy)))
        actors[key]=(sprite.resize(dims,Image.Resampling.LANCZOS),int(bbox[0]*sx),int(bbox[1]*sy))
    assert len(actors)==5
    return actors

def text_center(draw,y,text,font,color,width=W):
    bounds=draw.textbbox((0,0),text,font=font)
    draw.text(((width-(bounds[2]-bounds[0]))/2,y),text,font=font,fill=color)

def clean_baked_illustrative_prices(scene,font_roman,font_hindi):
    # The supplied design art contains fabricated illustrative SKU, rank and
    # ₹35,000 headline text. REPLACE the on-scene claim with educational comedy.
    out=scene.copy()
    d=ImageDraw.Draw(out)
    d.rounded_rectangle((174,104,755,402),radius=45,fill=PURPLE,
                        outline=GOLD,width=11)
    text_center(d,148,"LAUNDRY ADVENTURE",font_roman,GOLD,width=928)
    text_center(d,251,"5 fun appliance friends",font_roman,WHITE,width=928)
    for box,caption in [
        ((275,531,551,717),"चलो साथ में!"),
        ((683,417,932,565),"मस्ती शुरू!"),
        ((686,1045,930,1194),"सबकी पसंद अलग!")
    ]:
        d.ellipse(box,fill=WHITE,outline=PURPLE,width=8)
        tw=d.textbbox((0,0),caption,font=font_hindi)
        d.text(((box[0]+box[2]-tw[2]+tw[0])/2,(box[1]+box[3]-tw[3]+tw[1])/2),
               caption,font=font_hindi,fill=NAVY)
    return out

def camera(stage,t):
    if t<2.55: zoom=1.38+.035*math.sin(t*.7);cx=.35+.021*t;cy=.44+.025*t
    elif t<5.25: zoom=1.39+.015*math.sin(t*.72);cx=.68-.019*(t-2.55);cy=.49+.015*(t-2.55)
    else: zoom=1.12-.078*min(1,(t-5.25)/2.75);cx=.5;cy=.5
    ww,hh=int(W*zoom),int(H*zoom)
    scaled=stage.resize((ww,hh),Image.Resampling.BICUBIC)
    x=max(0,min(ww-W,int(cx*ww-W/2)))
    y=max(0,min(hh-H,int(cy*hh-H/2)))
    return scaled.crop((x,y,x+W,y+H))

def animate_layer(source,actors,t):
    scene=source.copy()
    for key,(sprite,x,y) in actors.items():
        phase_offset={"fifth":.3,"fourth":1.1,"third":2.2,"second":3.7,"hero":4.5}[key]
        p=t*6.1+phase_offset
        hop=-int((10 if key=="hero" else 7)*max(0,math.sin(p)))
        dx=int(5*math.sin(t*1.8+phase_offset))
        img=sprite.rotate(2.7*math.sin(t*2+phase_offset),Image.Resampling.BICUBIC,expand=True)
        scene.alpha_composite(img,(
            int(x+dx-(img.width-sprite.width)//2),
            int(y+hop-(img.height-sprite.height)//2)))
    return scene

def overlay(stage,brand,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    dr=ImageDraw.Draw(layer)
    dr.rectangle((0,0,W,153),fill=PURPLE)
    logo=brand.crop((235,0,800,87)).convert("RGBA")
    logo.thumbnail((410,93))
    layer.alpha_composite(logo,((W-logo.width)//2,10))
    dr.rounded_rectangle((20,98,W-20,155),radius=15,fill=GOLD)
    roman=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",26)
    small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",14)
    hindi=ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Bold.ttf",23)
    text_center(dr,101,"TOP 5 WASHING MACHINES",roman,NAVY)
    text_center(dr,130,"MASTER VISUAL • PRIVATE QA",small,NAVY)
    dr.rectangle((0,H-196,W,H),fill=NAVY)
    dr.rectangle((0,H-196,W,H-190),fill=GOLD)
    dialogue=("अरे! कपड़ों का पहाड़! दोस्तों, तैयार?" if t<3.9
              else "पाँचवाँ दोस्त आया! बबल पार्टी!" if t<7.6
              else "ट्रस्टफ़ोलियो पर तुलना करो!")
    text_center(dr,H-182,dialogue,hindi,WHITE)
    dr.rounded_rectangle((46,H-113,W-46,H-58),radius=24,fill=GOLD)
    text_center(dr,H-103,"COMPARE • TRUSTFOLIO.IN",roman,NAVY)
    text_center(dr,H-42,"DEMO • PRICES AND RANKS UNVERIFIED",small,WHITE)
    dst=Image.alpha_composite(stage,layer)
    d=ImageDraw.Draw(dst,"RGBA")
    for i in range(18):
        x=(i*127+22*math.sin(t*1.35+i))%W
        y=180+(i*171-t*29)%(H-420)
        r=2+(i%3)*2
        d.ellipse((x-r,y-r,x+r,y+r),fill=(190,245,255,15),outline=(255,255,255,130),width=2)
    for cut in (2.55,5.25):
        distance=abs(t-cut)
        if distance<.13:
            dst=Image.alpha_composite(dst,Image.new("RGBA",(W,H),(255,225,174,int((1-distance/.13)*110))))
    return dst.convert("RGB")

def run(master,brand,voice,output):
    input_lock(master,brand)
    if not Path(voice).is_file(): raise ValueError("Missing existing licensed/private voice demo")
    art=Image.open(master).convert("RGBA")
    typography=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",29)
    hindi=ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Bold.ttf",25)
    source=clean_baked_illustrative_prices(art,typography,hindi)
    raw=source.resize((W,H),Image.Resampling.LANCZOS)
    actors=face_layers(art)
    bg=Image.open(brand).convert("RGBA")
    def frame(t):
        return overlay(camera(animate_layer(raw,actors,t),t),bg,t)
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(".silent.mp4")
    cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-f","rawvideo",
         "-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate","12",
         "-i","pipe:0","-vf","fps=24,scale=1080:1920:flags=lanczos",
         "-c:v","libx264","-preset","ultrafast","-crf","21",
         "-pix_fmt","yuv420p","-an","-movflags","+faststart","-y",str(tmp)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for i in range(96):
            p.stdin.write(np.asarray(frame((i+.5)/12)).tobytes())
        p.stdin.close()
        e=p.stderr.read();rc=p.wait(timeout=75)
        if rc:raise RuntimeError("FFmpeg rendering failed: "+str(e[-1200:]))
    except BaseException:
        p.kill();raise
    subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
                   "-i",str(tmp),"-i",str(voice),"-map","0:v:0","-map","1:a:0",
                   "-c:v","copy","-c:a","aac","-b:a","160k","-t","8",
                   "-movflags","+faststart","-y",str(out)],check=True,timeout=75)
    j=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams",
                                         "-show_format","-of","json",str(out)]))
    v=next(s for s in j["streams"] if s["codec_type"]=="video")
    a=next(s for s in j["streams"] if s["codec_type"]=="audio")
    assert v["codec_name"]=="h264" and (v["width"],v["height"])==(1080,1920)
    assert a["codec_name"]=="aac" and 7.8<float(j["format"]["duration"])<=8.1
    return {"status":"PRIVATE_MOTION_QA_ONLY","sha256":sha(out),
       "duration":float(j["format"]["duration"]),"video_codec":"h264",
       "audio_codec":"aac","framesize":[1080,1920],
       "separate_sprite_characters":5,"camera_shots":3,
       "actual_skeletal_3d_rigs":False,"commercial_retailer_rights_approved":False,
       "rank_and_price_live_verified":False,"hindi_human_naturalness_approved":False,
       "production_approved":False,"publishing_enabled":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--master-illustration",required=True)
    p.add_argument("--brand-reference",required=True)
    p.add_argument("--speech-demo",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=run(a.master_illustration,a.brand_reference,a.speech_demo,a.output)
    target=Path(a.output).with_suffix(".qa.json")
    target.write_text(json.dumps(report,indent=2)+"\n")
    print("PRIVATE_APPROVED_MASTER_MOTION_RENDER_CREATED=true")
    print("PUBLISHING_ENABLED=false")

if __name__=="__main__":main()
