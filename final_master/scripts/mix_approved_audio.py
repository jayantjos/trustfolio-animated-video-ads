"""Assemble approved per-rank speech into unchanged original 90s master audio bed.

This is AUDIO MIX ONLY. Never claim lip sync from audio overlay.
Voice provider is external; each WAV must have accompanying audited metadata.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
       "-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,check=True)
    return float(p.stdout.strip())
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def assemble(video,dialogues,voice_dir,out):
    data=json.loads(Path(dialogues).read_text(encoding="utf8"))
    rows=data["product_lines"]
    if len(rows)!=5 or [r["rank"] for r in rows]!=[1,2,3,4,5]:
        raise ValueError("Five source-ranked dialogues required")
    if data.get("release_authorized") is not False:
        raise ValueError("Refuse untrusted release status")
    if not 89.5 <= probe(video) <= 90.5:
        raise ValueError("Original 90-second master duration mismatch")
    inputs=["-i",str(video)];filters=[]
    for i,row in enumerate(rows,1):
        file=Path(voice_dir)/(f"rank_{i:02d}.wav")
        meta=Path(voice_dir)/(f"rank_{i:02d}.json")
        if not file.is_file() or not meta.is_file():
            raise ValueError(f"Missing externally approved voice WAV or metadata at rank {i}")
        proof=json.loads(meta.read_text())
        if proof.get("source_snapshot_sha256")!=data["snapshot_sha256"] or proof.get("product_id")!=row["product_id"] or proof.get("spoken_text")!=row["text"] or proof.get("wav_sha256")!=sha(file):
            raise ValueError(f"Voice receipt mismatch rank {i}")
        if proof.get("voice_approved") is not True:
            raise ValueError(f"Voice is not approved rank {i}")
        sec=probe(file)
        if not .25 <=sec<=9.7:raise ValueError(f"Voice cannot fit 10s chapter rank {i}: {sec}")
        inputs += ["-i",str(file)]
        filters.append(f"[{i}:a]aresample=48000,adelay={32000+(i-1)*10000}:all=1,volume=1[v{i}]")
    # Product original audio is ducked, never deleted; intro and CTA remain normal.
    filters.insert(0,"[0:a]aresample=48000,volume='if(between(t,32,82),0.28,1)':eval=frame[bed]")
    graph=";".join(filters)+";[bed]"+ "".join(f"[v{i}]" for i in range(1,6))+ "amix=inputs=6:duration=first:normalize=0,alimiter=limit=0.89[a]"
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-y","-v","error",*inputs,"-filter_complex",graph,"-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac","-b:a","192k","-t","90",str(out)]
    subprocess.run(cmd,check=True)
    if not 89.5<=probe(out)<=90.5:raise ValueError("Output duration wrong")
    result={"source_snapshot_sha256":data["snapshot_sha256"],"ranks":[r["rank"] for r in rows],
        "video_sha256":sha(out),"voice_receipts_checked":True,
        "original_visual_stream_copied":True,"original_music_bed_preserved":True,
        "lip_sync_qa_pass":False,"publish_allowed":False,
        "status":"AUDIO_MIX_REVIEW_ONLY_REQUIRES_VISUAL_LIP_SYNC"}
    Path(str(out)+".qa.json").write_text(json.dumps(result,indent=2)+"\n")
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True);p.add_argument("--dialogues",required=True)
    p.add_argument("--voice-dir",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    print(json.dumps(assemble(a.video,a.dialogues,a.voice_dir,a.out),indent=2))
