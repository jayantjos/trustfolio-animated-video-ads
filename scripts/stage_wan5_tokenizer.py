#!/usr/bin/env python3
"""Stage ONLY the 4 missing official Wan2.2 tokenizer files to existing S3 volume.

No GPU Pod and no network-volume administration. Pin upstream revision,
bound file sizes, verify known large-file SHA256 and S3 readback. Do not touch
checkpoint shards or previously verified objects.
"""
import hashlib
import json
import os
from urllib.request import Request, urlopen
from botocore.config import Config

REV="921dbaf3f1674a56f47e83fb80a34bac8a8f203e"
MODEL_PREFIX=f"models/Wan2.2-TI2V-5B/{REV}/google/umt5-xxl/"
SOURCE=f"https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B/resolve/{REV}/google/umt5-xxl/"
BUCKET="1bch597yrz"
TOKENIZER={
    "tokenizer.json":(17_500_000,"6e197b4d3dbd71da14b4eb255f4fa91c9c1f2068b20a2de2472967ca3d22602b"),
    "spiece.model":(4_800_000,"e3909a67b780650b35cf529ac782ad2b6b26e6d1f849d3fbb6a872905f452458"),
    "tokenizer_config.json":(150_000,None),
    "special_tokens_map.json":(30_000,None),
}

def get_s3():
    import boto3
    key=os.environ.get("RUNPOD_S3_ACCESS_KEY_ID")
    secret=os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY")
    if not key or not secret:
        raise RuntimeError("S3_TOKEN_MISSING")
    return boto3.client("s3",region_name="eu-ro-1",
        endpoint_url="https://s3api-eu-ro-1.runpod.io",
        aws_access_key_id=key,aws_secret_access_key=secret,
        config=Config(signature_version="s3v4",
                      s3={"addressing_style":"path"},
                      connect_timeout=20,read_timeout=90))

def download_verified(name,max_bytes,expected_sha):
    if name not in TOKENIZER:
        raise ValueError("UNAPPROVED_TOKENIZER_FILE")
    req=Request(SOURCE+name,headers={"User-Agent":"TrustFolio-Wan2.2-ReadOnlyTokenizerVerifier/1.0"})
    with urlopen(req,timeout=75) as response:
        value=response.read(max_bytes+1)
    if not value or len(value)>max_bytes:
        raise RuntimeError("TOKENIZER_DOWNLOAD_SIZE_INVALID_"+name)
    digest=hashlib.sha256(value).hexdigest()
    if expected_sha is not None and digest!=expected_sha:
        raise RuntimeError("OFFICIAL_TOKENIZER_SHA256_MISMATCH_"+name)
    if name.endswith(".json"):
        doc=json.loads(value)
        if not isinstance(doc,dict):
            raise RuntimeError("BAD_TOKENIZER_JSON_"+name)
    return value,digest

def readback_verified(s3,key,data):
    result=s3.get_object(Bucket=BUCKET,Key=key)
    stream=result["Body"]
    try:
        if int(result.get("ContentLength",-1))!=len(data):
            return False
        digest=hashlib.sha256()
        for part in iter(lambda:stream.read(1024*1024),b""):
            digest.update(part)
        return digest.hexdigest()==hashlib.sha256(data).hexdigest()
    finally:
        stream.close()

def stage(s3):
    records=[]
    for name,(max_bytes,expected_sha) in TOKENIZER.items():
        value,digest=download_verified(name,max_bytes,expected_sha)
        key=MODEL_PREFIX+name
        # Never overwrite an existing file that does not match the official revision.
        try:
            prior=s3.get_object(Bucket=BUCKET,Key=key)
        except Exception as exc:
            code=str(getattr(exc,"response",{}).get("Error",{}).get("Code",""))
            if code not in ("NoSuchKey","404","NotFound"):
                raise RuntimeError("S3_READ_ERROR_"+name) from None
            prior=None
        if prior:
            body=prior["Body"]
            try:
                previous=body.read(max_bytes+1)
            finally:
                body.close()
            if previous!=value:
                raise RuntimeError("TOKENIZER_EXISTING_MISMATCH_REFUSE_OVERWRITE_"+name)
            state="PRESENT_VERIFIED"
        else:
            s3.put_object(Bucket=BUCKET,Key=key,Body=value,ContentType=(
                "application/json" if name.endswith(".json") else "application/octet-stream"))
            state="STAGED_VERIFIED"
        if not readback_verified(s3,key,value):
            raise RuntimeError("TOKENIZER_S3_READBACK_MISMATCH_"+name)
        records.append({"name":name,"bytes":len(value),"sha256":digest,"status":state})
        print("WAN_TOKENIZER_FILE_VERIFIED="+name,flush=True)
    return records

def main():
    result={"model":REV,"status":"FAILED","gpu_pods_created":False,
            "network_volume_deleted":False,"files":[]}
    try:
        result["files"]=stage(get_s3())
        result["status"]="ALL_FOUR_OFFICIAL_TOKENIZER_FILES_S3_VERIFIED"
        return 0
    except Exception as exc:
        # No raw URL response, credentials, or file data in logs.
        print("WAN_TOKENIZER_STAGE_FAILURE_CLASS="+type(exc).__name__,flush=True)
        return 1
    finally:
        os.makedirs("output",exist_ok=True)
        with open("output/wan5-tokenizer-stage-receipt.json","w") as file:
            json.dump(result,file,indent=2)
        print("WAN_TOKENIZER_STAGE="+result["status"],flush=True)

if __name__=="__main__":
    raise SystemExit(main())
