"""Safe real-product asset selection for a private nonpublishable Remotion demo."""
from __future__ import annotations
import argparse
import json
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from io import BytesIO
from PIL import Image, ImageOps
from trustfolio_video.demo import approve_historical_demo
from trustfolio_video.educational import build_educational_story

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=[
    ("अरे! कपड़ों का पहाड़! दोस्तों, तैयार?", "hf_alpha", 0.4, 4.0),
    ("पाँचवाँ दोस्त आया! बबल पार्टी!", "hm_omega", 4.2, 7.6),
    ("चौथा बोला, ज़रा घूमो भाई!", "hf_alpha", 7.8, 11.3),
    ("तीसरे की एंट्री! मेरी बारी?", "hm_omega", 11.5, 15.0),
    ("दूसरे दोस्त का स्टाइल देखो!", "hf_alpha", 15.2, 18.8),
    ("और अब, ट्रस्टफ़ोलियो का नंबर वन!", "hm_omega", 19.0, 24.0),
    ("असली पाँच प्रोडक्ट्स। तुलना करो ट्रस्टफ़ोलियो पर!", "hf_alpha", 24.2, 29.7),
]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot',default='evidence/washing-machines-snapshot.json')
    parser.add_argument('--output',default='premium/public')
    args=parser.parse_args()
    snap=json.loads(Path(args.snapshot).read_text('utf-8'))
    demo=approve_historical_demo(snap)
    spec=demo['campaign']
    if spec['category']!='washing-machines' or spec['mode']!='budget' or spec['budget']!=35000:
        raise ValueError('Premium pilot accepts only pinned source category/budget/mode')
    # Education is always sourced from the same hashed genuine backend snapshot.
    educational=build_educational_story(demo)
    if educational["ranked_source_ids"]!=[p["id"] for p in demo["products"]]:
        raise ValueError("Education/ranking source identity mismatch")
    by_id={p["product_id"]:p for p in educational["expanded_product_explanations"]}
    root=Path(args.output)
    pictures=root/'products'
    pictures.mkdir(parents=True,exist_ok=True)
    output=[]
    for product in demo['products']:
        rank=int(product['rank'])
        url=str(product['main_image'])
        host=urlsplit(url).hostname
        if host not in ('media.tatacroma.com','m.media-amazon.com','images-na.ssl-images-amazon.com',
                        'rukminim1.flixcart.com','rukminim2.flixcart.com'):
            raise ValueError('Blocked product image host')
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 TrustFolioPremiumQA/1.0','Accept':'image/*'})
        with urlopen(req,timeout=40) as response:
            if not response.headers.get('Content-Type','').lower().startswith('image/'):
                raise ValueError('Refuse non-image product response')
            raw=response.read(3_000_001)
        if len(raw)>3_000_000:raise ValueError('Image oversized')
        with Image.open(BytesIO(raw)) as im:
            im.load()
            if not 75<=im.width<=5000 or not 75<=im.height<=5000:
                raise ValueError('Image dimensions suspicious')
            canvas=Image.new('RGBA',(520,540),(0,0,0,0))
            thumb=ImageOps.contain(im.convert('RGB'),(500,510),Image.Resampling.LANCZOS)
            canvas.paste(thumb,((520-thumb.width)//2,(540-thumb.height)//2))
            canvas.save(pictures/f'{rank}.png')
        name=product['title']
        brand=str(product.get('brand') or '').strip()
        shown=' '.join(name.split()[:6])
        if len(shown)>48:shown=shown[:45].rstrip()+'…'
        explanation=by_id[product['id']]
        facts=explanation['verified_specs']
        # The card reads only literal specification data, never from title parsing.
        featured=facts[(5-rank)%len(facts)] if facts else None
        output.append({
          'id':product['id'],'rank':rank,'name':shown,'fullTitle':name,
          'brand':brand,'price':int(product['price_inr']),
          'platform':product['platform'],'image':'products/'+str(rank)+'.png',
          'sha256':hashlib.sha256(raw).hexdigest(),
          'priceSource':product.get('price_source','unknown'),
          'livePriceStatus':product.get('live_price_status'),
          'educationFact':(
              {'label':featured['field'],'value':featured['value'],
               'sourceProductId':featured['source_product_id'],
               'sourceKey':featured['field']}
              if featured else None),
          'verifiedFacts':facts,
          'rankExplanation':explanation['why_ranked'],
          'productPurpose':explanation['what_it_does']
        })
    data={
      'status':'HISTORICAL_DEMO_NOT_FOR_PUBLICATION',
      'publishing_enabled':False,
      'category':spec['category'],
      'budget':spec['budget'],
      'world':'Premium Bubble Kingdom',
      'sourceSha256':demo['source_sha256'],
      'sourceObservedAt':demo['source_observed_at'],
      'rankedProductIds':[x['id'] for x in output],
      'products':output,
      'educationalStoryId':educational['campaign_id'],
      'educationalStorySourceSha256':educational['source_sha256'],
      'educationGuidance':{
        'productRole':educational['education_role'],
        'whyBestRule':'Recorded TrustFolio rank only; source scoring reasons unavailable',
        'exampleUserNeeds':educational['expanded_product_explanations'][0]['possible_user_needs'],
      },
      'lines':[{'text':text,'voice':voice,'start':start,'end':end}
               for text,voice,start,end in SCRIPTS],
      'durationInFrames':30*24,
      'fps':24,
      'watermark':'CONCEPT DEMO • HISTORICAL PRICES • NOT FOR PUBLICATION',
    }
    if [p['rank'] for p in output]!=[1,2,3,4,5]:
        raise ValueError('Invalid source rank mapping')
    (root/'story.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'educational-story.json').write_text(json.dumps(educational,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PREMIUM_PILOT_SOURCE_IDS='+','.join(data['rankedProductIds']))
    print('ORIGINAL_PRODUCT_IMAGES=5')
    print('SOURCE_IS_HISTORICAL_DEMO=true')

if __name__=='__main__':
    main()
