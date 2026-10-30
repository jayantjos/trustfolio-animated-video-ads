#!/usr/bin/env python3
"""Strict verification of user-approved TrustFolio ZIP assets; no legacy media."""
import hashlib, json, sys, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MEDIA=ROOT/"assets/video/washing-machines"
KIT=MEDIA/"TrustFolio_Washing_Machine_Master_Kit.zip"
SOURCE=MEDIA/"complete washing machine.zip"
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def main():
    for x in (KIT,SOURCE):
        if not x.is_file() or x.stat().st_size<100000:raise SystemExit(f"MISSING_OR_EMPTY_APPROVED_ASSET: {x}")
    out={"schema":1,"source_policy":"assets/video/washing-machines/ ONLY","media":[],"status":"SOURCE_VERIFIED_NOT_RENDERED"}
    for archive in (SOURCE,KIT):
        with zipfile.ZipFile(archive) as z:
            bad=z.testzip()
            if bad:raise SystemExit(f"ZIP_CRC_FAILED: {bad}")
            names=[n for n in z.namelist() if not n.endswith("/")]
            if any(n.startswith("/") or ".." in Path(n).parts for n in names):raise SystemExit("UNSAFE_ZIP_PATH")
            videos=[n for n in names if n.lower().endswith(".mp4")]
            if not videos:raise SystemExit(f"ZIP_WITH_NO_VIDEO: {archive.name}")
            out["media"].append({"archive":archive.name,"sha256":sha(archive),"bytes":archive.stat().st_size,"mp4_files":len(videos),"paths":names})
    dst=ROOT/"handoff"
    dst.mkdir(exist_ok=True)
    (dst/"final_source_audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("FINAL_ASSETS_CRC_AND_INVENTORY_PASS; NO_LIVE_PRODUCT_OR_POST_CLAIM")
if __name__=="__main__":main()
