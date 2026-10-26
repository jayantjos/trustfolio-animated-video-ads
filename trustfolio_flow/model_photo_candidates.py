"""Download proposed exact-model product photos for visual QA; never update website or publish.

Sources are external retailer/brand product pages explicitly bearing model IDs.
These are *proposals*, not replacements for TrustFolio live product evidence.
"""
from __future__ import annotations
import hashlib,json
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image

PHOTOS=[
  dict(rank=1,brand="IFB",model="TL800EP1S",
       source_page="https://aaravelectronics.com/products/ifb-tl800ep1s-top-load-washing-machine-8-kg-720-rpm-espresso",
       image_url="https://aaravelectronics.com/cdn/shop/files/tl-800ep1s-fv.webp?v=1766863542"),
  dict(rank=3,brand="Bosch",model="WOE703S0IN",
       source_page="https://www.croma.com/bosch-7-kg-5-star-fully-automatic-top-load-washing-machine-series-2-woe703s0in-expertcare-wash-system-silver-/p/247680",
       image_url="https://img-prd-pim.poorvika.com/cdn-cgi/image/width%3D500%2Cheight%3D500%2Cquality%3D75/product/37582-bosch-7-0-kg-fully-automatic-top-load-washing-machine-woe703s0in-silver-01.png",
       photo_source_page="https://www.poorvika.com/bosch-7-0-kg-fully-automatic-top-load-washing-machine-woe703s0in-silver/p"),
]

def main(directory="handoff/candidate_photos"):
    d=Path(directory);d.mkdir(parents=True,exist_ok=True)
    records=[]
    for p in PHOTOS:
        req=Request(p["image_url"],headers={"User-Agent":"TrustFolioSourcePhotoQA/1.0","Accept":"image/*"})
        with urlopen(req,timeout=30) as response:
            if response.status!=200 or not response.headers.get("Content-Type","").lower().startswith("image/"):
                raise ValueError("Not a successful image response")
            raw=response.read(5_000_001)
        if len(raw)>5_000_000: raise ValueError("Oversized image")
        with Image.open(BytesIO(raw)) as im:
            im.load()
            if min(im.size)<320: raise ValueError("Image too low resolution for QA")
            im=im.convert("RGBA")
            target=d/(f"candidate_product_{p['rank']:02d}_{p['model']}.png")
            im.save(target)
        records.append({**p,"width":im.width,"height":im.height,
          "original_sha256":hashlib.sha256(raw).hexdigest(),
          "qa_status":"CANDIDATE_MODEL_MATCH_NOT_REVIEWED","approved_for_publishing":False,
          "file":target.name})
        print("CANDIDATE_DOWNLOADED="+p["model"]+" "+str(im.size))
    (d/"candidate_photo_evidence.json").write_text(json.dumps(
      {"source":"third_party_model_specific_product_pages","publishable":False,
       "note":"Must confirm actual TrustFolio product URL/model ID and rights before commercial use. Does NOT modify website DB or correct source mapping.", 
       "candidates":records},indent=2)+"\n")
    print("NO_WEBSITE_DB_CHANGE=YES; NO_PUBLISH=YES")
if __name__=="__main__": main()
