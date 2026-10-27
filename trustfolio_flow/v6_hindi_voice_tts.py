"""Five short, clear Hindi voice lines from the SAME current-source Top5 receipt.

Optional paid speech API. Caller must explicitly provide protected API key.
Maximum five requests; never auto-retry billable generation on failure.
Output 14s narration (5 times 2.8s) for approved sound mix.
"""
import json,os,re,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from .v6_live_campaign import validate_receipt

BRAND_HINDI={"ifb":"आई एफ बी","bosch":"बॉश","samsung":"सैमसंग",
             "whirlpool":"व्हर्लपूल","lg":"एल जी","voltas":"वोल्टास"}
ORDINAL=("पहली","दूसरी","तीसरी","चौथी","पाँचवीं")

def scripts(receipt):
    validate_receipt(receipt)
    lines=[]
    for i,p in enumerate(receipt["products"]):
        specs=p["specifications"]
        brand=BRAND_HINDI.get(str(p["brand"]).casefold(),str(p["brand"]))
        capacity=specs.get("Capacity") or ""
        load=specs.get("Load Type") or ""
        if not re.fullmatch(r"\d+(?:\.\d+)?\s*kg",capacity,re.I):
            raise ValueError("Cannot safely voice unsupported capacity")
        number=capacity.split()[0].replace("8","आठ").replace("7","सात")
        term={"top load":"टॉप लोड","front load":"फ्रंट लोड"}.get(load.casefold())
        if not term:raise ValueError("Cannot safely voice missing load type")
        lines.append(f"{ORDINAL[i]} पसंद, {brand}, {number} किलो {term}।")
    return lines

def request_wav(line,key,*,opener=urlopen):
    data=json.dumps({"model":"gpt-4o-mini-tts","voice":"nova","response_format":"wav",
                     "speed":1.1,"input":line,
                     "instructions":"Speak only the supplied Hindi sentence naturally, friendly Indian Hindi pronunciation, clear energetic commercial narrator, no music or effects."},ensure_ascii=False).encode("utf-8")
    req=Request("https://api.openai.com/v1/audio/speech",data=data,
                method="POST",headers={"Authorization":"Bearer "+key,
                "Content-Type":"application/json","Accept":"audio/wav"})
    try:
        with opener(req,timeout=50) as r:
            if r.status!=200:raise RuntimeError("Voice generation did not return HTTP 200")
            raw=r.read(3_000_001)
            if len(raw)>3_000_000 or not raw.startswith(b"RIFF"):
                raise RuntimeError("Invalid voice audio response")
            return raw
    except (HTTPError,URLError,TimeoutError) as e:
        raise RuntimeError("Speech provider unavailable; no retry to avoid duplicate cost") from e

def duration(audio):
    out=subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],text=True)
    return float(out.strip())

def generate(receipt,outdir,*,key=None,opener=urlopen):
    lines=scripts(receipt)
    key=key or os.getenv("TF_VIDEO_OPENAI_TTS_API_KEY","")
    if not key:raise RuntimeError("Optional paid Hindi speech secret missing; do not publish silent product showcase")
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    pieces=[]
    # Cost cap: exactly five independent calls once; no retries if HTTP response ambiguous.
    for i,line in enumerate(lines,1):
        clip=out/f"hindi_{i:02d}.wav"
        clip.write_bytes(request_wav(line,key,opener=opener))
        seconds=duration(clip)
        if not 0.65<=seconds<=3.8:
            raise RuntimeError("Generated speech too short/long; stop, check voice quality")
        processed=out/f"slot_{i:02d}.wav"
        factor=max(1.0,seconds/2.67)
        if factor>1.44:raise RuntimeError("Hindi speech would sound rushed; shorten or revise narration")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-i",str(clip),"-af",f"atempo={factor:.4f},aresample=48000,"
            "apad=pad_dur=2.8,atrim=duration=2.8",
            "-ac","1","-c:a","pcm_s16le",str(processed)],check=True)
        pieces.append(processed)
    listfile=out/"voice_concat.txt"
    listfile.write_text("".join("file '"+str(p.resolve())+"'\n" for p in pieces))
    target=out/"five_products_hindi_14s.wav"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","concat","-safe","0","-i",str(listfile),"-ar","48000",
        "-ac","1","-c:a","pcm_s16le",str(target)],check=True)
    if not 13.95<=duration(target)<=14.05:
        raise RuntimeError("Hindi narration total duration is not exactly 14 seconds")
    (out/"source_backed_hindi_lines.json").write_text(json.dumps({
      "source_snapshot_sha256":receipt["snapshot_sha256"],"lines":lines,
      "provider":"OpenAI speech API","paid_requests":5,
      "qa":"UNREVIEWED_HINDI_VOICE_NOT_YET_RELEASE_APPROVED"},ensure_ascii=False,indent=2)+"\n")
    print("FIVE_REAL_SOURCE_HINDI_LINES_RENDERED=YES")
    print("VOICE_PRODUCTION_QA_MANUAL_GATE=REQUIRED")
    return target

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",required=True)
    p.add_argument("--output-dir",required=True)
    a=p.parse_args()
    receipt=json.loads(Path(a.receipt).read_text(encoding="utf8"))
    generate(receipt,a.output_dir)

if __name__=="__main__":main()
