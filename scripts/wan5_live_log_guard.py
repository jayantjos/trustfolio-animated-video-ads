#!/usr/bin/env python3
"""Fail-closed RunPod container-log watchdog for the one private WAN5 pilot.

Never logs raw RunPod messages, credentials or prompts. Never creates/deletes
Pods; the exact-owned controller performs deletion in its finally block.
"""
import json
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

POD_ID = re.compile(r"^[A-Za-z0-9_-]{5,80}$")
FATALS = (
    ("MISSING_DEPENDENCY", ("modulenotfounderror:", "importerror:")),
    ("GPU_OOM", ("cuda out of memory", "outofmemoryerror", "cublas_status_alloc_failed")),
    ("FATAL_RUNTIME", ("runtimeerror:", "filenotfounderror:", "assertionerror:",
                       "segmentation fault", "illegal memory access", "fatal python error")),
    ("WORKER_BLOCKED", ("trustfolio_wan5=blocked_",)),
    ("MODEL_FAILURE", ("safetensorerror:", "unpicklingerror:", "load_state_dict error")),
)


def fatal_classification(line):
    """Return safe classification only; do not report the underlying raw log."""
    low = str(line).lower()
    for kind, patterns in FATALS:
        if any(pattern in low for pattern in patterns):
            return kind
    return None


def _event_line(value):
    if isinstance(value, str):
        if value.startswith("data:"):
            return _event_line(value[5:].strip())
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value[:500]
        return _event_line(parsed)
    if isinstance(value, dict):
        for key in ("line", "message", "log", "data", "text"):
            if key in value:
                return _event_line(value[key])
    return ""


def scan_container_logs(api_key, pod_id, opener=urlopen, now=time.monotonic):
    """Read at most 120 SSE events with a short wall-clock/network bound.

    Startup 404/empty events or network failures are UNAVAILABLE (not
    HEALTHY); controller terminates if sustained during its grace window.
    """
    if not api_key or "\n" in api_key or "\r" in api_key:
        raise ValueError("BAD_READ_KEY")
    if not POD_ID.fullmatch(str(pod_id)):
        raise ValueError("BAD_POD_ID")
    url = ("https://api.runpod.io/v2/pods/" + pod_id + "/logs?"
           + urlencode({"tail": 100, "source": "container"}))
    req = Request(url, method="GET",
                  headers={"Authorization": "Bearer " + api_key,
                           "Accept": "text/event-stream"})
    try:
        with opener(req, timeout=5) as response:
            deadline = now() + 3.0
            seen = 0
            while seen < 120 and now() < deadline:
                try:
                    raw = response.readline(4096)
                except (socket.timeout, TimeoutError):
                    break
                if not raw:
                    break
                if not raw.startswith(b"data:"):
                    continue
                seen += 1
                message = _event_line(raw.decode("utf-8", "replace").strip())
                classification = fatal_classification(message)
                if classification:
                    return {"available": True, "events": seen,
                            "fatal": classification}
            return {"available": bool(seen), "events": seen, "fatal": None}
    except (HTTPError, URLError, OSError, TimeoutError, ValueError):
        return {"available": False, "events": 0, "fatal": None}
