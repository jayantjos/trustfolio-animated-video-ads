"""Approved source-art asset upload gate: no synthetic face substitutions."""
import hashlib,json,os,sys
from pathlib import Path
IMAGE="assets/characters/shared/pink_kurta_lady_v1.png"
EXPECTED="7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"
BUCKET="1bch597yrz"
def hash_image(path=IMAGE):
    p=Path(path)
    if not p.is_file():raise ValueError("ORIGINAL_APPROVED_PNG_NOT_IN_REPO")
    if p.stat().st_size!=2484010:raise ValueError("APPROVED_IMAGE_SIZE_MISMATCH")
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=EXPECTED:raise ValueError("APPROVED_IMAGE_SHA256_MISMATCH")
    return h
def main():
    try:
        digest=hash_image()
        import boto3
        from botocore.config import Config
        a=os.environ.get("RUNPOD_S3_ACCESS_KEY_ID","");b=os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY","")
        if not a or not b:raise ValueError("S3_SECRETS_MISSING")
        s3=boto3.client("s3",region_name="eu-ro-1",endpoint_url="https://s3api-eu-ro-1.runpod.io",aws_access_key_id=a,aws_secret_access_key=b,config=Config(signature_version="s3v4",s3={"addressing_style":"path"}))
        from botocore.exceptions import ClientError
        try:
            remote=s3.head_object(Bucket=BUCKET,Key=IMAGE)
        except ClientError as exc:
            if str(exc.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"): raise
            s3.upload_file(IMAGE,BUCKET,IMAGE,ExtraArgs={"ContentType":"image/png","Metadata":{"sha256":digest,"asset-role":"approved-pink-kurta-lead"}})
            remote=s3.head_object(Bucket=BUCKET,Key=IMAGE)
        if int(remote.get("ContentLength",0))!=2484010 or remote.get("Metadata",{}).get("sha256")!=digest:
            raise ValueError("REMOTE_APPROVED_IMAGE_NOT_MATCHED")
        report={"status":"APPROVED_SHARED_LEAD_UPLOADED_AND_S3_HEAD_VERIFIED","s3_key":IMAGE,"bucket":BUCKET,"sha256":digest,"gpu_started":False,"publishing_enabled":False}
        Path("output").mkdir(exist_ok=True)
        Path("output/approved-character-upload.json").write_text(json.dumps(report,indent=2)+"\n")
        print("TRUSTFOLIO_SHARED_CHARACTER="+report["status"])
        return 0
    except Exception:
        print("TRUSTFOLIO_SHARED_CHARACTER=BLOCKED_MISSING_MISMATCH_OR_S3_ERROR")
        return 1
if __name__=="__main__":sys.exit(main())
