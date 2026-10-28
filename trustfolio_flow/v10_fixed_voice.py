"""Versioned fixed Hindi voice model for the extended 90-second TrustFolio Reel.

The vendor hosts the model. GitHub stores exact provider/model/voice ID, NEVER
private voice weights, API keys or raw character voice-cloning audio.
Speech uses source-backed five-product lines from ONE fresh TrustFolio receipt.
Each chapter has 10 seconds: NO tempo compression or robotic eSpeak fallback.
"""
from __future__ import annotations
import base64,hashlib,json,os,re,subprocess
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from .v6_live_campaign import validate_receipt

URL="https://api.inworld.ai/tts/v1/voice"
ORD=("पहली","दूसरी","तीसरी","चौथी","पाँचवीं")
BRAND={"ifb":"आई एफ बी","bosch":"बॉश","samsung":"सैमसंग",
       "whirlpool":"व्हर्लपूल","lg":"एल जी","voltas":"वोल्टास"}
NUM={"6":"छह","7":"सात","8":"आठ","9":"नौ","10":"दस","11":"ग्यारह","12":"बारह"}

def load_profile(path):
    p=json.loads(Path(path).read_text(encoding="utf-8"))
    if p.get("provider")!="inworld" or p.get("model_id")!="inworld-tts-2":
        raise ValueError("Unapproved voice provider or model")
    voice=p.get("voice_id")
    if not isinstance(voice,str) or not re.fullmatch(r"[A-Za-z0-9_-]{2,80}",voice):
        raise ValueError("Invalid fixed voice identifier")
    if p.get("language")!="hi":raise ValueError("Narrator language must be Hindi")
    return p

def real_reason(p):
    s=p["specifications"];title=p["title"].lower()
    cap=str(s.get("Capacity") or "").strip()
    m=re.fullmatch(r"(\d+)(?:\.0+)?\s*kg",cap,re.I)
    if not m or m.group(1) not in NUM:raise ValueError("Unverified capacity; block voice")
    load=str(s.get("Load Type") or "").lower().strip()
    if load not in ("top load","front load"):
        raise ValueError("Unverified load type; block voice")
    load_hi="टॉप लोड" if load=="top load" else "फ्रंट लोड"
    # Only claim product-title or specification facts, not comparative test results.
    if "steam" in title: reason="स्टीम फ़ीचर दिया गया है"
    elif any(x in title for x in ("in-built heater","inbuilt heater","built-in heater")):
        reason="इन-बिल्ट हीटर का फ़ीचर दिया गया है"
    elif any(x in title for x in ("wi-fi","wifi")):
        reason="वाई-फ़ाई कनेक्टिविटी का फ़ीचर दिया गया है"
    elif "deepclean" in title.replace(" ",""):
        reason="डीप क्लीन तकनीक का फ़ीचर दिया गया है"
    elif re.fullmatch(r"\d{2,4}\s*RPM",str(s.get("Spin Speed","")),re.I):
        reason="स्पिन स्पीड की जानकारी उपलब्ध है"
    elif s.get("Energy Rating") in ("5 Star","4 Star","3 Star"):
        reason=s["Energy Rating"].replace("5","पाँच").replace("4","चार").replace("3","तीन")+" एनर्जी रेटिंग है"
    else:reason="क्षमता और लोड टाइप स्रोत में दर्ज हैं"
    return NUM[m.group(1)],load_hi,reason

def voice_lines(receipt):
    validate_receipt(receipt)
    result=[]
    for i,p in enumerate(receipt["products"]):
        kg,load,reason=real_reason(p)
        brand=BRAND.get(str(p["brand"]).casefold(),p["brand"])
        line=f"{ORD[i]} पसंद, {brand}, {kg} किलो {load}। {reason}।"
        if len(line)>220:raise ValueError("Narration too long")
        result.append(line)
    if len(result)!=5:raise ValueError("Exactly five ranks needed")
    return result

def request_mp3(line,profile,key,*,opener=urlopen):
    if not key:raise RuntimeError("Protected TF_VIDEO_INWORLD_API_KEY missing")
    if profile.get("approved_for_hindi_narration") is not True:
        raise RuntimeError("Fixed voice Hindi sample has not been approved")
    payload={"modelId":profile["model_id"],"voiceId":profile["voice_id"],
             "text":line,"audioConfig":{"audioEncoding":"MP3"}}
    req=Request(URL,method="POST",data=json.dumps(payload,ensure_ascii=False).encode(),
                headers={"Authorization":"Basic "+key,"Content-Type":"application/json",
                         "Accept":"application/json"})
    try:
        with opener(req,timeout=45) as r:
            if r.status!=200:raise RuntimeError("TTS non-200; no auto retry")
            result=json.loads(r.read(7_000_000))
    except (HTTPError,URLError,TimeoutError):
        raise RuntimeError("Voice service failed; do not blindly repeat a billable call") from None
    value=result.get("audioContent")
    if not isinstance(value,str) or len(value)>7_000_000:
        raise RuntimeError("Voice response missing audioContent")
    raw=base64.b64decode(value,validate=True)
    if not 4000<=len(raw)<=5_250_000 or not(raw[:3]==b"ID3" or raw[:1]==b"\xff"):
        raise RuntimeError("Invalid MP3 output")
    return raw

def duration(path):
    out=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True)
    return float(out.strip())

def generate(receipt,profile_path,outdir,*,key=None,opener=urlopen):
    profile=load_profile(profile_path)
    if profile.get("approved_for_hindi_narration") is not True:
        raise RuntimeError("Unapproved voice. Zero paid requests.")
    texts=voice_lines(receipt)
    api_key=key or os.getenv("TF_VIDEO_INWORLD_API_KEY","")
    if not api_key:raise RuntimeError("No provider API key; zero paid requests")
    d=Path(outdir);d.mkdir(parents=True,exist_ok=True)
    for i,line in enumerate(texts,1):
        p=d/f"hindi_{i:02d}.mp3"
        if p.exists():raise RuntimeError("Old product voice file exists; refuse overwrite")
        p.write_bytes(request_mp3(line,profile,api_key,opener=opener))
        sec=duration(p)
        if not .75<=sec<=8.5:
            raise RuntimeError(f"Hindi voice #{i} too long/short ({sec}s); no speedup")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(p),
            "-af","aresample=48000,highpass=f=80,lowpass=f=9000,apad,atrim=duration=10",
            "-ac","1","-c:a","pcm_s16le",str(d/f"slot_{i:02d}.wav")],check=True)
    playlist=d/"concat.txt"
    playlist.write_text("".join("file '"+str((d/f"slot_{i:02d}.wav").resolve())+"'\n" for i in range(1,6)))
    stem=d/"fifty_seconds_stable_hindi_voice.wav"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat",
        "-safe","0","-i",str(playlist),"-ar","48000","-ac","1",
        "-c:a","pcm_s16le",str(stem)],check=True)
    if not 49.94<=duration(stem)<=50.06:raise RuntimeError("Voice stem is not 50 seconds")
    receipt_out={
       "source_snapshot_sha256":receipt["snapshot_sha256"],"voice_id":profile["voice_id"],
       "voice_model":profile["model_id"],"provider":"inworld","language":"hi",
       "spoken_lines":texts,"audio_sha256":hashlib.sha256(stem.read_bytes()).hexdigest(),
       "audio_qa":"AWAITING_HUMAN_LISTENING_QA","reel_publishing_authorized":False,
       "paid_calls_no_retries":5}
    (d/"voice_receipt.json").write_text(json.dumps(receipt_out,ensure_ascii=False,indent=2)+"\n")
    return stem

def mix(stable_video,voice_stem,output):
    if not 89.8<=duration(stable_video)<=90.2 or not 49.9<=duration(voice_stem)<=50.1:
        raise RuntimeError("Wrong 90s + 50s timeline. Don't compress speech.")
    graph=("[0:a]aresample=48000,volume='if(between(t,32,82),0.24,1)':eval=frame[bed];"
           "[1:a]aresample=48000,adelay=32000:all=1,volume=1.18[narrator];"
           "[bed][narrator]amix=inputs=2:duration=first:normalize=0,"
           "alimiter=limit=0.89:attack=5:release=50[a]")
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",
       "-i",str(stable_video),"-i",str(voice_stem),"-filter_complex",graph,
       "-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac","-ar","48000",
       "-b:a","192k","-t","90","-movflags","+faststart",str(output)],check=True)

def main():
    import argparse
    p=argparse.ArgumentParser()
    for key in ("receipt","voice-profile","output-dir"):p.add_argument("--"+key,required=True)
    p.add_argument("--stable-video")
    p.add_argument("--output-mp4")
    args=p.parse_args()
    receipt=json.loads(Path(args.receipt).read_text(encoding="utf8"))
    stem=generate(receipt,args.voice_profile,args.output_dir)
    if args.stable_video and args.output_mp4:mix(args.stable_video,stem,args.output_mp4)
    print("FIXED_VOICE_MODEL=SUCCESS; HUMAN_AUDIO_QA_AND_REAL_LIVE_PRICE_POST_GATE_STILL_REQUIRED")
if __name__=="__main__":main()
