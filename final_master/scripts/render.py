"""Approved-asset-only preview compositor; does not synthesize speech or publish."""
import argparse,json,zipfile,tempfile,subprocess,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

PREFIX="TrustFolio_Washing_Machine_Master_Kit/assets/video/"
STORY=["01_story_girl","02_friends_enter","03_blue_boy_dialogue","04_yellow_boy_dialogue","05_purple_girl_machine","06_green_boy_intro"]
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def cmd(*args):
    subprocess.run(["ffmpeg","-y","-loglevel","error",*map(str,args)],check=True)
def extract(z,name,folder):
    matches=[n for n in z.namelist() if n.endswith("/assets/video/"+name+".mp4")]
    if len(matches)!=1:raise ValueError("Missing approved video "+name)
    dst=folder/(name+".mp4")
    with z.open(matches[0]) as src,dst.open("wb") as output:shutil.copyfileobj(src,output)
    return dst
def overlay(p,photo,out):
    im=Image.new("RGBA",(720,1280))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((365,270,710,1130),radius=20,fill=(255,247,224,240))
    font=ImageFont.truetype(FONT,23)
    d.text((390,295),"TOP #"+str(p["rank"]),fill="#723913",font=font)
    with Image.open(photo) as source:
        pic=source.convert("RGB");pic.thumbnail((300,320))
        im.paste(pic,(385+(300-pic.width)//2,370+(320-pic.height)//2))
    d.text((390,725),p["title"][:26],fill="#3d2820",font=font)
    d.text((390,770),f"₹{p['price_inr']:,.0f}",fill="#783b16",font=font)
    for i,s in enumerate(p["specifications"]):
        d.text((390,823+i*64),(s["key"]+": "+s["value"])[:25],fill="#4a3423",font=font)
    im.save(out)
def normalize(src,dst):
    cmd("-i",src,"-vf","scale=720:1280:flags=lanczos,fps=24","-ar","48000","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac",dst)
def main():
    p=argparse.ArgumentParser()
    for x in ("kit","campaign","photos","output"):p.add_argument("--"+x,required=True)
    a=p.parse_args()
    q=json.loads(Path(a.campaign).read_text())
    if q.get("status")!="DATA_READY_NOT_PUBLISHABLE" or q.get("publish_allowed") is not False or len(q.get("products",[]))!=5:raise ValueError("Strict live contract not satisfied")
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp,zipfile.ZipFile(a.kit) as z:
        t=Path(tmp);segments=[]
        for i,name in enumerate(STORY):
            out=t/("part%02d.mp4"%i);normalize(extract(z,name,t),out);segments.append(out)
        green=extract(z,"08_green_boy_clean_master",t)
        for p in q["products"]:
            rank=p["rank"];photo=Path(a.photos)/("rank_%02d.png"%rank)
            if not photo.is_file():raise ValueError("Approved product photo missing rank "+str(rank))
            layer=t/("panel%d.png"%rank);overlay(p,photo,layer)
            out=t/("rank%d.mp4"%rank)
            cmd("-i",green,"-loop","1","-i",layer,"-f","lavfi","-t","10","-i","anullsrc=channel_layout=stereo:sample_rate=48000",
                "-filter_complex","[0:v]scale=720:1280:flags=lanczos,fps=24[b];[b][1:v]overlay=0:0:shortest=1[v]",
                "-map","[v]","-map","2:a","-t","10","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-c:a","aac",out)
            segments.append(out)
        end=t/"cta.mp4";normalize(extract(z,"09_premium_girl_cta",t),end);segments.append(end)
        playlist=t/"concat.txt";playlist.write_text("".join("file '"+str(s)+"'\n" for s in segments))
        cmd("-f","concat","-safe","0","-i",playlist,"-c","copy",a.output)
    Path(a.output+".qa.json").write_text(json.dumps({"visual_preview_created":True,"narration_approved":False,"lip_sync_approved":False,"qr_verified":False,"publish_allowed":False},indent=2))
    print("VISUAL_PREVIEW_ONLY_NOT_PUBLISHABLE")
if __name__=="__main__":main()
