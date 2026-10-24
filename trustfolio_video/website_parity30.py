"""Two-call parity with TrustFolio website: GET ranked Top5, POST same IDs.

Catalogue fallback is disclosed, never called a live price. No independent
re-ranking, substitution, scraping, GPU provisioning, or app repo mutation.
"""
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
import hashlib,json
from urllib.error import URLError,HTTPError
from urllib.request import Request,build_opener
from .contract import Blocked,canonical,campaign,fetch,NoRedirect,api_url

POST_URL="https://api.trustfolio.in/api/live-prices"
MAX_POST_BYTES=300000

def build_verified_two_api(spec, *, get_fetcher=fetch, post_opener=None):
    spec=campaign(**spec)
    source=get_fetcher(spec)
    response=source.get("response",{})
    data=response.get("data")
    if response.get("success") is not True or not isinstance(data,dict):
        raise Blocked("Website Top5 response unsuccessful")
    if data.get("category")!=spec["category"] or int(data.get("budget") or 0)!=spec["budget"]:
        raise Blocked("Website campaign/category echo mismatch")
    if spec["brand"] and (data.get("fallbackApplied") or data.get("partialBrandFill")):
        raise Blocked("Website brand-only filter returned fallback")
    products=data.get("products")
    if not isinstance(products,list) or len(products)!=5:
        raise Blocked("Website requires exact Top 5")
    ids=[p.get("id") if isinstance(p,dict) else None for p in products]
    if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=5:
        raise Blocked("Duplicate or missing website product IDs")
    opener=post_opener or build_opener(NoRedirect()).open
    req=Request(POST_URL,method="POST",
                data=json.dumps({"ids":ids}).encode("utf-8"),
                headers={"Accept":"application/json","Content-Type":"application/json",
                         "User-Agent":"TrustFolioVideoWebsiteParity/2"})
    try:
        with opener(req,timeout=35) as rep:
            if rep.status!=200 or "json" not in rep.headers.get("Content-Type","").lower():
                raise Blocked("Live prices POST did not return HTTP200 JSON")
            raw=rep.read(MAX_POST_BYTES+1)
    except (HTTPError,URLError,TimeoutError,OSError) as exc:
        raise Blocked("Website live-prices POST unavailable: "+type(exc).__name__) from None
    if len(raw)>MAX_POST_BYTES: raise Blocked("Website live-prices reply too large")
    try: payload=json.loads(raw)
    except (ValueError,UnicodeDecodeError):raise Blocked("Website live-prices invalid JSON") from None
    rows=payload.get("data")
    if payload.get("success") is not True or not isinstance(rows,list) or len(rows)!=5:
        raise Blocked("Website live prices POST missing exact five rows")
    lookup={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get("id"),str) or row["id"] in lookup:
            raise Blocked("Live price response ID invalid or duplicated")
        lookup[row["id"]]=row
    if set(lookup)!=set(ids):raise Blocked("Website live price IDs changed")
    budget=Decimal(spec["budget"])
    normalized=[]
    for expected_rank,p in enumerate(products,1):
        if p.get("rank",expected_rank)!=expected_rank:
            raise Blocked("Source Top5 rank mismatch")
        if p.get("is_active") is False or p.get("in_stock") is False:
            raise Blocked("Source product inactive or out of stock")
        if spec["brand"] and str(p.get("brand") or "").casefold()!=spec["brand"].casefold():
            raise Blocked("Different brand in brand-only Top5")
        row=lookup[p["id"]]
        live=row.get("live")
        if row.get("deleted") is True or (isinstance(live,dict) and live.get("status")=="out_of_stock"):
            raise Blocked("Live API marks product deleted/out of stock")
        live=live if isinstance(live,dict) else {}
        state=live.get("status")
        if state=="ok":
            price_raw=live.get("price_inr")
            kind="website_live_price_api"
        else:
            price_raw=p.get("price_inr")
            kind="website_catalog"
        try:
            price=Decimal(str(price_raw))
            if not price.is_finite() or not Decimal(0)<price<=budget:
                raise ValueError()
        except (InvalidOperation,ValueError,TypeError):
            raise Blocked("Rank "+str(expected_rank)+" exceeds budget or invalid") from None
        copy=dict(p)
        copy.update(rank=expected_rank,price_inr=float(price),
                    price_source=kind,live_price_status=state,
                    live_checked_at=live.get("checked_at"),
                    live_priced_at=live.get("priced_at"),
                    website_catalog_fallback=(kind=="website_catalog"),
                    price_observed_through_api_at=datetime.now(timezone.utc).isoformat())
        normalized.append(copy)
    observed=datetime.now(timezone.utc).isoformat()
    return {"campaign":spec,"products":normalized,
        "source_sha256":hashlib.sha256(canonical({"get_sha256":source["response_sha256"],
                           "live_sha256":hashlib.sha256(canonical(payload).encode()).hexdigest()}).encode()).hexdigest(),
        "observed_at":observed,"top5_response_sha256":source["response_sha256"],
        "live_price_post_sha256":hashlib.sha256(canonical(payload).encode()).hexdigest(),
        "live_price_refresh_completed":True,
        "live_price_api_url":POST_URL,
        "live_price_count":sum(p["price_source"]=="website_live_price_api" for p in normalized),
        "catalog_fallback_count":sum(p["price_source"]=="website_catalog" for p in normalized),
        "published":False}
