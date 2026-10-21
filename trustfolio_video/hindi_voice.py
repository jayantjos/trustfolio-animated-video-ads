"""Hindi voice adapter. Google Cloud TTS is OPT-IN and never claimed unlimited/free."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
from urllib.request import Request, urlopen
from .contract import Blocked

DEFAULT_TEXT = "अरे! इतने सारे कपड़े! अब कौन धोएगा?"

def local_demo(text, output):
    """Auditable offline, robotic Hindi demo; not approval-grade natural speech."""
    if not text or len(text)>1000:
        raise Blocked("Invalid TTS text")
    wav = Path(output).with_suffix(".wav")
    try:
        subprocess.run(["espeak","-v","hi","-s","133","-w",str(wav),text],
                       check=True,timeout=60,stdout=subprocess.DEVNULL)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(wav),
                        "-codec:a","libmp3lame","-qscale:a","3",str(output)],
                       check=True,timeout=60)
    finally:
        wav.unlink(missing_ok=True)
    return Path(output)

def google_cloud_mp3(text, output, *, environ=None, opener=None):
    """No default network request. Google OAuth token must be separately provisioned.
    Charges depend on Google's actual usage; no hard zero-cost guarantee is possible.
    """
    e = os.environ if environ is None else environ
    if e.get("TRUSTFOLIO_ALLOW_BILLABLE_TTS") != "I_ACCEPT_POSSIBLE_CHARGES":
        raise Blocked("Google Cloud TTS disabled: billing acknowledgement required")
    token = e.get("GOOGLE_CLOUD_ACCESS_TOKEN")
    if not token:
        raise Blocked("Missing short-lived Google Cloud OAuth token")
    if not isinstance(text,str) or not text.strip() or len(text)>1000:
        raise Blocked("Invalid text")
    payload=json.dumps({"input":{"text":text},"voice":{"languageCode":"hi-IN",
        "name":"hi-IN-Standard-A"},"audioConfig":{"audioEncoding":"MP3"}},
        ensure_ascii=False).encode("utf-8")
    request=Request("https://texttospeech.googleapis.com/v1/text:synthesize",
                    data=payload,headers={"Authorization":"Bearer "+token,
                    "Content-Type":"application/json"},method="POST")
    opener=opener or urlopen
    try:
        with opener(request,timeout=40) as response:
            if response.status!=200:
                raise Blocked("Google TTS HTTP error")
            raw=response.read(4_000_001)
        if len(raw)>4_000_000:
            raise Blocked("Google audio response too large")
        decoded=json.loads(raw)
        audio=base64.b64decode(decoded["audioContent"],validate=True)
        if len(audio)<100:
            raise Blocked("Empty Google TTS audio")
        Path(output).parent.mkdir(parents=True,exist_ok=True)
        Path(output).write_bytes(audio)
        return Path(output)
    except (KeyError,ValueError,OSError) as exc:
        raise Blocked("Google TTS failed; no audio written") from exc

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--backend",choices=("offline-demo","google-cloud"),default="offline-demo")
    p.add_argument("--text",default=DEFAULT_TEXT)
    p.add_argument("--output",default="output/washing-machines-hi.mp3")
    args=p.parse_args(argv)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    if args.backend=="offline-demo":
        local_demo(args.text,output)
    else:
        google_cloud_mp3(args.text,output)
    print(json.dumps({"audio_path":str(output),"backend":args.backend,
       "approved_natural_hindi":False,"publishing_enabled":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
