"""Offline, self-hosted Hindi voice test for TrustFolio; no paid speech API.

Run on a machine with Chatterbox Multilingual V3 installed. The original WAV
is the only voice reference. No hardcoded product claims; use dialogue JSON.
This module deliberately does not alter video or claim lip synchronization.
"""
import argparse,hashlib,json
from pathlib import Path

def render(dialogues,reference,outdir,rank=1,device="cuda"):
    data=json.loads(Path(dialogues).read_text(encoding="utf-8"))
    rows=data.get("product_lines")
    if not isinstance(rows,list) or len(rows)!=5 or [x.get("rank") for x in rows]!=[1,2,3,4,5]:
        raise ValueError("Exactly five verified ranked dialogues required")
    if not (1<=rank<=5):raise ValueError("rank must be 1..5")
    source=Path(reference)
    if not source.is_file() or source.stat().st_size<10000:
        raise ValueError("Original reference WAV missing or too small")
    row=rows[rank-1]
    if not row.get("text") or not row.get("product_id") or not data.get("snapshot_sha256"):
        raise ValueError("Missing source-backed dialogue")
    # Import after validation so contract QA can run without GPU packages.
    import torch,torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    if device=="cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable; do not start model/download")
    model=ChatterboxMultilingualTTS.from_pretrained(device=device,t3_model="v3")
    wav=model.generate(row["text"],language_id="hi",audio_prompt_path=str(source))
    target=Path(outdir);target.mkdir(parents=True,exist_ok=True)
    audio=target/f"rank_{rank:02d}.wav"
    torchaudio.save(str(audio),wav.cpu(),model.sr)
    duration=wav.shape[-1]/model.sr
    if not 0.5<duration<=9.7:
        audio.unlink(missing_ok=True)
        raise RuntimeError(f"Speech {duration:.2f}s does not fit original 10s chapter")
    proof={"rank":rank,"product_id":row["product_id"],"spoken_text":row["text"],
         "source_snapshot_sha256":data["snapshot_sha256"],
         "wav_sha256":hashlib.sha256(audio.read_bytes()).hexdigest(),
         "reference_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
         "model":"ChatterboxMultilingualTTS-v3","language":"hi",
         "seconds":round(duration,3),"voice_approved":False,
         "human_listening_qa":"PENDING","lip_sync_qa":"PENDING","publish_allowed":False}
    (target/f"rank_{rank:02d}.json").write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n")
    return proof

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dialogues",required=True)
    p.add_argument("--reference",default="assets/video/washing-machines/original_greenboy_reference.wav")
    p.add_argument("--outdir",required=True)
    p.add_argument("--rank",type=int,default=1)
    p.add_argument("--device",choices=["cuda","cpu"],default="cuda")
    a=p.parse_args()
    print(json.dumps(render(a.dialogues,a.reference,a.outdir,a.rank,a.device),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
