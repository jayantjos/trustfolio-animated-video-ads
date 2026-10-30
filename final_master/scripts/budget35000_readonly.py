"""Read-only website Top Five snapshot for user-approved catalog-price QA.
Do not represent catalog/no_price values as verified live.
"""
import json,urllib.request,hashlib,argparse
from pathlib import Path
URL="https://api.trustfolio.in/api/products/top?category=washing-machines&budget=35000&limit=5"
def main():
 p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
 req=urllib.request.Request(URL,headers={"User-Agent":"TrustFolio-35000-Video-QA/1.0"})
 with urllib.request.urlopen(req,timeout=50) as r: data=json.load(r)
 if data.get("success") is not True:raise ValueError("API unsuccessful")
 rows=data["data"]["products"]
 if len(rows)!=5 or [x["rank"] for x in rows]!=list(range(1,6)):raise ValueError("Rank mismatch")
 allowed={"Capacity","Energy Rating","Load Type","Automation Type","Washing Machine Type","Spin Speed","Wash Features"}
 output=[]
 for i,x in enumerate(rows,1):
  if not (0<int(x["price_inr"])<=35000):raise ValueError("Over budget")
  if x["live_price_status"] not in ("ok","no_price"):raise ValueError("Unsafe availability")
  specs=[{"label":k,"value":str(v)} for k,v in (x.get("specifications") or {}).items() if k in allowed and str(v).strip()][:4]
  if len(specs)!=4:raise ValueError("Incomplete source features")
  output.append(dict(rank=i,product_id=x["id"],brand=x["brand"],title=x["title"],price_inr=x["price_inr"],
   image_url=x["main_image"],specifications=specs,
   price_label="LIVE" if x["live_price_status"]=="ok" and x["price_source"]=="website_live_price_api" else "CATALOG - UNVERIFIED",
   live_price_status=x["live_price_status"],source=x["price_source"]))
 blob={"budget_inr":35000,"mode":"budget","category":"washing-machines","products":output,
  "approval":"REVIEW_ONLY","publish_allowed":False}
 blob["snapshot_sha256"]=hashlib.sha256(json.dumps(output,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(blob,ensure_ascii=False,indent=2)+"\n")
 print("TOP5_FETCHED",[(x["rank"],x["brand"],x["price_label"]) for x in output])
if __name__=="__main__":main()
