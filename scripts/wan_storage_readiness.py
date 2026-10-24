#!/usr/bin/env python3
"""Read-only S3 HEAD audit of all immutable Wan2.2 model objects.

Hashes were independently verified by GET at initial upload. HEAD can verify
size and presence but cannot re-hash the content. This check is NOT GPU inference.
"""
import json, os, sys
from pathlib import Path

MANIFEST="config/wan_verified_model_manifest.json"

def check_structure(m):
    assert m["model"]=="Wan-AI/Wan2.2-TI2V-5B"
    assert m["revision"]=="921dbaf3f1674a56f47e83fb80a34bac8a8f203e"
    s=m["storage"]
    assert s["bucket"]=="1bch597yrz" and s["region"]=="EU-RO-1"
    assert s["prefix"]=="models/Wan2.2-TI2V-5B/"+m["revision"]+"/"
    assert m["verified_transfer_receipts"] is True
    assert m["model_inference_completed"] is False
    objects=m["objects"]
    assert len(objects)==9 and len({x["name"] for x in objects})==9
    assert sum(x["bytes"] for x in objects)==m["expected_total_bytes"]==34180083066
    for obj in objects:
        assert obj["name"].replace("-","").replace("_","").replace(".","").isalnum()
        assert isinstance(obj["bytes"],int) and obj["bytes"]>0
        assert len(obj["sha256"])==64 and all(c in "0123456789abcdef" for c in obj["sha256"])
    return s

def check_remote(m, client):
    s=check_structure(m)
    status=[]
    for item in m["objects"]:
        key=s["prefix"]+item["name"]
        response=client.head_object(Bucket=s["bucket"],Key=key)
        if int(response["ContentLength"])!=item["bytes"]:
            raise ValueError("REMOTE_SIZE_MISMATCH:"+item["name"])
        status.append({"object":item["name"],"size_verified":True,"bytes":item["bytes"],
                       "sha256_verified_at_upload":item["sha256"]})
    return {
        "status":"ALL_9_FILES_PRESENT_WITH_EXPECTED_SIZES",
        "total_bytes":sum(item["bytes"] for item in status),
        "model_usable_by_inference":"NOT_YET_TESTED",
        "gpu_created":False,"publishing_enabled":False,
        "objects":status
    }

def main():
    try:
        m=json.loads(Path(MANIFEST).read_text())
        s=check_structure(m)
        import boto3
        from botocore.config import Config
        a=os.environ.get("RUNPOD_S3_ACCESS_KEY_ID","")
        b=os.environ.get("RUNPOD_S3_SECRET_ACCESS_KEY","")
        if not a or not b: raise ValueError("S3_SECRET_MISSING")
        client=boto3.client("s3",region_name="eu-ro-1",endpoint_url=s["endpoint"],
            aws_access_key_id=a,aws_secret_access_key=b,
            config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                          connect_timeout=20,read_timeout=60,retries={"max_attempts":3}))
        result=check_remote(m,client)
        out=Path("output/wan-storage-ready.json");out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(result,indent=2)+"\n")
        print("WAN_STORAGE_STATUS="+result["status"])
        print("WAN_TOTAL_VERIFIED_PRESENT_BYTES="+str(result["total_bytes"]))
        print("WAN_GPU_INFERENCE=NOT_TESTED")
        return 0
    except Exception:
        print("WAN_STORAGE_STATUS=FAILED_CHECK_ACTION_LOGS_AND_MANIFEST")
        return 1

if __name__=="__main__":sys.exit(main())
