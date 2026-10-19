"""Offline Hindi TTS evaluation (Kokoro Apache-2.0; no paid API or cloning).

This evaluation is intentionally NOT a claim of natural Hindi voice quality.
No eSpeak fallback: if the neural voice fails, mark the pilot blocked for audio QA.
"""
import argparse
import json
import math
from pathlib import Path
import hashlib
import numpy as np
import soundfile as sf

SR=24000
DURATION=30

def _music(total):
    audio=np.zeros(total,dtype=np.float32)
    beats=np.arange(0,DURATION,.375)
    # Original four-chord playful marimba tones; royalty-free generated signal.
    scale=[293.66,369.99,440.0,587.33,523.25,440.,369.99,329.63]
    for i,start in enumerate(beats):
        a=int(start*SR)
        n=min(int(.26*SR),total-a)
        if n<=0:continue
        t=np.arange(n,dtype=np.float32)/SR
        tone=np.sin(2*np.pi*scale[i%len(scale)]*t)
        tone+=.18*np.sin(2*np.pi*scale[i%len(scale)]*2*t)
        env=np.minimum(1,t/.01)*np.exp(-t*11)
        audio[a:a+n]+=.065*tone*env
        if i%4==0:
            audio[a:a+n]+=.025*np.sin(2*np.pi*75*t)*np.exp(-t*28)
    # Sparkly bubble-pop sounds at ranking entry beats.
    for i,t0 in enumerate((4.0,7.7,11.4,15.1,18.9,23.8,27.1)):
        st=int(t0*SR);n=min(int(.20*SR),total-st)
        if n<=0:continue
        tt=np.arange(n,dtype=np.float32)/SR
        pop=np.sin(2*np.pi*(510-240*tt)*tt)*np.exp(-tt*24)
        audio[st:st+n]+=.12*pop
    return audio

def run(root,*,allow_model=True):
    root=Path(root)
    story=json.loads((root/'story.json').read_text('utf-8'))
    assert story['status']=='HISTORICAL_DEMO_NOT_FOR_PUBLICATION'
    if not allow_model:raise RuntimeError('Neural TTS required for non-robotic audio test')
    from kokoro import KPipeline
    import torch
    torch.set_num_threads(2)
    pipeline=KPipeline(lang_code='h')
    length=SR*DURATION
    music=_music(length)
    voice_track=np.zeros(length,dtype=np.float32)
    cues=[]
    voices_dir=root/'voices';voices_dir.mkdir(exist_ok=True)
    for i,line in enumerate(story['lines']):
        chunks=[]
        for _,_,audio in pipeline(line['text'],voice=line['voice'],speed=1.15,split_pattern=r'\n+'):
            if audio is None:continue
            chunks.append(audio.detach().cpu().numpy().astype(np.float32)
                          if hasattr(audio,'detach') else np.asarray(audio,dtype=np.float32))
        if not chunks:raise ValueError('Kokoro generated no voice waveform for scene '+str(i))
        voice=np.concatenate(chunks)
        if not np.isfinite(voice).all():raise ValueError('Nonfinite neural voice')
        allowed=line['end']-line['start']-.15
        actual=len(voice)/SR
        if actual>allowed+.15:
            raise ValueError('Hindi voice scene too long: '+str(i)+' '+str(round(actual,2))+
                             's > '+str(round(allowed,2))+'s; edit script, do not clip')
        sf.write(str(voices_dir/f'{i:02d}.wav'),voice,SR)
        st=int(line['start']*SR)
        end=min(length,st+len(voice))
        voice_track[st:end]+=voice[:end-st]*.82
        cues.append({'scene':i,'voice':line['voice'],'start':line['start'],
                     'duration_seconds':round(actual,3),
                     'peak':round(float(np.max(np.abs(voice))),4),
                     'text':line['text']})
        print('NEURAL_HINDI_LINE='+str(i)+' '+str(round(actual,2))+'s')
    if max(abs(voice_track))<.025:raise ValueError('Unexpectedly silent TTS')
    full=np.clip(voice_track+music,-.92,.92)
    target=root/'audio';target.mkdir(exist_ok=True)
    sf.write(str(target/'soundtrack.wav'),full,SR,subtype='PCM_16')
    # Envelope powers mouth gestures against the *actual* narration.
    window=int(.1*SR)
    rms=[]
    for st in range(0,length,window):
        chunk=voice_track[st:st+window]
        val=float(np.sqrt(np.mean(chunk*chunk))) if len(chunk) else 0
        rms.append(round(min(1,val*8),3))
    story['voiceEngine']='Kokoro-82M'
    story['voiceLanguage']='Hindi hi-IN with Hinglish brand names'
    story['voiceModelLicense']='Apache-2.0; verify commercial asset rights separately'
    story['audioFile']='audio/soundtrack.wav'
    story['voiceCues']=cues
    story['mouthEnvelope100ms']=rms
    (root/'story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sha=hashlib.sha256((target/'soundtrack.wav').read_bytes()).hexdigest()
    report={'engine':'hexgrad/Kokoro-82M','language':'hi','license':'Apache-2.0',
            'actual_voices':[v['voice'] for v in cues], 'audio_sha256':sha,
            'duration_seconds':DURATION,'peak_dbfs':round(20*math.log10(float(np.max(np.abs(full)))),2),
            'speech_energy':round(float(np.mean(voice_track**2)),5),
            'human_voice_quality_approved':False,
            'paid_api_used':False,'script_cues':cues}
    (target/'qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('KOKORO_HINDI_AUDIO_TECHNICAL_QA_PASSED=true')
    print('SPEECH_HUMAN_QUALITY_APPROVED=false')
    print('HINDI_AUDIO_SHA256='+sha)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='premium/public')
    args=p.parse_args()
    run(args.root)
