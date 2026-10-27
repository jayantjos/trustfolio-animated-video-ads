"""Read-only five-product artwork ingestion for premium Reels.

Does not approve model identity. Cross-brand photo collisions, redirects,
low resolution and invalid source hosts cause a fail-closed campaign skip.
"""
from __future__ import annotations
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from urllib.request import Request, build_opener
from PIL import Image, UnidentifiedImageError
from .live import check_receipt,NoRedirect,DataBlocked

MAX_BYTES=8_000_000
MIN_SIDE=350

def acquire_five(receipt,folder,*,opener=None,now=None):
    check_receipt(receipt,now=now)
    products=receipt["products"]
    url_owners={}
    for p in products:
        old=url_owners.get(p["image_url"])
        if old and old["brand"].casefold()!=p["brand"].casefold():
            raise DataBlocked("CROSS_BRAND_SOURCE_PHOTO_URL: rank %d and %d"%(old["rank"],p["rank"]))
        url_owners[p["image_url"]]=p
    op=opener or build_opener(NoRedirect()).open
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    byhash={};entries=[]
    for p in products:
        try:
            request=Request(p["image_url"],headers={"User-Agent":"TrustFolioPremiumSourcePhotoQA/1.0","Accept":"image/*"})
            with op(request,timeout=30) as res:
                if res.status!=200 or not res.headers.get("Content-Type","").lower().startswith("image/"):
                    raise DataBlocked("Product image source HTTP status/format invalid")
                raw=res.read(MAX_BYTES+1)
            if not raw or len(raw)>MAX_BYTES:raise DataBlocked("Invalid image response size")
            with Image.open(BytesIO(raw)) as im:
                im.load()
                if min(im.size)<MIN_SIDE or max(im.size)>8000:
                    raise DataBlocked("Premium product source picture too small/large")
                rgba=im.convert("RGBA")
                original_size=list(im.size)
            digest=sha256(raw).hexdigest()
            owner=byhash.get(digest)
            if owner and owner["brand"].casefold()!=p["brand"].casefold():
                raise DataBlocked("CROSS_BRAND_SOURCE_PHOTO_BYTES")
            byhash[digest]=p
            path=folder/("rank_%02d.png"%p["rank"])
            rgba.save(path)
            entries.append({"rank":p["rank"],"id":p["id"],"brand":p["brand"],
                  "image_url":p["image_url"],"image_sha256":sha256(path.read_bytes()).hexdigest(),
                  "original_sha256":digest,"source_size":original_size,"file":path.name,
                  "model_identity_ok":False,"product_photo_ok":False,"commercial_usage_ok":False,
                  "review_note":"Correct model photo and commercial use MUST be approved before real Reel render"})
        except (OSError,ValueError,UnidentifiedImageError) as exc:
            raise DataBlocked("Product image acquisition or decode failed; no Reel") from exc
    manifest={"source_receipt_sha256":receipt["snapshot_sha256"],"status":"PENDING_MANUAL_PRODUCT_MODEL_QA",
              "publication_approved":False,"products":entries}
    (folder/"photo_review_pending.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("FIVE_SOURCE_PRODUCT_IMAGES_DOWNLOADED_BUT_NOT_APPROVED=YES")
    return manifest

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",required=True)
    p.add_argument("--outdir",required=True)
    a=p.parse_args()
    r=json.loads(Path(a.receipt).read_text(encoding="utf8"))
    acquire_five(r,a.outdir)

if __name__=="__main__":main()
