"""Download ONLY TrustFolio-verified retailer images as Flow reference ingredients.

Never use arbitrary product URLs, redirects, or private network addresses.
"""
from pathlib import Path
from urllib.request import Request, build_opener
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from hashlib import sha256
import json
from .live import NoRedirect, DataBlocked
from .site_display import check_flow_receipt

MAX_IMAGE_BYTES=8_000_000


def fetch_ingredients(receipt, folder, *, opener=None):
    check_flow_receipt(receipt)
    # Retailer data may contain a WRONG reused image. The ₹25k snapshot
    # gave identical Flipkart source image URLs to IFB #1 and Bosch #3.
    # Reject cross-brand duplicates BEFORE downloading any image ingredient.
    owners={}
    for p in receipt['products']:
        url=p['image_url']
        old=owners.get(url)
        if old is not None and old['brand'].casefold()!=p['brand'].casefold():
            raise DataBlocked(
                f"PRODUCT_REFERENCE_CROSS_BRAND_DUPLICATE: rank {old['rank']} {old['brand']} "
                f"and rank {p['rank']} {p['brand']} share identical URL; no Flow generation"
            )
        owners[url]=p
    opener=opener or build_opener(NoRedirect()).open
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    outputs=[]
    raw_owners={}
    evidence=[]
    for p in receipt['products']:
        url=p['image_url']
        try:
            with opener(Request(url,headers={'User-Agent':'TrustFolioFlowAssets/1.0','Accept':'image/*'}),timeout=25) as r:
                if r.status!=200 or not r.headers.get('Content-Type','').startswith('image/'):
                    raise DataBlocked('Retailer product image could not be fetched')
                raw=r.read(MAX_IMAGE_BYTES+1)
            if len(raw)>MAX_IMAGE_BYTES:
                raise DataBlocked('Oversize retailer image')
            digest=sha256(raw).hexdigest()
            old=raw_owners.get(digest)
            if old and old['brand'].casefold()!=p['brand'].casefold():
                raise DataBlocked(
                    f"PRODUCT_REFERENCE_CROSS_BRAND_DUPLICATE_BYTES: "
                    f"rank {old['rank']} {old['brand']} and rank {p['rank']} {p['brand']}"
                )
            raw_owners[digest]=p
            with Image.open(BytesIO(raw)) as original:
                original.load()
                if original.width>8000 or original.height>8000 or original.width<64 or original.height<64:
                    raise DataBlocked('Bad product image dimensions')
                original_size=(original.width,original.height)
                if min(original_size)<500:
                    quality_warning='LOW_SOURCE_RESOLUTION_FOR_PREMIUM_HD'
                else:
                    quality_warning=None
                evidence.append({'rank':p['rank'],'brand':p['brand'],
                                 'source_sha256':digest,'source_dimensions':original_size,
                                 'quality_warning':quality_warning})
                im=original.convert('RGBA');im.thumbnail((1400,1400))
                canvas=Image.new('RGBA',(1400,1400),(255,255,255,255))
                canvas.alpha_composite(im,((1400-im.width)//2,(1400-im.height)//2))
                target=folder/f'product_{p["rank"]:02d}.png'
                canvas.convert('RGB').save(target)
                outputs.append(target)
        except (OSError,UnidentifiedImageError) as e:
            raise DataBlocked('Product image fetch / decode failed; clip withheld') from e
    (folder/'ingredient_qa.json').write_text(json.dumps({
       'status':'SOURCE_URL_CHECKED_NOT_MODEL_ACCURACY_APPROVED',
       'publishable':False,'products':evidence,
       'warning':'Check title/photo actual model correspondence before any premium Flow edit.'
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return outputs
