"""Turn the 9 verified dynamic storyboards into a private, silent 30s QA MP4.

This is not a genuine animated Wan2.2 video and not reviewed Hindi voice.
Every frame is watermarked NOT FOR PUBLICATION. No GPU is created.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

def run(frame_dir,out):
    frames=Path(frame_dir)
    scenes=[frames/f"scene{i:02d}.png" for i in range(1,10)]
    if any(not p.is_file() or p.stat().st_size<10000 for p in scenes):
        raise RuntimeError("NINE_RENDERED_SCENE_PREVIEWS_REQUIRED")
    times=(3,3,4,4,4,4,4,2,2)
    listing=frames/"ffconcat.txt"
    with listing.open("w",encoding="utf-8") as f:
        f.write("ffconcat version 1.0\n")
        for scene,duration in zip(scenes,times):
            f.write("file '"+scene.resolve().as_posix()+"'\n")
            f.write("duration "+str(duration)+"\n")
        f.write("file '"+scenes[-1].resolve().as_posix()+"'\n")
    dest=Path(out);dest.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-safe","0","-f","concat","-i",str(listing),
        "-vf","fps=24,format=yuv420p",
        "-t","30","-c:v","libx264","-preset","fast","-crf","25",
        "-movflags","+faststart",str(dest)],check=True,timeout=180)
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration:stream=codec_name,width,height,codec_type",
        "-of","json",str(dest)],timeout=15)
    q=json.loads(raw)
    duration=float(q["format"]["duration"])
    streams=q["streams"]
    video=[x for x in streams if x["codec_type"]=="video"]
    audio=[x for x in streams if x["codec_type"]=="audio"]
    if len(video)!=1 or audio or video[0]["width"]!=1080 or video[0]["height"]!=1920 or not 29.8<=duration<=30.1:
        raise RuntimeError("CPU_PREVIEW_VIDEO_QA_FAILED")
    report={"status":"30_SECOND_SILENT_STORYBOARD_QA_PREVIEW_ONLY",
            "duration_seconds":duration,"width":1080,"height":1920,
            "has_hindi_voice":False,"has_wan_animation":False,"published":False,
            "gpu_created":False,"sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}
    (dest.parent/"video_qa.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("WASHING30_SILENT_MP4_PREVIEW_VERIFIED=true")
    print("WASHING30_ACTUAL_GPU_VIDEO=false")
    print("WASHING30_HAS_HINDI_AUDIO=false")
    return report

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--frames",required=True);a.add_argument("--output",required=True)
    args=a.parse_args();run(args.frames,args.output)
