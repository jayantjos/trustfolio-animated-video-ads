"""Build a 30s motion-storyboard MP4 with actual Hindi neural speech, CPU only.

This is a narrated *storyboard review*, not nine Wan2.2 character animations.
No synthetic character lipsync, unsupported product claims or social publishing.
The base video is verified to contain fresh source prices, clean photos and CTA.
"""
import argparse,asyncio,hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone

from trustfolio_video.contract import Blocked
from scripts.stage_washing30_s3 import validate_stage

VOICE_FEMALE="hi-IN-SwaraNeural"
VOICE_MALE="hi-IN-MadhurNeural"
RANK_WORDS={5:"पाँच",4:"चार",3:"तीन",2:"दो",1:"एक"}

def timeline(story):
    validate_stage(story)
    texts=[
        "अरे बाप रे! इतने सारे कपड़े!",
        "ट्रस्टफोलियो पर, बजट की टॉप पाँच मशीनें!",
    ]
    for scene in story["scenes"][2:7]:
        p=scene["dynamic"]
        rank=p["rank"]
        brand=str(p["brand"])
        if not brand or len(brand)>80 or any(ord(ch)<32 for ch in brand):
            raise Blocked("Missing safe dynamic product brand")
        texts.append("नंबर "+RANK_WORDS[rank]+", "+brand+"! कीमत स्क्रीन पर देखें!")
    texts.extend(["ये हैं टॉप पाँच विकल्प!","आज ही ट्रस्टफोलियो पर तुलना करो!"])
    if len(texts)!=9:
        raise Blocked("Nine speech scenes mandatory")
    return [
        {"scene":i+1,"start":s["start"],"duration":s["seconds"],
         "voice":VOICE_FEMALE if i in (0,1,8) else VOICE_MALE,
         "speech_hi":texts[i],
         "source":"fixed_story" if i in (0,1,7,8) else "current_verified_top5"}
        for i,s in enumerate(story["scenes"])
    ]

def invoke(args,timeout=120):
    subprocess.run(args,check=True,timeout=timeout,
                   stdout=subprocess.DEVNULL)

def probe(media):
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration:stream=codec_name,codec_type,width,height",
        "-of","json",str(media)],timeout=12)
    return json.loads(raw)

async def synthesize(plan,work):
    import edge_tts
    work.mkdir(parents=True,exist_ok=True)
    for item in plan:
        mp3=work/f"scene{item['scene']:02d}.mp3"
        # Brisk delivery to respect 2, 3, and 4 second scene windows.
        await edge_tts.Communicate(item["speech_hi"],voice=item["voice"],rate="+90%").save(str(mp3))
        if mp3.stat().st_size<2000:raise RuntimeError("HINDI_MP3_EMPTY")

def build(story_path,silent_path,out):
    story=json.loads(Path(story_path).read_text(encoding="utf-8"))
    plan=timeline(story)
    silent=Path(silent_path)
    meta=probe(silent)
    silent_video=[x for x in meta["streams"] if x["codec_type"]=="video"]
    if len(silent_video)!=1 or any(x["codec_type"]=="audio" for x in meta["streams"]):
        raise RuntimeError("REQUIRE_SILENT_VERIFIED_INPUT_VIDEO")
    if silent_video[0]["width"]!=1080 or silent_video[0]["height"]!=1920:
        raise RuntimeError("INPUT_VIDEO_NOT_VERTICAL_1080")
    if not 29.8<=float(meta["format"]["duration"])<=30.1:
        raise RuntimeError("INPUT_VIDEO_NOT_30S")
    dest=Path(out);dest.parent.mkdir(parents=True,exist_ok=True)
    work=dest.parent/"voice-staging";work.mkdir(parents=True,exist_ok=True)
    asyncio.run(synthesize(plan,work))
    for item in plan:
        k=item["scene"];dur=item["duration"]
        mp3=work/f"scene{k:02d}.mp3"
        d=float(probe(mp3)["format"]["duration"])
        # atempo preserves speech pitch; fail if 2x cannot fit comfortably.
        tempo=max(1.0,d/max(.2,dur-.18))
        if tempo>2.0:
            raise RuntimeError("SPEECH_TOO_LONG_FOR_SCENE_"+str(k))
        item["raw_tts_duration_seconds"]=round(d,3)
        item["time_stretch_rate"]=round(tempo,3)
        wav=work/f"scene{k:02d}.wav"
        invoke(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
            "-i",str(mp3),"-af",f"atempo={tempo:.5f},apad",
            "-t",str(dur),"-ac","1","-ar","48000","-c:a","pcm_s16le",str(wav)],timeout=45)
        actual=float(probe(wav)["format"]["duration"])
        if abs(actual-dur)>.05:raise RuntimeError("AUDIO_TIMEBOX_ERROR_"+str(k))
    concat=work/"speech.ffconcat"
    concat.write_text("ffconcat version 1.0\n"+"".join(
        "file '"+(work/f"scene{i:02d}.wav").resolve().as_posix()+"'\n" for i in range(1,10)))
    joined=work/"hindi_voice_30s.wav"
    invoke(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
        "-safe","0","-f","concat","-i",str(concat),"-c:a","pcm_s16le",str(joined)],timeout=45)
    raw_duration=float(probe(joined)["format"]["duration"])
    if not 29.9<=raw_duration<=30.1:
        raise RuntimeError("HINDI_COMPOSITE_NOT_30S")
    # Subtle continuous motion of *already truthful* clean reference-derived
    # cards; never animate a baked-in sample product label or fake a talking face.
    motion="zoompan=z='1.025+0.018*sin(on/95)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=24,format=yuv420p"
    invoke(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
        "-i",str(silent),"-i",str(joined),
        "-filter:v",motion,"-map","0:v:0","-map","1:a:0",
        "-c:v","libx264","-preset","veryfast","-crf","27",
        "-c:a","aac","-b:a","128k","-ar","48000",
        "-t","30","-movflags","+faststart",str(dest)],timeout=300)
    result=probe(dest)
    v=[x for x in result["streams"] if x["codec_type"]=="video"]
    a=[x for x in result["streams"] if x["codec_type"]=="audio"]
    if len(v)!=1 or len(a)!=1 or a[0]["codec_name"]!="aac" or v[0]["width"]!=1080 or v[0]["height"]!=1920 or not 29.8<=float(result["format"]["duration"])<=30.1:
        raise RuntimeError("HINDI_MOTION_30S_OUTPUT_QA_FAILED")
    report={"status":"30S_HINDI_NARRATED_MOTION_STORYBOARD_QA_PASS",
        "frames":9,"duration_seconds":float(result["format"]["duration"]),
        "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
        "audio_codec":"aac","video_resolution":[1080,1920],
        "hindi_voice_technical_qa":True,"hindi_human_listening_qa":False,
        "animated_3d_characters":False,"lip_sync_verified":False,
        "visual_motion":"KEN_BURNS_ON_TRUTHFUL_DYNAMIC_CARDS",
        "paid_gpu_pods_created":0,"published":False,"publish_allowed":False,
        "price_observed_at":story["data_observed_at"],"source_sha256":story["source_sha256"],
        "catalog_fallback_count":story.get("catalog_fallback_count"),
        "voice_plan":plan}
    (dest.parent/"hindi_motion_qa.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("WASHING30_VOICED_MOTION_QA=PASS_NO_GPU")
    print("WASHING30_PREVIEW_HAS_HINDI_AUDIO=true")
    print("WASHING30_WAN2_2_ANIMATION=false")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--story",required=True)
    p.add_argument("--silent",required=True)
    p.add_argument("--output",required=True)
    x=p.parse_args();build(x.story,x.silent,x.output)
