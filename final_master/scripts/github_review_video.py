"""Create GitHub-rendered 90s review from original kit + 5 generated WAVs.

No new graphics or claims of photoreal photo replacement/lip sync. Original
video images stay byte-originated from approved kit, original audio retained
except rank narration mix. Reject all publish attempts.
"""
import argparse,json,zipfile,tempfile,subprocess,shutil,wave
from pathlib import Path
STORY=["01_story_girl","02_friends_enter","03_blue_boy_dialogue","04_yellow_boy_dialogue","05_purple_girl_machine","06_green_boy_intro"]
def ff(*args):subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*map(str,args)],check=True)
def probe(path):
 s=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True)
 return float(s.strip())
def extract(z,name,d):
 hits=[x for x in z.namelist() if x.endswith("/assets/video/"+name+".mp4")]
 if len(hits)!=1:raise ValueError("Missing unique original clip "+name)
 out=d/(name+".mp4")
 with z.open(hits[0]) as f,out.open("wb") as w:shutil.copyfileobj(f,w)
 return out
def render(kit,audios,output):
 audios=Path(audios);out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
 products=json.loads((audios/"products.json").read_text())
 if products.get("budget_inr")!=35000 or len(products.get("products",[]))!=5:raise ValueError("Wrong campaign")
 if [x["rank"] for x in products["products"]]!=[1,2,3,4,5]:raise ValueError("Rank mismatch")
 with tempfile.TemporaryDirectory() as td,zipfile.ZipFile(kit) as z:
  tmp=Path(td);parts=[]
  for i,n in enumerate(STORY):
   source=extract(z,n,tmp);part=tmp/f"part_{i:02d}.mp4"
   ff("-i",source,"-vf","scale=720:1280,fps=24","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-ar","48000",part)
   parts.append(part)
  green=extract(z,"08_green_boy_clean_master",tmp)
  for idx,p in enumerate(products["products"],1):
   meta=json.loads((audios/f"rank_{idx:02d}.json").read_text())
   voice=audios/f"rank_{idx:02d}.wav"
   if meta["rank"]!=idx or meta["product_id"]!=p["product_id"] or not voice.exists():raise ValueError("Product-voice mismatch")
   if not .3<probe(voice)<=10.0:raise ValueError("Voice exceeds original slot")
   part=tmp/f"rank_{idx:02d}.mp4"
   # Copy original animated visual design, mix narration over a lowered original soundtrack.
   ff("-stream_loop","-1","-i",green,"-i",voice,
       "-filter_complex","[0:v]scale=720:1280,fps=24[v];[0:a]volume=0.20,aresample=48000[bed];[1:a]aresample=48000,apad,atrim=duration=10[voice];[bed][voice]amix=inputs=2:duration=first:normalize=0[a]",
       "-map","[v]","-map","[a]","-t","10","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-ar","48000",part)
   parts.append(part)
  source=extract(z,"09_premium_girl_cta",tmp);part=tmp/"end.mp4"
  ff("-i",source,"-vf","scale=720:1280,fps=24","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-ar","48000",part)
  parts.append(part)
  playlist=tmp/"join.txt";playlist.write_text("".join("file '"+str(x.resolve())+"'\n" for x in parts))
  ff("-f","concat","-safe","0","-i",playlist,"-c","copy",out)
 duration=probe(out)
 report={"budget_inr":35000,"duration_seconds":duration,"five_voice_tracks":True,
         "original_visual_clips":True,"exact_dynamic_photos":False,
         "dynamic_text_replacement":False,"lip_sync_verified":False,
         "publish_allowed":False,"video_type":"GITHUB_RENDERED_VOICE_INTEGRATION_REVIEW"}
 Path(str(out)+".qa.json").write_text(json.dumps(report,indent=2))
 if not 80<=duration<=95:raise ValueError("Video timeline unexpected: "+str(duration))
 print("GITHUB_REVIEW_MP4_CREATED_NOT_PUBLISHABLE",duration)
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--kit",required=True);p.add_argument("--audios",required=True);p.add_argument("--output",required=True)
 a=p.parse_args();render(a.kit,a.audios,a.output)
