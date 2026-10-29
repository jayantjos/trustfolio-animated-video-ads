#!/usr/bin/env python3
"""Build one fail-closed campaign plan from the approved final KIT and a live receipt.
No hardcoded product data, voice cloning, or social posting.
"""
import argparse,hashlib,json,re,zipfile
from decimal import Decimal,InvalidOperation
from trustfolio_flow.live import check_receipt
from pathlib import Path
from urllib.parse import urlencode
BAD={"","n/a","none","null","unknown","not available","-"}
SPEC_KEYS=("Capacity","Load Type","Energy Rating","Spin Speed","Automation Type","Washing Machine Type","Wash Programs","In-built Heater","Motor Type","Water Rating")
def require(condition,reason):
    if not condition: raise ValueError(reason)
def plan(receipt,kit):
    check_receipt(receipt)
    require(receipt.get("source")=="trustfolio_live_api","not a verified live API receipt")
    require(receipt.get("category")=="washing-machines","wrong category")
    mode=receipt.get("mode");require(mode in ("budget","brand_budget"),"unsupported mode")
    budget=receipt.get("budget_inr");require(type(budget) is int and budget>0,"invalid budget")
    brand=(receipt.get("brand") or "").strip()
    require(mode!="brand_budget" or brand,"brand is mandatory")
    products=receipt.get("products")
    require(isinstance(products,list) and len(products)==5,"exactly 5 live products required")
    require(receipt.get("snapshot_sha256") and re.fullmatch("[a-f0-9]{64}",receipt["snapshot_sha256"]),"missing immutable receipt checksum")
    with zipfile.ZipFile(kit) as z:
        require(z.testzip() is None,"corrupt approved master ZIP")
        names=set(z.namelist())
        for n in ("assets/video/08_green_boy_clean_master.mp4","assets/video/09_premium_girl_cta.mp4","assets/audio/original/08_green_boy_clean_master.wav"):
            require(any(x.endswith(n) for x in names),"missing master: "+n)
    ids=set();output=[]
    for rank,p in enumerate(products,1):
        require(p.get("rank")==rank,"rank mismatch")
        pid=str(p.get("id") or "")
        require(pid and pid not in ids,"duplicate product ID");ids.add(pid)
        try:
            price=Decimal(str(p.get("price_inr")))
        except (InvalidOperation,TypeError,ValueError):
            raise ValueError("invalid live price")
        require(price.is_finite() and 0<price<=budget,"invalid or over-budget live price")
        require(p.get("live_price_status")=="ok","price not verified live")
        require(p.get("image_url","").startswith("https://"),"missing HTTPS product image")
        require(p.get("title") and p.get("brand") and p.get("platform"),"missing source identity")
        require(mode!="brand_budget" or str(p["brand"]).casefold()==brand.casefold(),"brand mismatch")
        src=p.get("specifications") or {}
        require(isinstance(src,dict),"missing source specifications")
        specs=[{"key":k,"value":str(src[k]).strip()} for k in SPEC_KEYS if k in src and str(src[k]).strip().lower() not in BAD][:4]
        require(len(specs)==4,"fewer than 4 valid source specifications")
        output.append({"rank":rank,"id":pid,"brand":p["brand"],"title":p["title"],"price_inr":float(price),"platform":p["platform"],"image_url":p["image_url"],"specifications":specs})
    q={"budget":str(budget)}
    if mode=="brand_budget":q["brand"]=brand
    link="https://trustfolio.in/category/washing-machines/products?"+urlencode(q)
    lines=[f"🧺 Washing Machines • ₹{budget:,} • "+(brand if brand else "All Brands"),"TrustFolio के लाइव चेक किए गए Top 5:"]
    lines += [f"#{p['rank']} {p['title']} — ₹{p['price_inr']:,.0f}" for p in output]
    lines += ["",link,"कीमत और उपलब्धता बदल सकती है। खरीदने से पहले retailer पर जाँचें।","#TrustFolio #WashingMachine #BudgetShopping"]
    return {"status":"DATA_READY_NOT_PUBLISHABLE","source_snapshot_sha256":receipt["snapshot_sha256"],"mode":mode,"brand":brand,"budget_inr":budget,"products":output,"caption":"\n".join(lines),"landing_url":link,"voice_status":"REQUIRES_APPROVED_DYNAMIC_AUDIO_AND_LIPSYNC","video_status":"NOT_RENDERED","publish_allowed":False}
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--receipt",required=True);a.add_argument("--kit",required=True);a.add_argument("--output",required=True)
    x=a.parse_args()
    result=plan(json.loads(Path(x.receipt).read_text()),Path(x.kit))
    dest=Path(x.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("APPROVED_ASSET_AND_LIVE_DATA_CONTRACT_PASS; NO_POST")
if __name__=="__main__":main()
