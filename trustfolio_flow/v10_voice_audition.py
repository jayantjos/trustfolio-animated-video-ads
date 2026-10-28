"""One-shot manual Hindi voice audition. Never publishes/sets model approved.

Requires user-set TF_VIDEO_VOICE_AUDITION_APPROVED=true to spend ONE short
speech request. The immutable voice ID is loaded from GitHub's voice profile.
"""
import hashlib,json,os
from pathlib import Path
from .v10_fixed_voice import load_profile,request_mp3,duration

SAMPLE="नमस्ते! ट्रस्टफोलियो पर अपना बजट चुनिए और पाँच असली वॉशिंग मशीनों की तुलना कीजिए।"

def audition(profile_path,outdir,*,api_key=None,enabled=False):
    if enabled is not True:
        raise RuntimeError("Voice-audition cost switch OFF. Zero TTS calls.")
    p=load_profile(profile_path)
    key=api_key or os.getenv("TF_VIDEO_INWORLD_API_KEY","")
    if not key:raise RuntimeError("Missing protected Inworld TTS secret")
    # Authorization is only for a single PREVIEW request, not social release.
    trial=dict(p,approved_for_hindi_narration=True)
    raw=request_mp3(SAMPLE,trial,key)
    dest=Path(outdir);dest.mkdir(parents=True,exist_ok=True)
    path=dest/"TrustFolio_V10_Hindi_Narrator_Preview_NOT_APPROVED.mp3"
    if path.exists():raise RuntimeError("Refuse overwrite or automatic retry")
    path.write_bytes(raw)
    try:
        seconds=duration(path)
        if not 1<=seconds<=18:raise ValueError("Voice sample length out of QA range")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    (dest/"voice_audition_status.json").write_text(json.dumps({
       "provider":p["provider"],"model_id":p["model_id"],"voice_id":p["voice_id"],
       "language":"hi","sample_sha256":hashlib.sha256(raw).hexdigest(),
       "sample_duration_s":round(seconds,2),"human_listening_approved":False,
       "change_profile_approved_flag_automatically":False,"max_billable_calls":1,
       "social_publication":False},indent=2)+"\n")
    print("FIXED_VOICE_HINDI_AUDITION_MP3_READY_FOR_LISTENING=YES")
    print("VOICE_MODEL_PRODUCTION_RELEASE=NO")
    return path

def main():
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument("--profile",required=True);a.add_argument("--outdir",required=True)
    q=a.parse_args()
    enabled=os.getenv("TF_VIDEO_VOICE_AUDITION_APPROVED")=="true"
    audition(q.profile,q.outdir,enabled=enabled)
if __name__=="__main__":main()
