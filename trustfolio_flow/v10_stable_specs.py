"""Pixel-locked warm-gold specification overlays from verified current Top 5.

Use the CLEAN 40-second Flow cartoon footage; never float baked specs over
an already moving/oscillating legacy dynamic overlay. Cartoon motion remains;
the text itself does not pan/crop/zoom and has no blue border or card.
"""
import json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from .v6_live_campaign import validate_receipt,source_specs
W,H=720,1280
INK=(74,42,31,255);GOLD=(182,115,45,255);MUTED=(128,82,48,255)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def phrase(draw,pos,value,size,color=INK,anchor="lt"):
    draw.text(pos,str(value),font=ImageFont.truetype(FONT,size),
              fill=color,anchor=anchor,stroke_width=1,stroke_fill=(255,245,220,135))

def make_layers(receipt,folder):
    validate_receipt(receipt)
    product=receipt["products"][0]
    specs={x["label"]:x["value"] for x in source_specs(product)}
    for key in ("Capacity","Load Type","Energy Rating","Automation Type"):
        if key not in specs:raise ValueError("Missing actual source spec: "+key)
    dest=Path(folder);dest.mkdir(parents=True,exist_ok=True)
    a=Image.new("RGBA",(W,H));d=ImageDraw.Draw(a)
    phrase(d,(41,87),"THE SMARTER WASH",32)
    d.line((41,139,313,139),fill=GOLD,width=4)
    phrase(d,(42,162),str(specs["Capacity"]).upper()+" · "+str(specs["Load Type"]).upper(),19,MUTED)
    phrase(d,(42,204),str(specs["Energy Rating"]).upper()+" ENERGY RATING",17,MUTED)
    p1=dest/"girl_spec_LOCKED.png";a.save(p1)
    a=Image.new("RGBA",(W,H));d=ImageDraw.Draw(a)
    phrase(d,(462,83),"4 REAL SPECS",27)
    d.line((462,124,704,124),fill=GOLD,width=3)
    rows=[("01 CAPACITY",specs["Capacity"]),("02 LOAD TYPE",specs["Load Type"]),
          ("03 ENERGY RATING",specs["Energy Rating"]),("04 AUTOMATION",specs["Automation Type"])]
    for i,(label,value) in enumerate(rows):
        y=161+i*126
        phrase(d,(462,y),label,15,MUTED)
        if i==3 and str(value).casefold()=="fully automatic":
            phrase(d,(462,y+33),"FULLY",28)
            phrase(d,(462,y+68),"AUTOMATIC",24)
            bottom=y+105
        else:
            phrase(d,(462,y+34),str(value).upper(),27)
            bottom=y+90
        d.line((462,bottom,699,bottom),fill=(194,137,73,180),width=2)
    p2=dest/"boy_four_spec_LOCKED.png";a.save(p2)
    a=Image.new("RGBA",(W,H));d=ImageDraw.Draw(a)
    phrase(d,(454,100),"YOUR BUDGET",23,MUTED)
    d.line((448,132,692,132),fill=GOLD,width=3)
    phrase(d,(451,155),f"₹{receipt['budget_inr']:,}",43)
    phrase(d,(453,224),"TOP FIVE PICKS",20,MUTED)
    p3=dest/"budget_LOCKED.png";a.save(p3)
    return [p1,p2,p3]

def render_intro(clean_40s,receipt,output,*,folder):
    layers=make_layers(receipt,folder)
    inputs=["-i",str(clean_40s)]
    for p in layers:inputs+=["-loop","1","-framerate","24","-i",str(p)]
    graph=("[0:v]scale=720:1280:flags=lanczos,format=rgba[base];"
           "[base][1:v]overlay=enable='gte(t,12)*lt(t,16)':shortest=1[v1];"
           "[v1][2:v]overlay=enable='gte(t,16)*lt(t,20)':shortest=1[v2];"
           "[v2][3:v]overlay=enable='gte(t,24)*lt(t,28)':shortest=1,format=yuv420p[out]")
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",*inputs,
        "-filter_complex",graph,"-map","[out]","-an","-t","28","-r","24",
        "-threads","4","-c:v","libx264","-preset","veryfast","-crf","21",
        "-pix_fmt","yuv420p",str(output)],check=True)
    return Path(output)

def encode_still_without_shake(image,seconds,output):
    if seconds not in (4,10):raise ValueError("Only reviewed fixed cartoon segment lengths")
    # No sinusoidal crop, time-based camera transform or synthesized jitter.
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",
        "-loop","1","-framerate","24","-t",str(seconds),"-i",str(image),
        "-vf","scale=720:1280,format=yuv420p","-an","-threads","4",
        "-c:v","libx264","-preset","veryfast","-crf","22","-r","24",str(output)],check=True)
    return Path(output)
