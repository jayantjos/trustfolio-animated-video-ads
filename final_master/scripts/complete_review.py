"""Complete review using approved visuals; never publish or claim verified lip sync."""
import argparse,hashlib,json,shutil,subprocess,tempfile,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from github_review_video import STORY,ff,probe,extract
import zipfile

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def line(row):
 words={1:'पहली',2:'दूसरी',3:'तीसरी',4:'चौथी',5:'पाँचवीं'};f=row['specifications']
 return f"{words[row['rank']]} पसंद, {row['brand']} की वॉशिंग मशीन। {f[0]['label']} {f[0]['value']}। {f[1]['label']} {f[1]['value']}।"
def prepare(current,cached):
 current=Path(current);cached=Path(cached);source=json.loads((current/'products.json').read_text());old=json.loads((cached/'products.json').read_text())
 needed=[]
 for p in source['products']:
  n=p['rank'];meta=cached/f'rank_{n:02d}.json';wav=cached/f'rank_{n:02d}.wav';proof=json.loads(meta.read_text()) if meta.exists() else {}
  if proof.get('product_id')==p['product_id'] and proof.get('text')==line(p) and wav.exists() and proof.get('wav_sha256')==digest(wav):
   shutil.copy2(wav,current/wav.name);proof['source_snapshot_sha256']=source['snapshot_sha256'];proof['reused_from_run']=41073504968
   (current/meta.name).write_text(json.dumps(proof,ensure_ascii=False,indent=2))
  else: needed.append(p)
 (current/'voices_needed.json').write_text(json.dumps(needed,ensure_ascii=False))
 print('VOICES_REQUIRING_GENERATION',len(needed))

def wrap(d,text,font,width):
 lines=[];cur=''
 for word in str(text).split():
  trial=(cur+' '+word).strip()
  if d.textlength(trial,font=font)>width and cur: lines.append(cur);cur=word
  else:cur=trial
 if cur:lines.append(cur)
 return lines

def layer(p,photo,out):
 # Only the original empty right region, x>=468 in the 720px master.
 im=Image.new('RGBA',(720,1280));d=ImageDraw.Draw(im);x=480;w=228;y=66
 def text(value,size=21,color='#432d20',gap=7):
  nonlocal y
  font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)
  for s in wrap(d,value,font,w):d.text((x,y),s,font=font,fill=color);y+=size+gap
 text('TOP #'+str(p['rank']),30,'#703b19');text('Budget INR 35,000',19);y+=10
 with Image.open(photo) as src:
  pic=src.convert('RGBA');pic.thumbnail((224,330),Image.Resampling.LANCZOS)
  im.alpha_composite(pic,(x+(w-pic.width)//2,y))
 y+=340
 title=p['title']
 # Full model title is retained, reducing type only if needed to fit the existing region.
 size=21 if len(title)<130 else 18
 text(title,size);y+=8;text(f"INR {p['price_inr']:,.0f}",27,'#703b19')
 text(p['price_label'],15);y+=10
 for s in p['specifications']:
  text(s['label']+': '+s['value'],19);y+=9
 if y>1230: raise ValueError(f"Rank {p['rank']} data exceeds original empty region: {y}")
 im.save(out)

def render(kit,inputs,output):
 inputs=Path(inputs);out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);data=json.loads((inputs/'products.json').read_text());parts=[];chapters=[];photos=[];clock=0
 with tempfile.TemporaryDirectory() as td,zipfile.ZipFile(kit) as z:
  tmp=Path(td)
  def append(src,name):
   nonlocal clock
   dur=probe(src);parts.append(src);chapters.append(dict(name=name,start=round(clock,3),seconds=round(dur,3)));clock+=dur
  for i,name in enumerate(STORY):
   src=extract(z,name,tmp);part=tmp/f'story{i}.mp4';ff('-i',src,'-vf','scale=720:1280,fps=24','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',part);append(part,name)
  green=extract(z,'08_green_boy_clean_master',tmp)
  for p in data['products']:
   n=p['rank'];wav=inputs/f'rank_{n:02d}.wav';meta=json.loads((inputs/f'rank_{n:02d}.json').read_text())
   assert meta['product_id']==p['product_id'] and meta['text']==line(p) and meta['source_snapshot_sha256']==data['snapshot_sha256'] and meta['wav_sha256']==digest(wav),'Voice/data mismatch'
   seconds=probe(wav);assert .3<seconds<=9.7,'Voice exceeds original clip'
   photo=out.parent/f'rank_{n:02d}_source.png'
   req=urllib.request.Request(p['image_url'],headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=40) as r:raw=r.read(12000000)
   download=tmp/f'photo{n}';download.write_bytes(raw)
   with Image.open(download) as im:
    assert min(im.size)>=100,'Low resolution product image';im.convert('RGBA').save(photo)
   photos.append(dict(rank=n,product_id=p['product_id'],image_url=p['image_url'],sha256=digest(photo)))
   overlay=tmp/f'layer{n}.png';layer(p,photo,overlay)
   dur=min(10,max(7,seconds+.5));part=tmp/f'rank{n}.mp4'
   # Original animation is preserved. This is narration over an original sound bed,
   # NOT verified lip synchronization or a claim of isolated music stems.
   graph=f'[0:v]scale=720:1280,fps=24[b];[b][1:v]overlay=0:0[v];[0:a]volume=0.12,aresample=48000[bed];[2:a]aresample=48000,apad[voice];[bed][voice]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]'
   ff('-i',green,'-loop','1','-i',overlay,'-i',wav,'-filter_complex',graph,'-map','[v]','-map','[a]','-t',dur,'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',part);append(part,f'rank_{n:02d}')
  src=extract(z,'09_premium_girl_cta',tmp);part=tmp/'cta.mp4';ff('-i',src,'-vf','scale=720:1280,fps=24','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',part);append(part,'09_premium_girl_cta')
  playlist=tmp/'join.txt';playlist.write_text(''.join("file '"+str(p)+"'\n" for p in parts));ff('-f','concat','-safe','0','-i',playlist,'-c','copy','-movflags','+faststart',out)
 duration=probe(out)
 assert len(chapters)==12 and abs(duration-clock)<.5,'Missing chapter or duration drift'
 qa=dict(budget_inr=35000,source_snapshot_sha256=data['snapshot_sha256'],duration_seconds=duration,chapters=chapters,photos=photos,five_voice_tracks=True,dynamic_text_replacement=True,exact_dynamic_photos=True,original_character_position_preserved=True,original_visual_clips=True,all_required_scenes_present=True,background_sound_preserved=True,lip_sync_verified=False,lip_sync_mode='ORIGINAL_ANIMATION_WITH_DYNAMIC_VOICEOVER',publish_allowed=False,limitations=['Mouth animation is original; dynamic Hindi narration is NOT verified lip-sync.','Product segment original mixed audio is lowered to 12%; music/SFX stems are not isolated, so residual original speech may remain.','Retailer image URLs match API product IDs; visual model identity requires final review.','Original CTA/QR retained; QR scan has not been independently verified.'],video_sha256=digest(out))
 Path(str(out)+'.qa.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
 # Contact sheet covers every required scene plus each product.
 thumbs=[]
 for i,c in enumerate(chapters):
  frame=out.parent/f'qa_frame_{i:02d}.jpg';ff('-ss',c['start']+min(1,c['seconds']/2),'-i',out,'-frames:v','1',frame);thumb=Image.open(frame).resize((180,320));thumbs.append(thumb)
 sheet=Image.new('RGB',(6*180,2*344),'white');d=ImageDraw.Draw(sheet)
 for i,(c,im) in enumerate(zip(chapters,thumbs)):
  x=i%6*180;y=i//6*344;sheet.paste(im,(x,y));d.text((x+3,y+322),c['name'][:25],fill='black')
 sheet.save(out.parent/'qa_contact_sheet.jpg')
 print('COMPLETE_GITHUB_REVIEW_CREATED',duration)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--prepare',action='store_true');a.add_argument('--inputs',required=True);a.add_argument('--cached');a.add_argument('--kit');a.add_argument('--output');v=a.parse_args()
 if v.prepare:prepare(v.inputs,v.cached)
 else:render(v.kit,v.inputs,v.output)
