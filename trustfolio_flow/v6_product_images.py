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

def make_cutout(rgba):
    """Conservative connected-edge near-white removal. No generative model.

    A photograph with patterned/dark background stays opaque and is rejected
    downstream until an approved transparent product asset is supplied.
    Actual silhouette and commercial rights still need one-time manual QA.
    """
    from collections import deque
    from PIL import Image
    im=rgba.copy().convert("RGBA")
    w,h=im.size
    # Process no more than ~2 million pixels; no high-cost untrusted giant masks.
    if w*h>2_500_000:
        im.thumbnail((1400,1400),Image.Resampling.LANCZOS)
        w,h=im.size
    pix=im.load()
    def near_white(x,y):
        r,g,b,a=pix[x,y]
        return a>0 and min(r,g,b)>=246 and max(r,g,b)-min(r,g,b)<=8
    border=[(x,0) for x in range(w)]+[(x,h-1) for x in range(w)]
    border +=[(0,y) for y in range(1,h-1)]+[(w-1,y) for y in range(1,h-1)]
    white=sum(near_white(x,y) for x,y in border)
    if white/max(1,len(border))<.74:
        return im,False
    q=deque((x,y) for x,y in border if near_white(x,y))
    seen=bytearray(w*h)
    while q:
        x,y=q.popleft();index=y*w+x
        if seen[index]:continue
        seen[index]=1
        if not near_white(x,y):continue
        r,g,b,_=pix[x,y];pix[x,y]=(r,g,b,0)
        for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0<=xx<w and 0<=yy<h and not seen[yy*w+xx]:
                q.append((xx,yy))
    if im.getchannel("A").getextrema()==(255,255):
        return im,False
    return im,True

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
            rgba,cutout_ok=make_cutout(rgba)
            if not cutout_ok and rgba.getchannel("A").getextrema()==(255,255):
                raise DataBlocked("No safe transparent photo silhouette; manual model cutout required")
            path=folder/("rank_%02d.png"%p["rank"])
            rgba.save(path)
            entries.append({"rank":p["rank"],"id":p["id"],"brand":p["brand"],
                  "image_url":p["image_url"],"image_sha256":sha256(path.read_bytes()).hexdigest(),
                  "original_sha256":digest,"source_size":original_size,"file":path.name,
                  "edge_white_cutout_performed":cutout_ok,
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
