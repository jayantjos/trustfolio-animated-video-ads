#!/usr/bin/env python3
"""Strictly read-only RunPod API credential check, no GPU/volume creation.

Never print tokens, response bodies, resource IDs, environment variables, or usernames.
"""
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.runpod.io/v2"
ENDPOINTS = (("PODS", "/pods"), ("NETWORK_VOLUMES", "/network-volumes"))


def verify(key, opener=urlopen):
    if not key or "\n" in key or "\r" in key:
        return 2, "MISSING_OR_INVALID_KEY"
    for label, endpoint in ENDPOINTS:
        request = Request(BASE + endpoint, headers={
            "Authorization": "Bearer " + key,
            "Accept": "application/json",
        }, method="GET")
        try:
            with opener(request, timeout=20) as response:
                status = response.status
                if status != 200:
                    return 1, label + "_HTTP_" + str(status)
                # Small bound: don't dump account records.
                data = json.loads(response.read(1000001))
                if not isinstance(data, dict):
                    return 1, label + "_INVALID_JSON"
        except HTTPError as exc:
            return 1, label + "_HTTP_" + str(exc.code)
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return 1, label + "_REQUEST_ERROR"
    return 0, "READ_ONLY_CONNECTED"


def main():
    code, status = verify(os.environ.get("RUNPOD_API_KEY", ""))
    print("RUNPOD_CONNECTION=" + status)
    output = os.environ.get("GITHUB_STEP_SUMMARY")
    if output:
        with open(output, "a", encoding="utf-8") as file:
            file.write("RunPod read-only connection: **" + status + "**\\n")
            file.write("No GPU instance or storage volume was created, changed, or deleted.\\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
