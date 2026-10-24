#!/usr/bin/env python3
"""GET-only verification that TrustFolio's approved network volume exists."""
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.runpod.io/v2/network-volumes/"
CONFIG = "config/runpod_existing_volume.json"

class VolumeError(RuntimeError):
    pass

def verify(config, key, opener=urlopen):
    expected = json.loads(Path(config).read_text(encoding="utf-8"))
    if not key or "\n" in key or "\r" in key:
        raise VolumeError("READ_ONLY_API_KEY_MISSING")
    vid = expected["id"]
    if not isinstance(vid, str) or not vid.isalnum() or len(vid) > 32:
        raise VolumeError("VOLUME_ID_INVALID")
    request = Request(BASE + vid, headers={
        "Authorization": "Bearer " + key, "Accept": "application/json"
    }, method="GET")
    try:
        with opener(request,timeout=25) as response:
            if response.status != 200:
                raise VolumeError("HTTP_" + str(response.status))
            raw=response.read(131073)
            if len(raw)>131072:
                raise VolumeError("RESPONSE_TOO_LARGE")
            result=json.loads(raw)
    except HTTPError as exc:
        raise VolumeError("HTTP_" + str(exc.code)) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise VolumeError("NETWORK_OR_PARSE_FAILED") from None
    if not isinstance(result,dict):
        raise VolumeError("INVALID_API_RESPONSE")
    for field, key2 in (("id","id"),("name","name"),("size","size_gb"),
                        ("dataCenter","datacenter"),("type","tier")):
        if result.get(field)!=expected[key2]:
            raise VolumeError("REGISTERED_VOLUME_MISMATCH_"+field.upper())
    return {"status":"VERIFIED_EXISTING_VOLUME","name":expected["name"],
            "volume_id":expected["id"],"size_gb":expected["size_gb"],
            "datacenter":expected["datacenter"],"tier":expected["tier"],
            "gpu_created":False,"new_volume_created":False}

def main():
    try:
        checked=verify(CONFIG,os.environ.get("RUNPOD_API_KEY",""))
        print("RUNPOD_VOLUME=" + checked["status"])
        print("SIZE_GB="+str(checked["size_gb"]))
        print("DATACENTER="+checked["datacenter"])
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
                f.write("Existing RunPod 100 GB EU-RO-1 network volume: **VERIFIED**\n")
        out=Path("output/existing-volume-verified.json")
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(checked,indent=2)+"\n")
    except (VolumeError,KeyError,TypeError) as exc:
        print("RUNPOD_VOLUME=BLOCKED_"+str(exc))
        return 1
    return 0

if __name__=="__main__":
    sys.exit(main())
