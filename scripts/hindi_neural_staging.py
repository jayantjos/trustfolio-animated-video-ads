"""CPU-only Hindi female neural audio test; never claims lip-sync or publishing."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
CFG="config/hindi_neural_clips.json"
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def main():
    cfg=json.loads(Path(CFG).read_text())
    assert cfg["category"]=="washing-machines" and cfg["gpu_enabled"] is False and cfg["publishing_enabled"] is False
    assert cfg["status"]=="NEEDS_LISTENING_QA" and len(cfg["clips"])==3
    model=Path("output/indus-pocket-tts/speak.py")
    if not model.is_file(): raise RuntimeError("Hindi PocketTTS source missing")
    out=Path("output/hindi-neural-pilot");out.mkdir(parents=True,exist_ok=True)
    import boto3
    from botocore.config import Config
    a=os.environ["RUNPOD_S3_ACCESS_KEY_ID"];b=os.environ["RUNPOD_S3_SECRET_ACCESS_KEY"]
    s3=boto3.client("s3",endpoint_url="https://s3api-eu-ro-1.runpod.io",region_name="eu-ro-1",aws_access_key_id=a,aws_secret_access_key=b,config=Config(signature_version="s3v4",s3={"addressing_style":"path"}))
    report=[]
    for item in cfg["clips"]:
        name=item["id"];wav=out/(name+".wav");mp3=out/(name+".mp3")
        subprocess.run([sys.executable,str(model),item["text"],str(wav),"--int8"],check=True,timeout=300)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(wav),"-codec:a","libmp3lame","-qscale:a","3",str(mp3)],check=True,timeout=60)
        if mp3.stat().st_size<3000: raise RuntimeError("MP3 QA failed")
        digest=sha(mp3); key="assets/audio/washing-machines/hindi_neural_v1/"+name+".mp3"
        from botocore.exceptions import ClientError
        try:
            current=s3.head_object(Bucket="1bch597yrz",Key=key)
        except ClientError as e:
            if str(e.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):raise
            s3.upload_file(str(mp3),"1bch597yrz",key,ExtraArgs={"ContentType":"audio/mpeg","Metadata":{"sha256":digest}})
            current=s3.head_object(Bucket="1bch597yrz",Key=key)
        if current["ContentLength"]!=mp3.stat().st_size or current.get("Metadata",{}).get("sha256")!=digest:
            raise RuntimeError("Existing audio or uploaded copy differs, refusing overwrite")
        report.append({"id":name,"sha256":digest,"bytes":mp3.stat().st_size,"s3_key":key,"status":"S3_HEAD_VERIFIED_PENDING_HUMAN_LISTENING_QA"})
        wav.unlink(missing_ok=True)
    (out/"qa.json").write_text(json.dumps({"model":cfg["engine"],"license":"CC-BY-4.0","credits_required":True,"clips":report,"lip_sync":False,"publishing":False},ensure_ascii=False,indent=2)+"\n")
    print("HINDI_NEURAL_CLIPS_STAGED="+str(len(report)))
    return 0
if __name__=="__main__":sys.exit(main())
