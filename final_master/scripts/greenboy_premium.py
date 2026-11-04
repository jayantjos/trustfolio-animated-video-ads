"""Render the frozen mobile review with one reference voice and styled data panels."""
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

root = Path('premium')
root.mkdir(exist_ok=True)
video = Path('mobile/TrustFolio_35000_Mobile.mp4')
reference = Path('assets/video/washing-machines/original_greenboy_reference.wav')
snapshot = json.loads(Path('checkpoint/inputs/products.json').read_text())
qa = json.loads(Path('source/FINAL_QA.json').read_text())
products = snapshot['products']
assert qa['source_snapshot_sha256'] == snapshot['snapshot_sha256']
assert [p['rank'] for p in products] == [1, 2, 3, 4, 5]
budget = snapshot['budget_inr']
budget_words = {35000: 'पैंतीस हज़ार'}.get(budget, str(budget))
lines = [f'{budget_words} रुपये के बजट में देखिए पाँच बेहतरीन वॉशिंग मशीनें!']
brands = ['सैमसंग', 'गोदरेज', 'बॉश', 'व्हर्लपूल', 'एल जी']
models = []
verified_models = {
    '69f419329a622ea2d7ccb736': ('WFEON ZUS 9014 5.0 IDCRM GLWH', 'https://www.flipkart.com/p/itm85c805abf4849', 'डब्ल्यू एफ ई ऑन, ज़ेड यू एस, नौ शून्य एक चार'),
    '6a2d5c9956fa4e642c57742f': ('TX311SWO', 'https://www.flipkart.com/p/itm2d9a0b5dbfb1c?pid=WMNHMVUFQN4G2TMT', 'टी एक्स, तीन एक एक, एस डब्ल्यू ओ'),
}
for p, brand in zip(products, brands, strict=True):
    codes = re.findall(r'\b[A-Z]{2,}\d[A-Z0-9]*(?:/[A-Z0-9]+)?\b', p['title'])
    verified = verified_models.get(p['product_id'])
    code = verified[0] if verified else (codes[0] if len(codes) == 1 else None)
    models.append(code)
    facts = []
    for spec in p['specifications']:
        key, value = spec['label'], spec['value']
        if key == 'Capacity':
            words = {'7':'सात','8':'आठ','9':'नौ','11':'ग्यारह'}
            facts.append(words[value.split()[0]] + ' किलो क्षमता')
        elif key == 'Load Type':
            facts.append({'Front Load':'फ्रंट लोड','Top Load':'टॉप लोड'}[value])
        elif key == 'Energy Rating':
            facts.append({'5 Star':'पाँच स्टार रेटिंग'}[value])
        elif key in ('Automation Type', 'Washing Machine Type'):
            facts.append({'Fully Automatic':'पूरी तरह ऑटोमैटिक'}[value])
        elif key == 'Wash Features':
            facts.append({'In-built Heater':'बिल्ट इन हीटर'}[value])
        else:
            raise ValueError(spec)
    assert len(facts) == 4
    spoken_code = verified[2] if verified else code
    name = f'{brand}, मॉडल {spoken_code}' if spoken_code else brand
    lines.append(f'{name}। ' + ', '.join(facts[:-1]) + ' और ' + facts[-1] + '।')

def ff(*args):
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y',*map(str,args)],check=True)

def seconds(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)],text=True))

def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)

def overlay(index, frame):
    # Keep the approved placement and source imagery. Refine the existing panel only.
    still = root / f'still_{index}.png'
    ff('-ss',frame,'-i',video,'-frames:v',1,still)
    im = Image.open(still).convert('RGB')
    layer = Image.new('RGBA', im.size)
    draw = ImageDraw.Draw(layer)
    if index == 0:
        box = (470,60,695,255)
        draw.rounded_rectangle(box, radius=12, fill='#f3deae', outline='#a97127', width=3)
        layer.paste(im.crop((474,65,691,249)), (474,65))
        draw.line((486,245,680,245), fill='#b27d32', width=2)
    else:
        p = products[index-1]
        for y in range(43, 1251):
            t = min(1, (y-43)/850)
            color = tuple(round(a+(b-a)*t) for a,b in zip((233,202,148),(250,237,207)))
            draw.line((468,y,719,y), fill=color)
        draw.line((469,43,469,1250), fill='#b78239', width=2)
        draw.rounded_rectangle((480,51,686,162),radius=11,fill='#f8e7bf',outline='#c79852',width=2)
        layer.paste(im.crop((480,173,690,468)),(480,173))
        def text(x,y,s,size,max_width=170):
            f = font(size)
            while draw.textlength(s,font=f)>max_width:
                size -= 1
                f = font(size)
            draw.text((x,y),s,font=f,fill='#4c2b16')
        text(488,57,f'#{index} {p["brand"]}',29,190)
        specs = {x['label']:x['value'] for x in p['specifications']}
        text(488,98,f'{specs["Capacity"]} · {specs["Load Type"]}',24,190)
        code = models[index-1] or 'Model unverified'
        if code.startswith('WFEON ZUS '):
            text(488,126,'WFEON ZUS 9014',20,190)
            text(488,149,'5.0 IDCRM GLWH',18,190)
        else:
            text(488,131,code,21,190)
        draw.rounded_rectangle((479,480,650,580),radius=12,fill='#e9bd72',outline='#b9833e',width=2)
        text(487,488,f'₹{p["price_inr"]:,.0f}',39,154)
        text(487,536,p['price_label'].split(' - ')[0],23,153)
        y = 595
        if p['price_label'].startswith('CATALOG'):
            text(484,y,'Not live-verified',19)
            y += 34
        labels={'Capacity':'Capacity','Load Type':'Load','Automation Type':'Operation','Washing Machine Type':'Operation','Energy Rating':'Energy','Wash Features':'Heater'}
        for key,value in specs.items():
            draw.rounded_rectangle((478,y,649,y+57),radius=8,fill='#fff0cf',outline='#d9b577')
            text(486,y+3,labels[key],18,154)
            text(486,y+25,{'Fully Automatic':'Fully auto','In-built Heater':'Built-in'}.get(value,value),23,154)
            y += 65
    out = root / f'panel_{index}.png'
    layer.save(out)
    return out

import torch
import torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

torch.set_num_threads(2)
torch.manual_seed(35000)
engine = ChatterboxMultilingualTTS.from_pretrained(device='cpu')
voice_paths = []
prior_qa = Path('first-pass/QA.json')
prior = json.loads(prior_qa.read_text()) if prior_qa.exists() else {}
reference_sha = hashlib.sha256(reference.read_bytes()).hexdigest()
for i,line in enumerate(lines):
    path = root / f'greenboy_{i}.wav'
    previous = Path(f'first-pass/greenboy_{i}.wav')
    if previous.exists() and prior.get('reference_sha256') == reference_sha and prior.get('texts', [None]*6)[i] == line:
        path.write_bytes(previous.read_bytes())
        voice_paths.append(path)
        continue
    speech = engine.generate(line,language_id='hi',audio_prompt_path=str(reference),exaggeration=0.5,cfg_weight=0.5,temperature=0.8)
    torchaudio.save(str(path),speech.cpu(),engine.sr)
    assert 1 < seconds(path) < 35, (line, seconds(path))
    voice_paths.append(path)
    print(f'Voice {i} generated: {seconds(path):.2f}s',flush=True)

def frame_time(t):
    return math.ceil(t*24-1e-7)/24

starts = [frame_time(t['visual_start']) for t in qa['timing']]
cta = frame_time(qa['timing'][-1]['visual_end'])
intro_start, intro_end = 289/24, 385/24
parts = []
timings = []
clock = 0.0

def segment(start, stop, voice=None):
    global clock
    source_len = stop-start
    duration = source_len if voice is None else max(source_len,frame_time(seconds(voice_paths[voice])+0.32))
    out = root / f'part_{len(parts):02d}.mp4'
    args = ['-ss',start,'-t',source_len,'-i',video]
    if voice is None:
        args += ['-map','0:v:0','-map','0:a:0']
    else:
        art = overlay(voice,(start+stop)/2)
        bed_name = 'intro_bed' if voice == 0 else 'product_bed'
        bed = f'source/stems/htdemucs/{bed_name}/no_vocals.wav'
        args += ['-i',art,'-i',voice_paths[voice],'-stream_loop','-1','-i',bed]
        graph = (
            f'[0:v]setpts=(PTS-STARTPTS)*{duration/source_len},fps=24[v0];'
            '[v0][1:v]overlay=0:0[v];'
            '[2:a]aresample=48000,adelay=80:all=1,apad[n];'
            f'[3:a]volume=0.36,aresample=48000,atrim=duration={duration}[b];'
            '[b][n]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]'
        )
        args += ['-filter_complex_threads',1,'-filter_complex',graph,'-map','[v]','-map','[a]']
        timings.append(dict(chapter=voice, start=clock, speech_start=clock+.08,
                            speech_end=clock+.08+seconds(voice_paths[voice]), end=clock+duration,
                            visual_retime=duration/source_len))
    ff(*args,'-t',duration,'-c:v','libx264','-preset','veryfast','-crf',17,'-r',24,
       '-pix_fmt','yuv420p','-c:a','aac','-ar',48000,'-ac',2,'-b:a','192k',out)
    parts.append(out)
    clock += seconds(out)

segment(0,intro_start)
segment(intro_start,intro_end,0)
segment(intro_end,starts[0])
for i,(start,stop) in enumerate(zip(starts,starts[1:]+[cta]),1):
    segment(start,stop,i)
segment(cta,qa['duration_seconds'])
playlist = root/'concat.txt'
playlist.write_text(''.join(f"file '{p.name}'\n" for p in parts))
target = root/'TrustFolio_35000_GreenBoy_Premium.mp4'
ff('-f','concat','-safe',0,'-i',playlist,'-c','copy','-movflags','+faststart',target)
assert all(t['start'] <= t['speech_start'] < t['speech_end'] < t['end'] for t in timings)
for t in timings:
    ff('-ss',(t['start']+t['end'])/2,'-i',target,'-frames:v',1,'-vf','scale=360:640',root/f'mobile_{t["chapter"]}.png')
ff('-i',target,'-f','null','-')
report = dict(duration=seconds(target), reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
              voice_engine='Chatterbox Multilingual CPU, Hindi, cfg=.5 exaggeration=.5 temperature=.8',
              texts=lines, timing=timings, model_codes=models, retailer_model_evidence=verified_models, voice_identity_approved=False,
              listening_qa='Pending perceptual comparison', localized_lip_sync_verified=False,
              background='Original separated music/SFX beds under new speech, other scenes use source audio',
              publish_allowed=False)
(root/'QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
