"""GET-only product photo source QA. Never replace source identities or publish."""
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from .live import ORIGIN, IMAGE_HOSTS, _get_json, campaign, amount, DataBlocked, sha

FIELDS=("main_image","images","image","image_url","image_urls","gallery","product_images","thumbnail","thumbnails")
NESTED=("url","src","large","original","image","image_url","main","imageUrl","thumbnail")

def image_candidates(row, max_candidates=25):
    """List authentic allowed image URLs from THIS exact product record only."""
    found=[]
    def visit(item, depth=0):
        if depth>4 or len(found)>=max_candidates: return
        if isinstance(item,str):
            s=item.strip()
            if not s or len(s)>2048: return
            try:
                u=urlsplit(s)
                ok=(u.scheme=="https" and u.hostname in IMAGE_HOSTS
                    and not u.username and not u.password and u.port in (None,443))
            except ValueError: ok=False
            if ok and s not in found: found.append(s)
        elif isinstance(item,list):
            for v in item[:32]: visit(v,depth+1)
        elif isinstance(item,dict):
            for k in NESTED:
                if k in item: visit(item[k],depth+1)
            for k,v in list(item.items())[:32]:
                if k not in NESTED and isinstance(v,(dict,list)): visit(v,depth+1)
    for key in FIELDS:
        if key in row: visit(row[key])
    return found

def audit_top5(data, category="washing-machines", budget=25000):
    spec=campaign(category,budget)
    if not isinstance(data,dict) or not isinstance(data.get("products"),list) or len(data["products"])!=5:
        raise DataBlocked("Expected exactly five website products")
    products=[]; seen=set()
    for rank,p in enumerate(data["products"],1):
        if not isinstance(p,dict): raise DataBlocked("Invalid product row")
        pid=str(p.get("id") or "")
        if not re.fullmatch(r"[a-fA-F0-9]{24}",pid) or pid in seen:
            raise DataBlocked("Bad/duplicate product ID")
        seen.add(pid)
        if "rank" in p and (type(p["rank"]) is not int or p["rank"]!=rank):
            raise DataBlocked("Rank changed")
        price=amount(p.get("price_inr"))
        if price>spec["budget_inr"]: raise DataBlocked("Out-of-budget product")
        title=str(p.get("title") or "").strip()
        brand=str(p.get("brand") or "").strip()
        platform=str(p.get("platform") or "").strip()
        if not title or not brand or not platform: raise DataBlocked("Missing product identity")
        urls=image_candidates(p)
        products.append({"rank":rank,"source_product_id":pid,"title":title[:240],
          "brand":brand,"platform":platform,"website_listed_price_inr":str(price),
          "primary_image_url":urls[0] if urls else None,"candidate_image_urls":urls,
          "candidate_count":len(urls),"model_image_accuracy_verified":False})
    conflicts=[]
    for i,a in enumerate(products):
        for b in products[i+1:]:
            if a["primary_image_url"] and a["primary_image_url"]==b["primary_image_url"] and a["brand"].casefold()!=b["brand"].casefold():
                conflicts.append({"rank_a":a["rank"],"brand_a":a["brand"],
                  "rank_b":b["rank"],"brand_b":b["brand"],"url":a["primary_image_url"]})
    return {"source":"TRUSTFOLIO_WEBSITE_GET_ONLY","budget_inr":spec["budget_inr"],
      "category":spec["category"],"source_response_sha256":sha(data),
      "live_price_post_calls":0,"publishable":False,
      "status":"BLOCKED_CROSS_BRAND_PRIMARY_IMAGE" if conflicts else "MANUAL_PHOTO_QA_REQUIRED",
      "products":products,"cross_brand_primary_conflicts":conflicts,
      "note":"Other image URLs are unverified candidates from the SAME source record, not approved substitutes. Manual product/model verification is mandatory."}

def fetch_image_audit(category="washing-machines",budget=25000,opener=None):
    spec=campaign(category,budget)
    url=ORIGIN+"/api/products/top?"+urlencode({"category":spec["category"],"budget":str(spec["budget_inr"]),"limit":"5"})
    return audit_top5(_get_json(url,opener=opener).get("data"),category,budget)

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--category",default="washing-machines")
    p.add_argument("--budget",type=int,default=25000)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=fetch_image_audit(a.category,a.budget)
    f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("IMAGE_AUDIT_STATUS="+report["status"])
    for x in report["products"]:
        print(f"RANK_{x['rank']}_BRAND={x['brand']}_IMAGE_CANDIDATES={x['candidate_count']}")
    for x in report["cross_brand_primary_conflicts"]:
        print(f"CROSS_BRAND_IMAGE_SOURCE_DUPLICATE={x['rank_a']},{x['rank_b']}")
    print("NO_LIVE_PRICE_POST=YES; NO_SOCIAL_PUBLISH=YES; IMAGE_MATCH_QA_REQUIRED=YES")

if __name__=="__main__": main()
