#!/usr/bin/env python3
"""Warm-gold NO BLUE video finishing treatment for all TrustFolio V8 Reels.

Applies a deterministic color 3D LUT ONLY to product showroom and CTA scenes,
preserving ORIGINAL cartoon actors, their costumes and the untouched AAC
soundtrack. This is not live-price/photo QA or a social publisher.

LUT remaps blue, cyan and bluish-violet saturated materials to walnut/copper/
champagne-gold, leaving neutral appliances, skin tones and existing gold alone.
Built with Python standard library and FFmpeg; no Google Flow/GPU cost.
"""
from __future__ import annotations
import argparse
import colorsys
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

def smoother(x,a,b):
    t=max(0.0,min(1.0,(x-a)/(b-a)))
    return t*t*(3-2*t)

def warm_pixel(red,green,blue):
    hue,sat,val=colorsys.rgb_to_hsv(red,green,blue)
    strength=(smoother(hue,76/180,106/180)
             *(1-smoother(hue,171/180,179/180))
             *smoother(sat,8/255,36/255))
    new_hue=(16 if val>140/255 else 11)/180
    new_sat=(max(sat*.72,108/255) if val>145/255
             else max(sat*.78,104/255))
    new_rgb=colorsys.hsv_to_rgb(new_hue,min(1,new_sat),min(1,val*1.07))
    return tuple(red0*(1-strength)+new0*strength
                 for red0,new0 in zip((red,green,blue),new_rgb))

def write_lut(path,size=49):
    if not 9<=size<=65 or size%2!=1:
        raise ValueError("3D LUT needs an odd cube size between 9 and 65")
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="ascii") as out:
        out.write('TITLE "TrustFolio V8 No Blue Warm Gold"\n')
        out.write(f"LUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n")
        # .cube canonical order: red varies fastest, then green, then blue
        for bi in range(size):
            b=bi/(size-1)
            for gi in range(size):
                g=gi/(size-1)
                for ri in range(size):
                    r=ri/(size-1)
                    values=warm_pixel(r,g,b)
                    out.write(" ".join(f"{v:.6f}" for v in values)+"\n")
    return p

def probe(path):
    return json.loads(subprocess.check_output(["ffprobe","-v","error",
        "-show_entries","format=duration:stream=codec_type,codec_name,width,height,sample_rate",
        "-of","json",str(path)],text=True))

def grade(source,destination,*,start_seconds=28.0,lut_size=49):
    source=Path(source);destination=Path(destination)
    if not source.is_file() or source.stat().st_size<50_000:
        raise ValueError("Missing real MP4 source")
    if source.resolve()==destination.resolve():
        raise ValueError("Never overwrite uploaded approved artistic master")
    info=probe(source)
    duration=float(info["format"]["duration"])
    if not 53.7<=duration<=90.3 or start_seconds<0 or start_seconds>duration-3:
        raise ValueError("Unsupported duration/start for washing-machine V8 master")
    streams=info.get("streams",[])
    vid=next((x for x in streams if x.get("codec_type")=="video"),{})
    aud=next((x for x in streams if x.get("codec_type")=="audio"),{})
    if (vid.get("codec_name")!="h264" or (vid.get("width"),vid.get("height"))!=(720,1280)
        or aud.get("codec_name")!="aac" or aud.get("sample_rate")!="48000"):
        raise ValueError("Source must have approved 720x1280 H264 + 48 kHz AAC soundtrack")
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tf_v8_") as temp:
        lut=write_lut(Path(temp)/"no_blue.cube",size=lut_size)
        vf=f"lut3d=file={lut}:interp=tetrahedral:enable='gte(t,{start_seconds:g})'"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(source),
            "-vf",vf,"-map","0:v:0","-map","0:a:0",
            "-c:v","libx264","-preset","veryfast","-crf","20",
            "-pix_fmt","yuv420p","-r","24","-c:a","copy",
            "-movflags","+faststart",str(destination)],check=True)
    output=probe(destination)
    if abs(float(output["format"]["duration"])-duration)>.26:
        raise RuntimeError("Video timing changed during recolor")
    report={"preset":"TRUSTFOLIO_V8_WARM_GOLD_NO_BLUE",
            "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "output_sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
            "story_seconds_preserved":min(start_seconds,duration),
            "animated_stage_remapped_to":"champagne gold, copper, walnut, warm plum",
            "original_aac_audio_bitstream":"copy",
            "live_prices_verified_by_grade":False,
            "social_publishing_enabled_by_grade":False}
    destination.with_suffix(".color_qa.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("V8_NO_BLUE_WARM_GOLD_VIDEO_QA=PASS")
    print("LIVE_PRICE_PHOTO_AUDIO_RELEASE_GATES_STILL_REQUIRED=YES")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--start-seconds",type=float,default=28)
    a=p.parse_args()
    grade(a.input,a.output,start_seconds=a.start_seconds)

if __name__=="__main__":
    main()
