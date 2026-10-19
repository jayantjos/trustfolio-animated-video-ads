"""CPU-only genuine cartoon-character pilot renderer; historical DEMO only.

The product photo remains unaltered inside an independently moving 2D character
rig (limbs, eyes, expressions and partner reactions are separate render layers).
eSpeak voice output and original procedurally synthesized music/SFX are mixed
into a final AAC/H264 MP4. No external AI service or credentials.
"""
import argparse
from array import array
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.request import Request, urlopen
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .demo import APPROVED_IMAGE_HOSTS, approve_historical_demo
from .storyboard import validate_registry

W, H = 540, 960
FPS_DRAW = 12
AUDIO_RATE = 22050
FINAL_W, FINAL_H, FINAL_FPS = 1080, 1920, 24
PALETTES = {
    "washing-machines": ("bubble", (9, 71, 129), (40, 175, 208), (225, 250, 255)),
    "smart-phones": ("neon", (28, 12, 70), (119, 58, 219), (231, 210, 255)),
    "headphones-earbuds": ("beat", (48, 12, 78), (213, 52, 143), (255, 225, 249)),
}
DIALOGUE = {
    "washing-machines": [
        "Kapdon ki duniya mein paanch dost!",
        "Paanch bola: bubble party hai!",
        "Chaar bola: mere bina party?",
        "Teen bola: ghoomo, dosto!",
        "Do bola: main bhi race mein!",
        "Ek bola: TrustFolio ka top pick!",
        "Paanch dost, ek budget. TrustFolio!"
    ],
    "smart-phones": [
        "Neon Nagar mein phone ki meeting!",
        "Paanch bola: selfie ready?",
        "Chaar bola: group pose banao!",
        "Teen bola: notification aaya!",
        "Do bola: sabko smile chahiye!",
        "Ek bola: top rank, hello dosto!",
        "Phone squad dekho, TrustFolio par!"
    ],
    "headphones-earbuds": [
        "Beat Street pe paanch dost!",
        "Paanch bola: beat suno yaar!",
        "Chaar bola: volume, please!",
        "Teen bola: mere saath naacho!",
        "Do bola: arre DJ, beat badhao!",
        "Ek bola: rank one ki entry!",
        "Paanch picks compare karo, TrustFolio!"
    ],
}
BUDGET_LABELS = {"budget": "BUDGET FUN", "brand_budget": "BRAND SQUAD",
                 "comparison": "FRIENDLY COMPARISON"}

def font(size, bold=False):
    paths = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]
    for p in ([paths[0], paths[2]] if bold else [paths[1], paths[2]]):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise RuntimeError("Licensed system font not available")

def text_fit(d, text, max_width, size=21, minimum=11, bold=True):
    text = str(text).replace("\n", " ").strip()
    while size >= minimum:
        f = font(size, bold)
        if d.textbbox((0, 0), text, font=f)[2] <= max_width:
            return text, f
        size -= 1
    f = font(minimum, bold)
    while len(text) > 2 and d.textbbox((0, 0), text + "…", font=f)[2] > max_width:
        text = text[:-1]
    return text + "…", f

def center(d, text, y, color, size=21, max_width=460, bold=True):
    txt, f = text_fit(d, text, max_width, size, bold=bold)
    width = d.textbbox((0, 0), txt, font=f)[2]
    d.text(((W-width)/2, y), txt, fill=color, font=f)

def _image_for(product, directory):
    from urllib.parse import urlsplit
    url = product["main_image"]
    host = urlsplit(url).hostname
    if host not in APPROVED_IMAGE_HOSTS:
        raise ValueError("Image host not allowlisted")
    asset = Path(directory) / (product["id"] + ".png")
    provenance = {"product_id": product["id"], "image_url": url,
                  "download_ok": False, "image_sha256": None}
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 TrustFolioAnimatedDemo/0.1",
                                    "Accept": "image/png,image/jpeg,image/webp"})
        with urlopen(req, timeout=12) as response:
            mime = response.headers.get("Content-Type", "").lower()
            if not mime.startswith("image/"):
                raise ValueError("Not a product image")
            raw = response.read(3_000_001)
            if len(raw) > 3_000_000:
                raise ValueError("Product image too large")
        with Image.open(BytesIO(raw)) as incoming:
            incoming.load()
            if incoming.width < 50 or incoming.height < 50 or incoming.width * incoming.height > 18_000_000:
                raise ValueError("Invalid image dimensions")
            img = ImageOps.contain(incoming.convert("RGB"), (235, 245))
        img.save(asset)
        provenance.update(download_ok=True, image_sha256=hashlib.sha256(raw).hexdigest())
        return img, provenance
    except (OSError, TimeoutError, ValueError, Exception) as ex:
        # Fallback shape is conspicuously labeled; no imaginary product render.
        provenance["failure_type"] = type(ex).__name__
        return None, provenance

def _background(world, tick, seed):
    _, dark, bright, light = PALETTES.get(world, ("generic",(19,30,78),(71,102,221),(242,246,255)))
    im = Image.new("RGB", (W, H), dark)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y/H
        d.line((0,y,W,y),fill=tuple(int(dark[i]*(1-t*.5)+bright[i]*t*.5) for i in range(3)))
    if world == "washing-machines":
        for i in range(24):
            rad = 6 + (i*7)%28
            x = (31+i*71+int(8*math.sin(tick*2+i)))%W
            y = (H+105-i*91-int(tick*24*(1+i%3)))%(H+105)
            d.ellipse((x-rad,y-rad,x+rad,y+rad),outline=(152,234,254),width=3)
        d.rounded_rectangle((32,240,508,755),radius=35,outline=(109,205,241),width=3)
    elif world == "smart-phones":
        for i in range(9):
            x=24+i*68
            high=130+(i*53)%180
            d.rounded_rectangle((x,740-high,x+45,740),radius=6,fill=(51,33,112),outline=(136,96,233),width=3)
            for j in range(3):
                d.rectangle((x+10,740-high+20+j*37,x+20,740-high+32+j*37),fill=(255,191,88))
        for i in range(17):
            x=(i*53+17)%W
            y=(i*83+int(tick*25))%H
            d.ellipse((x,y,x+3,y+3),fill=(205,165,255))
    elif world == "headphones-earbuds":
        for i in range(18):
            x=14+i*31
            height=35+abs(math.sin(tick*3+i*.61))*110
            d.rounded_rectangle((x,747-height,x+18,747),radius=7,
                                fill=(130+int(85*abs(math.sin(tick+i))),67,174))
        for i in range(8):
            x=(i*71+int(tick*18))%W
            y=170+(i*73)%400
            d.ellipse((x-4,y-4,x+4,y+4),fill=(251,191,255))
    else:
        for i in range(15):
            x=(i*61+int(tick*15))%W
            y=(i*47)%H
            d.ellipse((x,y,x+8,y+8),fill=bright)
    return im

def _character(im, d, product, photo, x, y, scale, phase, featured=False):
    """Product image is a rigid/photo layer; animated arms, legs, pupils, mouth outside it."""
    bob=math.sin(phase*5)* (11 if featured else 6)
    sway=math.sin(phase*3)* (10 if featured else 5)
    cx=int(x+sway); cy=int(y+bob)
    cw=int(186*scale); ch=int(218*scale)
    sx=int(5*scale)
    arm_color=(255,209,112)
    # independently moving limbs
    angle=math.sin(phase*8)
    d.line((cx-cw//2+5,cy+ch//3,cx-cw//2-26*scale,cy+ch//5-angle*31*scale),
           fill=arm_color,width=max(3,int(8*scale)))
    d.line((cx+cw//2-5,cy+ch//3,cx+cw//2+28*scale,cy+ch//5+angle*31*scale),
           fill=arm_color,width=max(3,int(8*scale)))
    d.line((cx-25*scale,cy+ch//2-4,cx-28*scale+angle*12*scale,cy+ch//2+29*scale),
           fill=arm_color,width=max(3,int(8*scale)))
    d.line((cx+25*scale,cy+ch//2-4,cx+28*scale-angle*12*scale,cy+ch//2+29*scale),
           fill=arm_color,width=max(3,int(8*scale)))
    l=cx-cw//2;t=cy-ch//2
    d.rounded_rectangle((l-4,t-4,l+cw+4,t+ch+4),radius=max(8,int(19*scale)),
                        fill=(243,247,255),outline=(255,211,67),width=max(2,int(4*scale)))
    if photo is not None:
        thumb=ImageOps.contain(photo,(max(5,cw-12),max(5,int(ch*.68))))
        im.paste(thumb,(cx-thumb.width//2,t+int(18*scale)))
    else:
        d.rounded_rectangle((l+12,t+18*scale,l+cw-12,t+ch*.66),radius=12,fill=(223,224,232))
        # Product silhouette intentionally unlabeled as a real product image
        center_text, f=text_fit(d,"IMAGE UNAVAILABLE",cw-25,10,minimum=8)
        d.text((l+11,t+ch*.42),center_text,font=f,fill=(48,54,76))
    eye_y=cy+ch//4
    eye_sep=18*scale
    radius=max(2,int(5*scale))
    for eye_x in (cx-eye_sep,cx+eye_sep):
        d.ellipse((eye_x-radius,eye_y-radius,eye_x+radius,eye_y+radius),fill=(26,29,65))
    mouth_depth=(9 if int(phase*10)%2 else 3)*scale
    d.arc((cx-10*scale,eye_y+9*scale,cx+10*scale,eye_y+9*scale+mouth_depth),
          start=0,end=180,fill=(191,46,89),width=max(2,int(3*scale)))
    badge_r=17 if featured else 11
    bx=cx-cw//2+2;by=cy-ch//2
    d.ellipse((bx-badge_r,by-badge_r,bx+badge_r,by+badge_r),fill=(255,209,55))
    ttxt,f=text_fit(d,str(product["rank"]),badge_r*1.5,18 if featured else 12)
    d.text((bx-badge_r*.35,by-badge_r*.65),ttxt,font=f,fill=(17,33,70))
    return cx,cy

def render_frame(approved, photos, scene_idx, seconds, total, world):
    products=approved["products"]
    frame=_background(world, seconds, approved["source_sha256"])
    d=ImageDraw.Draw(frame)
    d.rounded_rectangle((24,30,516,83),radius=22,fill=(11,18,57),outline=(255,209,55),width=2)
    center(d,"TrustFolio  •  CARTOON PICKS",45,(255,252,245),25)
    d.rounded_rectangle((75,94,465,121),radius=8,fill=(255,223,76))
    center(d,"DEMO - NOT FOR PUBLICATION",98,(16,28,67),17)
    spec=approved["campaign"]
    _, _, _, pale=PALETTES.get(world, ("generic",(19,30,78),(71,102,221),(242,246,255)))
    center(d, BUDGET_LABELS[spec["mode"]],147,(255,228,86),28)
    center(d, spec["category"].replace("-"," ").title(),185,pale,29)
    center(d,("Brand: "+spec["brand"]+"  |  " if spec["brand"] else "")+
              "Budget: Rs "+format(spec["budget"],","),223,(255,255,255),19)
    script=DIALOGUE.get(spec["category"],[spec["category"]+" ke paanch dost!"]+
                      ["Rank "+str(n)+" entry!" for n in range(5,0,-1)]+["TrustFolio par compare karo!"])
    phase=seconds
    if scene_idx==0:
        center(d,"FIVE FRIENDS. ONE BUDGET!",278,(255,231,100),22)
        for i,p in enumerate(reversed(products)):
            x=78+i*97
            _character(frame,d,p,photos.get(p["id"]),x,480,.48,phase+i*.55)
        center(d,"Meet the five real ranked picks!",647,pale,19)
    elif 1<=scene_idx<=5:
        rank=6-scene_idx
        p=products[rank-1]
        _character(frame,d,p,photos.get(p["id"]),W//2,475,1.23,phase,True)
        center(d, "#"+str(rank)+"  "+p["title"],642,(255,255,255),19)
        center(d,"Recorded Rs "+format(int(p["price_inr"]),",")+"  •  "+p["platform"].title(),
               674,(255,231,100),18)
        # Partner reacts from other character position; data order remains unchanged.
        partner=products[max(0,rank-2)] if rank>1 else products[1]
        _character(frame,d,partner,photos.get(partner["id"]),438,688,.32,phase+.8)
        d.rounded_rectangle((48,716,490,771),radius=18,fill=(250,248,255))
        center(d,script[scene_idx],733,(40,29,102),18,430)
    else:
        center(d,"All five friends together!",280,(255,226,80),22)
        for i,p in enumerate(reversed(products)):
            _character(frame,d,p,photos.get(p["id"]),80+i*95,470,.46,phase+i*.9)
        center(d,"Rank #1 stays #1 — real website order",652,(255,255,255),17)
        center(d,script[-1],704,pale,20)
    d.rounded_rectangle((29,817,511,897),radius=25,fill=(255,218,59))
    center(d,"COMPARE NOW ON TRUSTFOLIO",834,(17,29,67),22)
    center(d,"www.trustfolio.in",863,(17,29,67),17)
    center(d,"Recorded prices • Verify latest price before buying",907,(255,255,255),12)
    center(d,"HISTORICAL DEMO • NEVER AUTO-PUBLISH",937,(255,229,90),13)
    return frame

def _run(cmd, *, timeout=240):
    result=subprocess.run(cmd,timeout=timeout,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError("Media subprocess failed: "+Path(cmd[0]).name+
                           " exit="+str(result.returncode)+" "+result.stderr[-500:])
    return result

def _voice_track(script, boundaries, temp, voice_binary):
    """Build original (not cloned) voice and original synthesized sounds."""
    n=int((boundaries[-1]+.2)*AUDIO_RATE)
    track=np.zeros(n,dtype=np.float64)
    music=np.zeros(n,dtype=np.float64)
    xs=np.arange(n,dtype=np.float64)/AUDIO_RATE
    # Original royalty-free procedural three-note melody, gentle behind speech.
    notes=[220.,261.63,329.63,392.]
    for beat_idx,t in enumerate(np.arange(0,boundaries[-1],.4)):
        beg=int(t*AUDIO_RATE);dur=int(.30*AUDIO_RATE)
        size=min(dur,n-beg)
        if size<=0:break
        tt=np.arange(size)/AUDIO_RATE
        env=np.minimum(1,tt/.025)*np.exp(-tt*7)
        freq=notes[beat_idx%len(notes)]
        music[beg:beg+size]+=0.085*np.sin(2*np.pi*freq*tt)*env
        if beat_idx%4==0:
            music[beg:beg+size]+=0.11*np.sin(2*np.pi*90*tt)*np.exp(-tt*20)
    speech_total=0
    voices=[]
    for i,line in enumerate(script):
        outfile=Path(temp)/("voice_"+str(i)+".wav")
        variant="en+f3" if i%2==0 else "en+m3"
        _run([voice_binary,"-v",variant,"-s","200","-p",str(55 if i%2 else 70),
              "-a","175","-w",str(outfile),line],timeout=45)
        with wave.open(str(outfile),"rb") as reader:
            rate=reader.getframerate()
            channels=reader.getnchannels()
            width=reader.getsampwidth()
            raw=reader.readframes(reader.getnframes())
        if channels!=1 or width!=2:
            raise ValueError("Unexpected voice WAV encoding")
        data=np.frombuffer(raw,dtype="<i2").astype(np.float64)/32768
        if rate!=AUDIO_RATE:
            samples=int(len(data)*AUDIO_RATE/rate)
            data=np.interp(np.linspace(0,len(data)-1,samples),
                           np.arange(len(data)),data)
        start=int((boundaries[i]+.15)*AUDIO_RATE)
        allowed=int((boundaries[i+1]-boundaries[i]-.24)*AUDIO_RATE)
        clipped=data[:max(0,allowed)]
        count=min(len(clipped),n-start)
        if count:
            track[start:start+count]+=clipped[:count]*.77
            speech_total+=count
        voices.append({"scene":i,"voice":variant,"text":line,"audio_samples_used":count})
    # Rank reveal cartoon pop (procedurally synthesized, no external sample).
    for t in boundaries[1:-1]:
        beg=int(t*AUDIO_RATE);size=min(int(.18*AUDIO_RATE),n-beg)
        if size<=0:continue
        tt=np.arange(size)/AUDIO_RATE
        music[beg:beg+size]+=.18*np.sin(2*np.pi*(700-500*tt)*tt)*np.exp(-tt*20)
    full=np.clip(track+music,-.93,.93)
    dest=Path(temp)/"soundtrack.wav"
    with wave.open(str(dest),"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(AUDIO_RATE)
        wav.writeframes((full*32767).astype("<i2").tobytes())
    return dest,{"voices":voices,"speech_duration_seconds":speech_total/AUDIO_RATE,
                 "music_source":"original procedural synthesis (no third-party soundtrack)",
                 "tts_engine":Path(voice_binary).name,"tts_license_review":"eSpeak GPL; demo only; no production voice quality approval",
                 "peak_dbfs":round(20*math.log10(max(float(np.max(np.abs(full))),1e-9)),2)}

def generate_pilot(snapshot_path, registry_path, output, *, duration=15):
    if duration not in (15,20,30):
        raise ValueError("Unsupported pilot duration")
    approved=approve_historical_demo(json.loads(Path(snapshot_path).read_text(encoding="utf8")))
    registry=json.loads(Path(registry_path).read_text(encoding="utf8"))
    validate_registry(registry)
    spec=approved["campaign"]
    world=next((x for x in registry["categories"] if x.get("slug")==spec["category"] and x["enabled"]),None)
    if world is None:raise ValueError("Unregistered pilot category")
    voice=shutil.which("espeak-ng") or shutil.which("espeak")
    ffmpeg=shutil.which("ffmpeg");ffprobe=shutil.which("ffprobe")
    if not all([voice,ffmpeg,ffprobe]):
        raise RuntimeError("Offline eSpeak, ffmpeg and ffprobe required")
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    preview=output.with_suffix(".preview.png")
    with tempfile.TemporaryDirectory(prefix="tf_cartoon_demo_") as tmp:
        tmp=Path(tmp)
        photos={};provenance=[]
        for p in approved["products"]:
            img,record=_image_for(p,tmp)
            photos[p["id"]]=img
            provenance.append(record)
        # Intro 2 seconds, CTA 3; rank 5 to rank 1 fill remaining 5 slots.
        intro=2.0
        cta=3.0 if duration==15 else 4.0
        per=(duration-intro-cta)/5
        boundaries=[0.0,intro]+[intro+i*per for i in range(1,6)]+[float(duration)]
        assert len(boundaries)==8 and abs(boundaries[-2]-(duration-cta))<1e-5
        script=DIALOGUE.get(spec["category"],[world["hooks"][0]]+
                            world["dialogue"]+[world["cta"]])
        soundtrack,audio=_voice_track(script,boundaries,tmp,voice)
        silent=tmp/"silent.mp4"
        cmd=[ffmpeg,"-nostdin","-hide_banner","-loglevel","error",
             "-f","rawvideo","-pixel_format","rgb24","-video_size","540x960",
             "-framerate",str(FPS_DRAW),"-i","pipe:0",
             "-vf","scale=1080:1920:flags=bicubic,fps=24",
             "-an","-c:v","libx264","-preset","ultrafast","-crf","27",
             "-pix_fmt","yuv420p","-y",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            total_frames=duration*FPS_DRAW
            for frame_idx in range(total_frames):
                seconds=frame_idx/FPS_DRAW
                scene_idx=next(i for i in range(7) if boundaries[i]<=seconds<boundaries[i+1])
                scene=render_frame(approved,photos,scene_idx,seconds,duration,spec["category"])
                if frame_idx==int(4.5*FPS_DRAW):
                    scene.save(preview)
                proc.stdin.write(scene.tobytes())
            proc.stdin.close()
            err=proc.stderr.read()
            ret=proc.wait(timeout=180)
            if ret:raise RuntimeError("Video encoding failed: "+err.decode(errors="replace")[-500:])
        finally:
            if proc.poll() is None:proc.kill()
        _run([ffmpeg,"-nostdin","-hide_banner","-loglevel","error",
              "-i",str(silent),"-i",str(soundtrack),
              "-map","0:v:0","-map","1:a:0","-c:v","copy",
              "-c:a","aac","-b:a","128k","-t",str(duration),
              "-movflags","+faststart","-y",str(output)],timeout=90)
        probe=json.loads(_run([ffprobe,"-v","error","-show_streams","-show_format",
                               "-of","json",str(output)],timeout=40).stdout)
    streams=probe["streams"]
    videos=[x for x in streams if x["codec_type"]=="video"]
    audios=[x for x in streams if x["codec_type"]=="audio"]
    if len(videos)!=1 or len(audios)!=1:
        raise ValueError("Real video and audible audio required")
    v=videos[0];a=audios[0];actual=float(probe["format"]["duration"])
    if (v["codec_name"]!="h264" or v["width"]!=FINAL_W or v["height"]!=FINAL_H or
        a["codec_name"]!="aac" or not duration-.12<=actual<=duration+.4 or
        output.stat().st_size<80000 or audio["speech_duration_seconds"]<2):
        raise ValueError("MP4 technical/audio QA failed")
    report={
        "status":"HISTORICAL_DEMO_RENDERED_NOT_APPROVED_FOR_PUBLICATION",
        "publishing_enabled":False,"watermark":"DEMO - NOT FOR PUBLICATION",
        "source_observed_at":approved["source_observed_at"],
        "source_sha256":approved["source_sha256"],
        "campaign":spec,"world":world["world"],
        "ranked_product_ids":[p["id"] for p in approved["products"]],
        "recorded_prices":[p["price_inr"] for p in approved["products"]],
        "price_evidence":approved["price_evidence"],
        "image_provenance":provenance,
        "photos_downloaded":sum(p["download_ok"] for p in provenance),
        "video":output.name,"video_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
        "duration":actual,"resolution":[FINAL_W,FINAL_H],
        "fps":FINAL_FPS,"codec":v["codec_name"],"audio_codec":a["codec_name"],
        "visual_layers":["real-product-photo","moving-limbs","animated-faces",
                         "partner-reactions","scene-specific-background",
                         "rank-badges","subtitle","permanent-demo-watermarks"],
        "audio":audio,
        "limitations":["Historical retail prices are not live verified",
                       "Retailer product photos retained for internal QA only",
                       "Text TrustFolio wordmark is not independently verified official logo",
                       "Robotic offline voice is not approved as natural production Hinglish",
                       "No human visual/audio creative signoff yet"]
    }
    output.with_suffix(".qa.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("CARTOON_DEMO_MP4_CREATED="+str(output))
    print("CARTOON_DEMO_IMAGES_DOWNLOADED="+str(report["photos_downloaded"]))
    print("CARTOON_DEMO_PUBLISHING_ENABLED=false")
    print("CARTOON_DEMO_QA_SHA256="+report["video_sha256"])
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",required=True)
    p.add_argument("--registry",default="config/worlds.json")
    p.add_argument("--output",required=True)
    p.add_argument("--duration",type=int,choices=(15,20,30),default=15)
    args=p.parse_args()
    generate_pilot(args.snapshot,args.registry,args.output,duration=args.duration)

if __name__=="__main__":
    main()
