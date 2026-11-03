"""Repair the existing MP4 without regenerating its characters or product data."""
import argparse,json,hashlib,subprocess,math,os
from pathlib import Path
import cv2,numpy as np,qrcode
from PIL import Image,ImageDraw,ImageFont
URL='https://play.google.com/store/apps/details?id=com.trustfolio.app'
def run(*a):subprocess.run(list(map(str,a)),check=True)
def ff(*a):run('ffmpeg','-y','-v','error',*a)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def duration(p):return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(p)],text=True))
def main():
 a=argparse.ArgumentParser();a.add_argument('--source',required=True);a.add_argument('--out',required=True);a.add_argument('--inspect-only',action='store_true');x=a.parse_args();root=Path(x.source);out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
 video=root/'review/TrustFolio_Washing_Machines_35000_Complete_Review.mp4';data=json.loads((root/'inputs/products.json').read_text());old=json.loads(Path(str(video)+'.qa.json').read_text());assert len(data['products'])==5
 cap=cv2.VideoCapture(str(video));fps=24;pts=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)],text=True))['frames'];times=[float(f['best_effort_timestamp_time']) for f in pts];origin=times[0]
 templates=[cv2.imread(str(root/f'review/qa_frame_{i:02d}.jpg'))[60:115,480:710].astype(float) for i in range(6,11)]
 starts=[]
 for idx,c in enumerate(old['chapters'][6:11]):
  first=max(0,int((c['start']-1.5)*fps));last=int((c['start']+1.5)*fps);cap.set(cv2.CAP_PROP_POS_FRAMES,first);hits=[]
  for f in range(first,last):
   ok,im=cap.read()
   if not ok:break
   crop=im[60:115,480:710].astype(float);scores=[np.mean(abs(crop-t)) for t in templates]
   if np.argmin(scores)==idx and scores[idx]<12:hits.append(f)
  candidates=[f for f in hits if f+1 in hits and f+2 in hits];assert candidates,f'Cannot identify rank {idx+1} visual boundary'
  starts.append(times[min(candidates)]-origin)
 cap.release();assert starts==sorted(starts)
 # CTA onset is detected from a stable logo crop around the prior chapter boundary.
 cap=cv2.VideoCapture(str(video));ref=cv2.imread(str(root/'review/qa_frame_11.jpg'))[150:370,400:700].astype(float);begin=int((old['chapters'][-1]['start']-1)*fps);cap.set(cv2.CAP_PROP_POS_FRAMES,begin);cta=None
 for f in range(begin,begin+72):
  ok,im=cap.read()
  if ok and np.mean(abs(im[60:115,480:710].astype(float)-templates[4]))>18:cta=times[f]-origin;break
 cap.release();assert cta and cta>starts[-1]
 end=round(duration(video)*fps)/fps;bounds=starts+[cta]
 if x.inspect_only:
  print(json.dumps(dict(starts=starts,cta=cta,end=end)));return
 # Validate frozen source identities and exact original photo bytes; independent SKU claims stay unverified.
 for p,receipt in zip(data['products'],old['photos']):
  n=p['rank'];m=json.loads((root/f'inputs/rank_{n:02d}.json').read_text());assert m['product_id']==p['product_id'] and m['source_snapshot_sha256']==data['snapshot_sha256'];assert m['wav_sha256']==sha(root/f'inputs/rank_{n:02d}.wav');assert receipt['product_id']==p['product_id'] and receipt['image_url']==p['image_url'] and receipt['sha256']==sha(root/f'review/rank_{n:02d}_source.png')
 # Separate only the two mixed soundtrack passages that receive replacement speech.
 intro=old['chapters'][3];istart=int(round(intro['start']*fps))/fps;iend=int(round(old['chapters'][4]['start']*fps))/fps
 for name,t,d in [('product_bed',starts[0],bounds[1]-starts[0]),('intro_bed',istart,iend-istart)]:
  ff('-ss',t,'-i',video,'-t',d,'-vn','-ac','2','-ar','44100',out/(name+'.wav'))
  run('python','-m','demucs','--device','cpu','--two-stems','vocals','-n','htdemucs','-o',out/'stems',out/(name+'.wav'))
 # Generate only the missing budget sentence using the already-approved CPU engine/reference.
 import torch,torchaudio
 from chatterbox.mtl_tts import ChatterboxMultilingualTTS
 budget=int(data['budget_inr']);spoken=str(budget)+' रुपये में टॉप पाँच वॉशिंग मशीनें।'
 model=ChatterboxMultilingualTTS.from_pretrained(device='cpu');wav=model.generate(spoken,language_id='hi',audio_prompt_path='reference.wav');torchaudio.save(str(out/'budget_raw.wav'),wav.cpu(),model.sr)
 raw=duration(out/'budget_raw.wav');available=iend-istart-.20;speed=max(1,raw/available);assert speed<=1.6,'Budget narration cannot fit naturally in the existing scene'
 ff('-i',out/'budget_raw.wav','-af',f'atempo={speed},adelay=100:all=1,apad','-t',iend-istart,out/'budget.wav')
 # Product WAVs begin after their detected frame boundary and end before the following transition.
 pieces=[]
 def source_piece(start,stop,name):
  path=out/(name+'.wav');ff('-ss',start,'-i',video,'-t',stop-start,'-vn','-ar','48000','-ac','2',path);pieces.append(path)
 source_piece(0,istart,'opening')
 bed=out/'stems/htdemucs/intro_bed/no_vocals.wav';p=out/'budget_mix.wav';ff('-i',bed,'-i',out/'budget.wav','-filter_complex','[0:a]volume=0.45[b];[b][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-map','[a]','-ar','48000','-ac','2',p);pieces.append(p)
 source_piece(iend,starts[0],'remaining_story')
 timing=[]
 for i,(start,stop) in enumerate(zip(starts,bounds[1:])):
  voice=root/f'inputs/rank_{i+1:02d}.wav';vlen=duration(voice);slot=stop-start;assert vlen+.10<slot,'Narration would cross a visual boundary'
  p=out/f'product_mix_{i+1}.wav';bed=out/'stems/htdemucs/product_bed/no_vocals.wav'
  ff('-stream_loop','-1','-i',bed,'-i',voice,'-filter_complex','[0:a]volume=0.40[b];[1:a]adelay=80:all=1,apad[v];[b][v]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]','-map','[a]','-t',slot,'-ar','48000','-ac','2',p);pieces.append(p);timing.append(dict(rank=i+1,visual_start=start,voice_start=start+.08,voice_end=start+.08+vlen,visual_end=stop))
 source_piece(cta,end,'cta_audio');playlist=out/'audio_concat.txt';playlist.write_text(''.join("file '"+str(p.resolve())+"'\n" for p in pieces));ff('-f','concat','-safe','0','-i',playlist,'-ar','48000','-ac','2',out/'soundtrack.wav')
 # Replace the failed QR only inside its existing white patch.
 qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=4,border=4);qr.add_data(URL);qr.make(fit=True);q=qr.make_image(fill_color='black',back_color='white').convert('RGB');q.save(out/'qr.png');assert cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(out/'qr.png')))[0]==URL
 layer=Image.new('RGBA',(720,1280));d=ImageDraw.Draw(layer);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34);d.text((478,78),f'₹{budget:,}',font=font,fill='#673f16');d.text((478,126),'Budget',font=font,fill='#673f16');d.text((478,181),'TOP 5',font=font,fill='#673f16');layer.save(out/'budget.png')
 # Keep every source frame, including the original character mouth. No synthetic mouth claims.
 target=out/'TrustFolio_35000_Corrected.mp4';graph=f"[0:v]setpts=PTS-STARTPTS,fps=24[v0];[v0][2:v]overlay=0:0:enable='between(t,{istart},{iend})'[v1];[v1][3:v]overlay=410:854:enable='gte(t,{cta})'[v];[1:a]asetpts=PTS-STARTPTS[a]"
 ff('-i',video,'-i',out/'soundtrack.wav','-loop','1','-i',out/'budget.png','-loop','1','-i',out/'qr.png','-filter_complex',graph,'-map','[v]','-map','[a]','-t',end,'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',target)
 cap=cv2.VideoCapture(str(target));qrchecks=[]
 for t in [cta+1,cta+3,cta+5]:
  cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,im=cap.read();decoded=cv2.QRCodeDetector().detectAndDecode(im)[0] if ok else '';qrchecks.append(decoded==URL)
 cap.release();assert all(qrchecks),'Final video QR decode failed'
 report=dict(source_run=41397080007,source_snapshot_sha256=data['snapshot_sha256'],duration_seconds=duration(target),chapters_preserved=12,five_original_wavs_reused=True,timing=timing,qr_url=URL,qr_frame_decode_pass=qrchecks,budget=budget,budget_spoken_text=spoken,budget_speech_speed=speed,source_image_hashes_match=True,lip_sync_verified=False,publication_allowed=False,limitations=['Original mouth animation retained: localized lip-sync is unverified.','CPU source separation may leave audible residuals or remove some music/SFX; perceptual listening approval remains required.','Frozen source image identity hashes verified; independent exact-model/SKU and retailer-page verification remains unverified.','Existing five WAV pronunciations were not independently listening-approved.'])
 (out/'FINAL_QA.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
