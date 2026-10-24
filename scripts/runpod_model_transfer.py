#!/usr/bin/env python3
"""Stream immutable Hugging Face Wan2.2 weights directly into RunPod S3.

No GPU and no local multi-GB downloads. Use only approved one-at-a-time files.
Existing objects are never overwritten; remote SHA256 is verified by streaming GET.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO = "Wan-AI/Wan2.2-TI2V-5B"
REV = "921dbaf3f1674a56f47e83fb80a34bac8a8f203e"
BUCKET = "1bch597yrz"
ENDPOINT = "https://s3api-eu-ro-1.runpod.io"
PREFIX = "models/Wan2.2-TI2V-5B/" + REV + "/"
MIB = 1024 * 1024
MAX_OBJECT_BYTES = 12 * 1024 * 1024 * 1024
ALLOW = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,100}$")
ALLOWED_EXT = (".pth", ".safetensors", ".json", ".md")

class Blocked(RuntimeError):
    pass

def select_file(info, name):
    if not ALLOW.fullmatch(name) or not name.endswith(ALLOWED_EXT):
        raise Blocked("FILE_NOT_ALLOWED")
    if info.sha != REV:
        raise Blocked("MODEL_REVISION_CHANGED")
    sibling = next((x for x in info.siblings if x.rfilename == name), None)
    if sibling is None or sibling.size is None or not (0 < sibling.size <= MAX_OBJECT_BYTES):
        raise Blocked("FILE_MISSING_OR_UNSUPPORTED_SIZE")
    lfs = getattr(sibling, "lfs", None) or {}
    sha = lfs.get("sha256")
    if sha is not None and not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise Blocked("SOURCE_LFS_SHA_INVALID")
    if name.endswith((".pth", ".safetensors")) and not sha:
        raise Blocked("WEIGHT_MISSING_SOURCE_SHA")
    return {"name":name,"size":sibling.size,"lfs_sha256":sha,
            "revision":REV,"repository":REPO,"s3_key":PREFIX+name}

def make_s3():
    import boto3
    from botocore.config import Config
    if not (os.environ.get("RUNPOD_S3_ACCESS_KEY_ID") and os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY")):
        raise Blocked("S3_CREDENTIALS_NOT_CONFIGURED")
    return boto3.client("s3",region_name="eu-ro-1",endpoint_url=ENDPOINT,
      aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY_ID"],
      aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_ACCESS_KEY"],
      config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                    connect_timeout=30,read_timeout=7200,retries={"max_attempts":8,"mode":"standard"}))

class HashReader:
    def __init__(self, raw):
        self.raw=raw
        self.sha=hashlib.sha256()
        self.count=0
    def read(self, size=-1):
        block=self.raw.read(size)
        if block:
            self.sha.update(block)
            self.count+=len(block)
            if self.count>MAX_OBJECT_BYTES:
                raise Blocked("TRANSFER_EXCEEDS_FILE_CAP")
        return block

def remote_sha(client,key, expected_size):
    response=client.get_object(Bucket=BUCKET,Key=key)
    try:
        if response["ContentLength"]!=expected_size:
            raise Blocked("REMOTE_SIZE_MISMATCH")
        stream=response["Body"]
        digest=hashlib.sha256()
        count=0
        while True:
            block=stream.read(4*MIB)
            if not block: break
            digest.update(block)
            count+=len(block)
            if count>MAX_OBJECT_BYTES: raise Blocked("REMOTE_READ_EXCEEDS_LIMIT")
        if count!=expected_size: raise Blocked("REMOTE_SHORT_READ")
        return digest.hexdigest()
    finally:
        response["Body"].close()

def s3_exists(client,key):
    from botocore.exceptions import ClientError
    try:
        result=client.head_object(Bucket=BUCKET,Key=key)
        return int(result["ContentLength"])
    except ClientError as exc:
        code=str(exc.response.get("Error",{}).get("Code",""))
        if code in ("404","NoSuchKey","NotFound"):
            return None
        raise Blocked("S3_HEAD_REJECTED") from None

def upload(model,client,session,*,dry_run=False):
    name,size,key=model["name"],model["size"],model["s3_key"]
    src_sha=model["lfs_sha256"]
    if dry_run:
        return {"name":name,"status":"PREPARED_NOT_UPLOADED","bytes":size,"source_sha":src_sha}
    old=s3_exists(client,key)
    if old is not None:
        if old!=size: raise Blocked("EXISTING_OBJECT_WRONG_SIZE")
        existing_sha=remote_sha(client,key,size)
        if src_sha and existing_sha!=src_sha:
            raise Blocked("EXISTING_OBJECT_WRONG_SHA_NO_OVERWRITE")
        return {"name":name,"status":"ALREADY_PRESENT_VERIFIED",
                "bytes":size,"sha256":existing_sha}
    # Requests streaming: follow vetted Hugging Face signed CDN redirects.
    from huggingface_hub import hf_hub_url
    from boto3.s3.transfer import TransferConfig
    url=hf_hub_url(repo_id=REPO,filename=name,revision=REV)
    if not url.startswith("https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B/resolve/"+REV+"/"):
        raise Blocked("UPSTREAM_URL_MISMATCH")
    with session.get(url,stream=True,timeout=(30,900)) as response:
        response.raise_for_status()
        response.raw.decode_content=True
        reader=HashReader(response.raw)
        client.upload_fileobj(reader,BUCKET,key,
          Config=TransferConfig(multipart_threshold=64*MIB,multipart_chunksize=64*MIB,
                                max_concurrency=1,use_threads=False))
        if reader.count!=size:
            raise Blocked("SOURCE_TRANSFER_SIZE_MISMATCH")
        source_digest=reader.sha.hexdigest()
        if src_sha and source_digest!=src_sha:
            raise Blocked("SOURCE_SHA256_MISMATCH")
    length=s3_exists(client,key)
    if length!=size: raise Blocked("S3_OBJECT_SIZE_MISMATCH")
    verified=remote_sha(client,key,size)
    if verified!=source_digest:raise Blocked("S3_RETURNED_SHA_MISMATCH")
    return {"name":name,"status":"UPLOADED_AND_VERIFIED","bytes":size,"sha256":verified}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--file",default="config.json")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--report-dir",default="output/model-transfers")
    args=parser.parse_args(argv)
    try:
        import requests
        from huggingface_hub import HfApi
        info=HfApi().model_info(repo_id=REPO,revision=REV,files_metadata=True)
        meta=select_file(info,args.file)
        client=None if args.dry_run else make_s3()
        with requests.Session() as session:
            result=upload(meta,client,session,dry_run=args.dry_run)
        output=Path(args.report_dir)
        output.mkdir(parents=True,exist_ok=True)
        (output/(args.file+".json")).write_text(json.dumps({
          "repository":REPO,"revision":REV,"volume_id":BUCKET,
          "object_key":meta["s3_key"],**result
        },indent=2)+"\n")
        print("WAN_MODEL_TRANSFER="+result["status"])
        print("WAN_FILE="+args.file)
        print("WAN_SIZE_BYTES="+str(meta["size"]))
        print("WAN_REMOTE_SHA256="+str(result.get("sha256","PENDING")))
        return 0
    except Exception as exc:
        # Intentionally do not output SDK/HF exceptions, URLs or headers.
        print("WAN_MODEL_TRANSFER=FAILED")
        print("WAN_ERROR_CATEGORY="+("BLOCKED_"+str(exc) if isinstance(exc,Blocked)
                                    else "NETWORK_OR_SERVICE_FAILURE"))
        return 1

if __name__=="__main__":
    sys.exit(main())
