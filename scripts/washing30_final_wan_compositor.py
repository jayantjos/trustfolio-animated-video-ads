"""Final ONLY after nine genuine Wan motion receipts + independent Hindi/lipsync QA.

This compositor never generates fake moving characters: it accepts already
verified Wan MP4s, composites current live product facts and CTA in removable
layers, and synchronizes approved 30s Hindi audio. Publishing stays OFF.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps

from trustfolio_video.contract import Blocked
from .final_motion_gate import verify_final_motion_inputs
from scripts.washing30_compose_preview import photo

W,H=1080,1920
BLUE=(48,19,125,228);YELLOW=(255,225,33,245)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def font(sz,bold=False):
    return ImageFont.truetype(BOLD if bold else FONT,sz)

def write_lines(canvas,text,x,y,max_width,*,size=35,fill=(255,255,255),max_lines=2):
    d=ImageDraw.Draw(canvas)
    f=font(size,True);words=str(text).split();line="";lines=[]
    for word in words:
        trial=(line+" "+word).strip()
        if d.textbbox((0,0),trial,font=f)[2]>max_width and line:
            lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    if len(lines)>max_lines:
        lines=lines[:max_lines]
        while d.textbbox((0,0),lines[-1]+"…",font=f)[2]>max_width and lines[-1]:
            lines[-1]=lines[-1][:-1]
        lines[-1]+="…"
    for text_line in lines:
        d.text((x,y),text_line,font=f,fill=fill)
        y+=size+14
    return y

def badge(canvas,budget):
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((24,32,1056,165),radius=25,fill=BLUE)
    d.text((55,55),"Trust",font=font(66,True),fill="white")
    d.text((273,55),"Folio",font=font(66,True),fill=(255,225,15))
    d.text((760,73),"Under Rs "+format(budget,","),font=font(30,True),fill="white")

def overlay(scene,story,output):
    image=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(image)
    budget=story["validated_budget_inr"]
    badge(image,budget)
    # Lower third safe area, so cartoon eyes/acting remain visible above it.
    if scene["kind"]=="product":
        data=scene["dynamic"]
        d.rounded_rectangle((25,1310,1055,1875),radius=35,fill=(248,244,255,251))
        d.rounded_rectangle((43,1342,280,1418),radius=24,fill=YELLOW)
        d.text((79,1353),"RANK "+str(data["rank"]),font=font(35,True),fill=(35,19,96))
        image_rgb=photo(data["unaltered_photo_url"])
        small=ImageOps.contain(image_rgb,(314,330),Image.Resampling.LANCZOS)
        im=small.convert("RGBA")
        image.alpha_composite(im,(54+(314-im.width)//2,1470+(330-im.height)//2))
        write_lines(image,data["title"],396,1335,620,size=36,fill=(41,17,104),max_lines=3)
        d=ImageDraw.Draw(image)
        d.text((395,1550),"Rs {:,.0f}".format(data["price_inr"]),font=font(49,True),fill=(42,21,121))
        fact=data.get("verified_spec")
        if fact:
            write_lines(image,fact["label"]+": "+fact["value"],396,1642,615,size=29,fill=(65,47,108),max_lines=2)
        write_lines(image,data["price_label"],396,1762,615,size=23,fill=(83,66,112),max_lines=2)
    elif scene["kind"] in ("intro","ranking"):
        d.rounded_rectangle((25,1350,1055,1888),radius=30,fill=(250,246,255,247))
        write_lines(image,"Verified website Top 5",55,1380,950,size=42,fill=(55,22,135))
        ranked=sorted((s["dynamic"] for s in story["scenes"][2:7]),key=lambda x:x["rank"],reverse=True)
        for i,item in enumerate(ranked):
            yy=1455+i*80
            write_lines(image,"#"+str(item["rank"])+" "+item["title"],60,yy,745,size=25,fill=(45,25,114),max_lines=1)
            d.text((840,yy),"Rs {:,.0f}".format(float(item["price_inr"])),font=font(23,True),fill=(50,20,131))
    elif scene["kind"]=="cta":
        d.rounded_rectangle((28,1350,1052,1890),radius=32,fill=(242,230,255,250))
        write_lines(image,"Apne budget ki best washing machine compare karo!",58,1400,950,size=45,fill=(56,25,129),max_lines=3)
        d.rounded_rectangle((53,1650,1027,1765),radius=35,fill=(255,224,20,254))
        d.text((90,1683),"www.trustfolio.in",font=font(58,True),fill=(40,23,105))
        write_lines(image,"Live price may change. Check before buying.",70,1810,930,size=25,fill=(68,57,93))
    elif scene["kind"]=="hook":
        d.rounded_rectangle((38,1560,1040,1830),radius=35,fill=(251,241,255,246))
        write_lines(image,"Arre! Itne saare kapde! Ab kaun dhoyega?",78,1615,915,size=41,fill=(54,31,116),max_lines=3)
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    image.save(output)
    return Path(output)

def call(args,timeout):
    subprocess.run(args,check=True,timeout=timeout)

def probe(path):
    obj=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height","-of","json",str(path)],timeout=12))
    return obj

def compose(story_path,receipt_path,clips_dir,human_qa_path,voice_path,out_path):
    story=json.loads(Path(story_path).read_text())
    receipts=json.loads(Path(receipt_path).read_text())
    qa=json.loads(Path(human_qa_path).read_text())
    clips={f"scene{i:02d}":str(Path(clips_dir)/f"scene{i:02d}.motion.mp4") for i in range(1,10)}
    review=verify_final_motion_inputs(story,receipts,clips,qa)
    if review["status"]!="FINAL_RENDER_MEDIA_INPUTS_VERIFIED_PRIVATE_QA":
        raise Blocked("Nine verified Wan clips and independent Hindi/lipsync QA required: "+
            ",".join(review["missing_requirements"]))
    aud=Path(voice_path)
    if not aud.is_file() or not 29.7<=float(probe(aud)["format"]["duration"])<=30.3:
        raise Blocked("Approved exact 30-second Hindi audio required")
    d=Path(out_path);d.parent.mkdir(parents=True,exist_ok=True)
    segment_dir=d.parent/"segments";segment_dir.mkdir(parents=True,exist_ok=True)
    segments=[]
    for scene in story["scenes"]:
        sid=scene["scene"];overlay_png=overlay(scene,story,segment_dir/(sid+".overlay.png"))
        clip=clips[sid];dst=segment_dir/(sid+".overlay.mp4")
        call(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
             "-i",clip,"-loop","1","-framerate","24","-i",str(overlay_png),
             "-filter_complex","[0:v]scale=1080:1920:flags=lanczos,setsar=1[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p[out]",
             "-map","[out]","-an","-t",str(scene["seconds"]),
             "-r","24","-c:v","libx264","-preset","veryfast","-crf","23",
             "-pix_fmt","yuv420p",str(dst)],timeout=150)
        segments.append(dst)
    listing=segment_dir/"join.ffconcat"
    listing.write_text("ffconcat version 1.0\n"+"".join(
        "file '"+f.resolve().as_posix()+"'\n" for f in segments),encoding="utf-8")
    silent=segment_dir/"full30-no-voice.mp4"
    call(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
        "-safe","0","-f","concat","-i",str(listing),"-c:v","copy","-t","30",str(silent)],timeout=50)
    call(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
        "-i",str(silent),"-i",str(aud),"-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","160k","-t","30",
        "-movflags","+faststart",str(d)],timeout=60)
    info=probe(d)
    video=[x for x in info["streams"] if x.get("codec_type")=="video"]
    audio=[x for x in info["streams"] if x.get("codec_type")=="audio"]
    if len(video)!=1 or len(audio)!=1 or video[0].get("width")!=W or video[0].get("height")!=H or not 29.8<=float(info["format"]["duration"])<=30.2:
        raise Blocked("Final 30s portrait sound-video validation failed")
    report={"status":"WAN_9_SHOT_30_SECOND_PRIVATE_QA_COMPOSED",
            "video_sha256":hashlib.sha256(d.read_bytes()).hexdigest(),
            "scenes":9,"duration":float(info["format"]["duration"]),
            "resolution":[W,H],"audio_codec":audio[0].get("codec_name"),
            "publishing_enabled":False,"published":False,
            "live_snapshot_observed_at":story["data_observed_at"]}
    (d.parent/"final-private-qa.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--story",required=True);p.add_argument("--receipts",required=True)
    p.add_argument("--clips-dir",required=True);p.add_argument("--human-qa",required=True)
    p.add_argument("--hindi-audio",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    print(json.dumps(compose(a.story,a.receipts,a.clips_dir,a.human_qa,a.hindi_audio,a.output),indent=2))
