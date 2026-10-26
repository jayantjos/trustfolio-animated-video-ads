"""Download ONLY TrustFolio-verified retailer images as Flow reference ingredients.

Never use arbitrary product URLs, redirects, or private network addresses.
"""
from pathlib import Path
from urllib.request import Request, build_opener
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from .live import NoRedirect, DataBlocked
from .site_display import check_flow_receipt

MAX_IMAGE_BYTES=8_000_000


def fetch_ingredients(receipt, folder, *, opener=None):
    check_flow_receipt(receipt)
    opener=opener or build_opener(NoRedirect()).open
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for p in receipt['products']:
        url=p['image_url']
        try:
            with opener(Request(url,headers={'User-Agent':'TrustFolioFlowAssets/1.0','Accept':'image/*'}),timeout=25) as r:
                if r.status!=200 or not r.headers.get('Content-Type','').startswith('image/'):
                    raise DataBlocked('Retailer product image could not be fetched')
                raw=r.read(MAX_IMAGE_BYTES+1)
            if len(raw)>MAX_IMAGE_BYTES:
                raise DataBlocked('Oversize retailer image')
            with Image.open(BytesIO(raw)) as original:
                original.load()
                if original.width>8000 or original.height>8000 or original.width<64 or original.height<64:
                    raise DataBlocked('Bad product image dimensions')
                im=original.convert('RGBA');im.thumbnail((1400,1400))
                canvas=Image.new('RGBA',(1400,1400),(255,255,255,255))
                canvas.alpha_composite(im,((1400-im.width)//2,(1400-im.height)//2))
                target=folder/f'product_{p["rank"]:02d}.png'
                canvas.convert('RGB').save(target)
                outputs.append(target)
        except (OSError,UnidentifiedImageError) as e:
            raise DataBlocked('Product image fetch / decode failed; clip withheld') from e
    return outputs
