"""Local 40-second TrustFolio video data compositor; no API, GPU, or publishing writes."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
from .receipt import validate, price, InvalidReceipt

W,H=360,640
TIMES={'features':(12,20),'budget':(24,28),'top5':(28,32),'compare':(32,36),'cta':(36,40)}
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
HI='/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf'

def money(v): return '₹'+f'{int(price(v)):,}'

def line(d,xy,s,sz=13,width=300,color='white',hindi=False):
    font=ImageFont.truetype(HI if hindi else FONT,sz)
    s=str(s).strip();x,y=xy; words=s.split();part='';n=0
    for w in words:
        nextpart=(part+' '+w).strip()
        if part and d.textlength(nextpart,font=font)>width:
            d.text((x,y),part,font=font,fill=color);y+=sz+5;n+=1;part=w
            if n==2:break
        else:part=nextpart
    if part:d.text((x,y),part,font=font,fill=color)

def panel(d,xy):d.rounded_rectangle(xy,radius=13,fill=(14,15,58,235),outline=(219,187,112,220),width=2)

def header(d,s):panel(d,(8,15,352,67));line(d,(18,28),s,18,326,'#FFFFFF')

def product(d,p,x,y,w,h,rank):
    panel(d,(x,y,x+w,y+h))
    line(d,(x+9,y+8),f'#{rank} • {p["brand"]}',12,w-18,'#FFE077')
    line(d,(x+9,y+33),p['title'],10,w-18)
    line(d,(x+9,y+h-26),money(p['price_inr']),14,w-18,'#FFF29C')

def make_cards(doc,demo=False):
    cards={};p=doc['products']
    def sheet(title):
        im=Image.new('RGBA',(W,H),(0,0,0,0));draw=ImageDraw.Draw(im);header(draw,title);return im,draw
    im,d=sheet('FEATURES • VERIFIED DATA')
    for j,v in enumerate(p[:2]):
        spec=list(v.get('specifications',{}).items())[:2];x=174;y=106+j*202
        panel(d,(x,y,351,y+181));line(d,(x+8,y+8),v['brand'],15,159,'#FFE077')
        for i,(k,val) in enumerate(spec):
            line(d,(x+8,y+44+i*58),k,12,151,'#FFFFFF')
            line(d,(x+8,y+65+i*58),val,12,151,'#D5E3FF')
    cards['features']=im
    im,d=sheet('BUDGET • BRAND • PRICE')
    panel(d,(155,186,353,326));line(d,(166,207),money(doc['budget_inr']),24,183,'#FFE077')
    line(d,(166,262),doc['mode'].replace('_',' + ').upper(),12,180)
    if doc.get('brand'):line(d,(166,284),doc['brand'],12,175)
    cards['budget']=im
    im,d=sheet('TOP 5 • VERIFIED PRICES')
    product(d,p[0],96,98,166,115,1)
    for i,(x,y) in enumerate([(9,230),(184,230),(9,351),(184,351)],1):product(d,p[i],x,y,166,111,i+1)
    cards['top5']=im
    im,d=sheet('PRODUCT COMPARISON')
    for i in range(2):
        x=9+i*176;product(d,p[i],x,151,166,179,i+1)
        panel(d,(x,341,x+166,442));spec=list(p[i].get('specifications',{}).items())[:1]
        if spec:
            k,v=spec[0];line(d,(x+9,355),k,12,147,'#FFE077');line(d,(x+9,382),v,12,147)
        else:line(d,(x+9,356),'No specs verified',11,147)
    cards['compare']=im
    im,d=sheet('TrustFolio')
    panel(d,(165,140,355,316));line(d,(178,162),'अपना बजट डालो',16,169,hindi=True)
    line(d,(178,207),'Best 5',19,165,'#FFE077')
    line(d,(178,238),'पाओ!',18,160,'#FFE077',True)
    d.rounded_rectangle((139,341,355,406),radius=17,fill=(255,255,255,245))
    line(d,(149,360),'TrustFolio.in',17,196,'#3B1681')
    cards['cta']=im
    if demo:
        for im in cards.values():
            d=ImageDraw.Draw(im);panel(d,(96,571,265,621));line(d,(109,587),'SAMPLE • NOT LIVE',12,149,'#FFCB75')
    return cards

def probe(video):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise RuntimeError('ffmpeg + ffprobe required')
    result=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(video)],text=True)
    dat=json.loads(result);stream=next(s for s in dat['streams'] if s['codec_type']=='video')
    if (stream['width'],stream['height'])!=(W,H) or abs(float(dat['format']['duration'])-40)>0.25:raise RuntimeError('Expected 40s 360x640 source')

def render(master,doc,out,*,demo=False):
    validate(doc,demo=demo)
    master=Path(master).resolve();out=Path(out).resolve()
    if master==out:raise RuntimeError('Source overwrite refused')
    probe(master);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tf-graphics-') as directory:
        cards=make_cards(doc,demo)
        command=['ffmpeg','-nostdin','-y','-loglevel','error','-i',str(master)]
        for k in TIMES:
            path=Path(directory)/(k+'.png');cards[k].save(path)
            command.extend(['-loop','1','-framerate','24','-i',str(path)])
        prev='[0:v]';filters=[]
        for i,(name,(start,end)) in enumerate(TIMES.items(),1):
            dest=f'[v{i}]';filters.append(f"{prev}[{i}:v]overlay=0:0:format=auto:enable='between(t,{start},{end-0.043})'{dest}");prev=dest
        command+=['-filter_complex',';'.join(filters),'-map',prev,'-map','0:a?','-c:v','libx264','-preset','ultrafast','-crf','25','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart','-t','40',str(out)]
        subprocess.run(command,check=True)
    probe(out)
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master',required=True);parser.add_argument('--receipt',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--demo',action='store_true',help='Only synthetic QA fixture, permanently watermarked')
    options=parser.parse_args()
    doc=json.loads(Path(options.receipt).read_text(encoding='utf-8'))
    try:print('RENDERED:',render(options.master,doc,options.output,demo=options.demo))
    except (InvalidReceipt,RuntimeError,subprocess.CalledProcessError) as exc:parser.error(str(exc))

if __name__=='__main__':main()
