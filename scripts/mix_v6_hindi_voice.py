#!/usr/bin/env python3
"""Mix approved Hindi product narration into a fully re-rendered V6 video.

Audio mix does NOT verify live prices, approve product photos or publish.
Do not use this to imply the historical 54s video has current prices.
"""
import argparse,json,subprocess
from pathlib import Path

def probe(path):
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height",
        "-of","json",str(path)],text=True)
    return json.loads(raw)

def mix(video,voice,output):
    video,voice,output=map(Path,(video,voice,output))
    for p in (video,voice):
        if not p.is_file():raise ValueError("Missing video or approved Hindi voice file: "+str(p))
    vm=probe(video);am=probe(voice)
    vd=float(vm["format"]["duration"]);ad=float(am["format"]["duration"])
    if not 53.8<=vd<=54.2:
        raise ValueError("Expected 54s NEWLY RENDERED dynamic V6 source")
    if not 9<=ad<=14:
        raise ValueError("Hindi five-product speech audio must fit into 14s (9-14s)")
    v=[x for x in vm["streams"] if x.get("codec_type")=="video"]
    if not v or (v[0].get("width"),v[0].get("height"))!=(720,1280):
        raise ValueError("Expected vertical 720x1280 video")
    output.parent.mkdir(parents=True,exist_ok=True)
    # Original story remains full-volume; only 32-46s product section ambience ducks.
    graph=("[0:a]aresample=48000,"
        "volume='if(between(t,31.95,46.05),0.24,1)':eval=frame[bg];"
        "[1:a]aresample=48000,atrim=0:14,asetpts=PTS-STARTPTS,"
        "afade=t=in:st=0:d=0.18,afade=t=out:st=13.72:d=0.20,"
        "adelay=32000:all=1,volume=1.45[vo];"
        "[bg][vo]amix=inputs=2:duration=first:normalize=0,"
        "loudnorm=I=-16:LRA=9:TP=-1.5,atrim=0:54[outa]")
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),
         "-i",str(voice),"-filter_complex",graph,"-map","0:v:0","-map","[outa]",
         "-c:v","copy","-c:a","aac","-ar","48000","-b:a","192k",
         "-movflags","+faststart","-t","54",str(output)]
    subprocess.run(cmd,check=True)
    if abs(float(probe(output)["format"]["duration"])-54)>0.2:
        raise RuntimeError("Audio mix duration drift")
    print("HINDI_NARRATION_MIX_COMPLETED=YES")
    print("LIVE_DATA_VERIFICATION_AND_PUBLISHING_NOT_DONE_BY_THIS_SCRIPT=YES")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True,help="Fresh correct-data V6 rendered 54s MP4")
    p.add_argument("--hindi-voice",required=True,help="Human-approved product voice recording covering up to 14s")
    p.add_argument("--output",required=True)
    a=p.parse_args();mix(a.video,a.hindi_voice,a.output)
