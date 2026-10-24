#!/usr/bin/env python3
"""Read-only S3 connectivity test. Does not upload, delete, or provision resources."""
import json, os, sys
from pathlib import Path

CONFIG = "config/runpod_existing_volume.json"

def check_s3(bucket, endpoint, access_key, secret_key, client_factory=None):
    if not access_key or not secret_key:
        return "S3_NOT_CONFIGURED"
    if client_factory is None:
        import boto3
        from botocore.config import Config
        client_factory=lambda: boto3.client("s3",endpoint_url=endpoint,
            region_name="eu-ro-1",aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4",
                          s3={"addressing_style":"path"},
                          retries={"max_attempts":3,"mode":"standard"}))
    client=client_factory()
    result=client.list_objects_v2(Bucket=bucket,MaxKeys=1)
    if not isinstance(result,dict) or "ResponseMetadata" not in result:
        raise RuntimeError("INVALID_S3_RESULT")
    if result["ResponseMetadata"].get("HTTPStatusCode")!=200:
        raise RuntimeError("S3_NON_200_RESPONSE")
    return "S3_CONNECTED_READ_ONLY"

def main():
    settings=json.loads(Path(CONFIG).read_text())
    try:
        status=check_s3(settings["s3_bucket"],settings["s3_endpoint"],
            os.environ.get("RUNPOD_S3_ACCESS_KEY_ID",""),
            os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY",""))
    except Exception:
        # Never log SDK error or exception content: it may disclose request URLs/headers.
        print("RUNPOD_S3=S3_CONNECTION_FAILED_CHECK_CREDENTIALS")
        return 1
    print("RUNPOD_S3="+status)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
            f.write("RunPod S3 network-volume access: **"+status+"**\n")
            f.write("No object uploads/deletes or GPU creation were attempted.\n")
    return 0

if __name__=="__main__":
    sys.exit(main())
