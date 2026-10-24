"""CPU-only nine-scene visual compositor. DRAFT, not a Wan2.2 animation.

Reference PNGs with stale hardcoded brands/prices may NOT be used directly for
ranked scenes. All text, prices, photos and ranks here come from validated data.
"""
import hashlib
import io
import json
from pathlib import Path
import textwrap
from urllib.parse import urlsplit
from urllib.request import Request,build_opener

from PIL import Image,ImageDraw,ImageFilter,ImageFont,ImageOps,ImageEnhance

from trustfolio_video.contract import Blocked,NoRedirect
from scripts.stage_washing30_s3 import validate_stage

SIZE=(1080,1920)
PURPLE=(42,14,112)
YELLOW=(255,220,24)
WHITE=(255,255,255)
ALLOWED={"m.media-amazon.com","images-na.ssl-images-amazon.com",
         "rukminim2.flixcart.com","rukminim1.flixcart.com","media.tatacroma.com"}
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def font(size,bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG,size)

def draw_lines(d,text,pos,max_width,f,fill=WHITE,line_gap=12,max_lines=3):
    words=str(text).split()
    lines=[];current=""
    for word in words:
        attempt=(current+" "+word).strip()
        if d.textbbox((0,0),attempt,font=f)[2]>max_width and current:
            lines.append(current);current=word
        else:current=attempt
    if current:lines.append(current)
    if len(lines)>max_lines:
        lines=lines[:max_lines]
        while d.textbbox((0,0),lines[-1]+"...",font=f)[2]>max_width and lines[-1]:
            lines[-1]=lines[-1][:-1]
        lines[-1]+="..."
    y=pos[1]
    for line in lines:
        d.text((pos[0],y),line,font=f,fill=fill)
        y+=f.size+line_gap
    return y

def centered(d,text,y,f,color=WHITE):
    x=(SIZE[0]-d.textbbox((0,0),text,font=f)[2])//2
    d.text((x,y),text,font=f,fill=color)

def backdrop(ref):
    # Strong blur and an opaque purple veil make historical sample words unreadable.
    art=Image.open(ref).convert("RGB")
    art=ImageOps.fit(art,SIZE,method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(105))
    tint=Image.new("RGB",SIZE,PURPLE)
    return Image.blend(art,tint,0.92)

def panel(d,xy,fill=WHITE,outline=None,r=35,width=3):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=width if outline else 1)

def header(d,subtitle):
    d.rounded_rectangle((40,50,1040,173),radius=34,fill=(59,21,169))
    d.text((77,72),"Trust",font=font(68,True),fill=WHITE)
    d.text((273,72),"Folio",font=font(68,True),fill=YELLOW)
    draw_lines(d,subtitle,(65,207),955,font(43,True),max_lines=2)

def bottom(d):
    panel(d,(40,1772,1040,1886),(250,212,24),r=28)
    centered(d,"Compare at www.trustfolio.in",1800,font(38,True),color=(30,15,98))
    d.text((54,1900-55),"STORYBOARD PREVIEW - NOT FOR PUBLICATION",
           font=font(21,True),fill=(245,228,244))

def photo(url):
    parsed=urlsplit(str(url))
    if parsed.scheme!="https" or parsed.hostname not in ALLOWED or parsed.port not in (None,443):
        raise Blocked("Unapproved product photo host")
    req=Request(url,headers={"User-Agent":"TrustFolioStoryboardQA/1.0","Accept":"image/*"})
    opener=build_opener(NoRedirect()).open
    with opener(req,timeout=20) as res:
        ctype=res.headers.get("Content-Type","")
        if not ctype.startswith("image/"):raise Blocked("Product photo is not image")
        data=res.read(10*1024*1024+1)
    if not 1000<=len(data)<=10*1024*1024:raise Blocked("Product photo missing or too large")
    im=Image.open(io.BytesIO(data))
    if im.width*im.height>20_000_000:raise Blocked("Oversized decompressed product photo")
    im.load()
    if im.format not in ("JPEG","PNG","WEBP"):raise Blocked("Unsupported product photo format")
    return im.convert("RGB")

def render_one(scene,story,photos):
    idx=int(scene["scene"][-2:])
    frame=backdrop(scene["reference_path"])
    d=ImageDraw.Draw(frame)
    budget=story["validated_budget_inr"]
    subtitle="Best Washing Machines under Rs {:,}".format(budget)
    header(d,subtitle)
    if idx==1:
        # Hook contains fixed, approved dialogue only: no prices or brands.
        im=Image.open(scene["reference_path"]).convert("RGB")
        contained=ImageOps.contain(im,(1000,1080),Image.Resampling.LANCZOS)
        panel(d,(29,345,1051,350+contained.height+35),fill=WHITE,r=32)
        frame.paste(contained,((SIZE[0]-contained.width)//2,361))
        d=ImageDraw.Draw(frame)
        panel(d,(55,1503,1025,1730),fill=(247,240,255),r=30)
        draw_lines(d,"Arre! Itne saare kapde! Ab kaun dhoyega?",
                  (86,1552),912,font(46,True),(35,21,90),max_lines=3)
    elif idx==2:
        centered(d,"Meet the verified website Top 5",365,font(43,True),YELLOW)
        ranks=[5,4,3,2,1]
        for i,r in enumerate(ranks):
            p=photos[r];item=next(x for x in story["scenes"][2:7] if x["dynamic"]["rank"]==r)["dynamic"]
            y=460+i*246
            panel(d,(62,y,1018,y+213),(255,255,255),r=30)
            d.ellipse((83,y+56,157,y+132),fill=(63,25,155))
            d.text((106,y+66),str(r),font=font(40,True),fill=YELLOW)
            icon=ImageOps.contain(p,(230,182),Image.Resampling.LANCZOS)
            frame.paste(icon,(195+(230-icon.width)//2,y+14+(182-icon.height)//2))
            d=ImageDraw.Draw(frame)
            draw_lines(d,item["title"],(465,y+37),510,font(30,True),(31,20,99),max_lines=3)
        d=ImageDraw.Draw(frame)
    elif 3<=idx<=7:
        item=scene["dynamic"];p=photos[item["rank"]]
        panel(d,(55,342,1025,1285),fill=(255,255,255),r=42)
        icon=ImageOps.contain(p,(910,825),Image.Resampling.LANCZOS)
        frame.paste(icon,((1080-icon.width)//2,400+(825-icon.height)//2))
        d=ImageDraw.Draw(frame)
        panel(d,(70,1310,1010,1435),fill=(255,221,28),r=26)
        d.text((103,1343),"RANK #"+str(item["rank"]),font=font(47,True),fill=(32,13,88))
        if item["rank"]==1:
            d.polygon([(840,1368),(871,1325),(897,1348),(925,1325),(957,1368)],fill=(190,100,0))
        panel(d,(70,1460,1010,1749),fill=(244,236,255),r=27)
        end=draw_lines(d,item["title"],(100,1490),870,font(39,True),(31,19,94),max_lines=2)
        d.text((100,end+7),"Rs {:,.0f}".format(float(item["price_inr"])),
                font=font(51,True),fill=(45,19,118))
        label=item.get("verified_spec")
        if label:
            draw_lines(d,str(label["label"])+": "+str(label["value"]),
                (100,end+90),850,font(27,True),(40,34,96),max_lines=1)
        draw_lines(d,item["price_label"],(100,end+143),850,font(24),(65,53,104),max_lines=1)
    elif idx==8:
        centered(d,"Top 5 - verified rank order",340,font(44,True),YELLOW)
        for i,r in enumerate((5,4,3,2,1)):
            item=next(x for x in story["scenes"][2:7] if x["dynamic"]["rank"]==r)["dynamic"]
            y=450+i*256
            panel(d,(55,y,1025,y+220),(255,233,175) if r==1 else WHITE,r=26)
            d.text((90,y+72),"#"+str(r),font=font(72,True),fill=(62,21,146))
            pic=photos[r];ic=ImageOps.contain(pic,(220,180))
            frame.paste(ic,(240+(220-ic.width)//2,y+16+(180-ic.height)//2))
            d=ImageDraw.Draw(frame)
            e=draw_lines(d,item["title"],(492,y+26),482,font(32,True),(40,21,106),max_lines=2)
            d.text((492,e+6),"Rs {:,.0f}".format(float(item["price_inr"])),
                   font=font(38,True),fill=(35,20,92))
    else:
        # Crop only the smiling face from approved last reference; the old
        # illustrative phone/price cards and sample CTA never enter output.
        base=Image.open(scene["reference_path"]).convert("RGB")
        w,h=base.size
        crop=base.crop((0,int(.10*h),int(.35*w),int(.74*h)))
        crop=ImageOps.fit(crop,(780,905),method=Image.Resampling.LANCZOS)
        panel(d,(138,330,942,1263),fill=WHITE,r=34)
        frame.paste(crop,(150,344))
        d=ImageDraw.Draw(frame)
        panel(d,(67,1294,1013,1740),fill=(252,245,255),r=33)
        draw_lines(d,"Your budget. Your best choice.",
                   (107,1342),850,font(57,True),(47,20,122),max_lines=2)
        draw_lines(d,"Compare current top 5 at TrustFolio!",
                   (107,1498),850,font(43,True),(47,20,122),max_lines=2)
        d.text((115,1634),"www.trustfolio.in",font=font(47,True),fill=(63,31,141))
    bottom(d)
    return frame

def render(story,output):
    validate_stage(story)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    photos={}
    for scene in story["scenes"][2:7]:
        rank=scene["dynamic"]["rank"]
        photos[rank]=photo(scene["dynamic"]["unaltered_photo_url"])
    paths=[]
    for scene in story["scenes"]:
        im=render_one(scene,story,photos)
        name=scene["scene"]+".png"
        im.save(output/name,optimize=True)
        paths.append(output/name)
    (output/"manifest.json").write_text(json.dumps({
        "campaign_id":story["campaign_id"],"frames":[str(p) for p in paths],
        "duration":30,"size":SIZE,"video_type":"STATIC_STORYBOARD_VISUAL_PREVIEW",
        "requires_hindi_voice_qa":True,"requires_wan_animated_scenes":True,
        "original_prices":"REPLACED_WITH_LIVE_OR_DISCLOSED_CATALOG_SOURCE",
        "publishing_enabled":False},indent=2)+"\\n",encoding="utf-8")
    return paths

if __name__=="__main__":
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("--story",required=True);a.add_argument("--output",default="output/washing30-frames")
    v=a.parse_args()
    story=json.loads(Path(v.story).read_text("utf-8"))
    frames=render(story,v.output)
    print("WASHING30_VISUAL_PREVIEW_FRAMES_VERIFIED="+str(len(frames)))
    print("NO_GPU_NO_PUBLICATION=true")
