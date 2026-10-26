"""Fetch TrustFolio's real public Top-5 and refresh the exact same five live prices.

Networked commands run only on explicit user invocation. This does not interact
with RunPod, models, social networks or the main TrustFolio app repository.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from hashlib import sha256
import json
import re

ORIGIN = "https://api.trustfolio.in"
MAX_REPLY = 500_000
MAX_AGE_SECONDS = 900
IMAGE_HOSTS = {
    "m.media-amazon.com", "images-na.ssl-images-amazon.com",
    "rukminim1.flixcart.com", "rukminim2.flixcart.com",
    "media.tatacroma.com", "media.croma.com",
}


class DataBlocked(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DataBlocked("Redirect blocked for verified product data")


def canonical(doc):
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(doc):
    return sha256(canonical(doc).encode("utf-8")).hexdigest()


def amount(value):
    if isinstance(value, bool):
        raise DataBlocked("Boolean is not a price")
    try:
        a = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise DataBlocked("Invalid price") from None
    if not a.is_finite() or not Decimal(0) < a <= Decimal(10_000_000):
        raise DataBlocked("Invalid price")
    return a


def valid_time(value, now=None, *, freshness=MAX_AGE_SECONDS):
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, str):
        raise DataBlocked("Missing live-price check time")
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("timezone missing")
    except ValueError:
        raise DataBlocked("Invalid price check time") from None
    delay = (now - ts.astimezone(timezone.utc)).total_seconds()
    if not -60 <= delay <= freshness:
        raise DataBlocked("Live price too old or in future")
    return ts.astimezone(timezone.utc).isoformat()


def image_url(p):
    sources = [p.get("main_image"), p.get("images")]
    for source in sources:
        if isinstance(source, dict):
            source = [source.get(k) for k in ("url", "src", "image_url", "large")]
        if isinstance(source, str):
            source = [source]
        for item in (source or []) if isinstance(source, list) else []:
            if isinstance(item, dict):
                item = next((item.get(k) for k in ("url", "src", "image_url") if item.get(k)), None)
            if not isinstance(item, str):
                continue
            parsed = urlsplit(item.strip())
            if parsed.scheme == "https" and parsed.hostname in IMAGE_HOSTS and not parsed.username and not parsed.password and parsed.port in (None, 443):
                return item.strip()
    raise DataBlocked("Product image missing or unapproved retailer image host")


def campaign(category, budget, mode="budget", brand=""):
    if not isinstance(category, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", category):
        raise DataBlocked("Invalid category")
    budget = amount(budget)
    if budget != budget.to_integral_value():
        raise DataBlocked("Budget must be a whole INR amount")
    if mode not in {"budget", "brand_budget", "comparison"}:
        raise DataBlocked("Invalid mode")
    if not isinstance(brand, str) or len(brand) > 100 or any(ord(c) < 32 for c in brand):
        raise DataBlocked("Invalid brand")
    brand = brand.strip()
    if (mode == "brand_budget") != bool(brand):
        raise DataBlocked("Brand required exactly for brand_budget")
    return dict(category=category, budget_inr=int(budget), mode=mode, brand=brand)


def _get_json(url, *, body=None, opener=None):
    opener = opener or build_opener(NoRedirect()).open
    req = Request(url, method="POST" if body is not None else "GET", data=canonical(body).encode() if body is not None else None,
                  headers={"Accept": "application/json", "Content-Type": "application/json",
                           "User-Agent": "TrustFolioGoogleFlowLiveClipPrep/1.0"})
    try:
        with opener(req, timeout=40) as response:
            if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
                raise DataBlocked("Unexpected API HTTP status or content type")
            raw = response.read(MAX_REPLY + 1)
    except (TimeoutError, OSError) as e:
        raise DataBlocked("TrustFolio live API unreachable") from e
    if len(raw) > MAX_REPLY:
        raise DataBlocked("API response too large")
    try:
        doc = json.loads(raw)
    except (UnicodeError, ValueError):
        raise DataBlocked("API JSON invalid") from None
    if not isinstance(doc, dict) or doc.get("success") is not True:
        raise DataBlocked("API did not confirm success")
    return doc


def normalize_live(get_data, live_rows, *, spec, checked_at=None, now=None):
    """Fail closed; preserve source Top-5 order and never invent/fill ranks."""
    now = now or datetime.now(timezone.utc)
    spec = campaign(spec["category"], spec["budget_inr"], spec.get("mode", "budget"), spec.get("brand", ""))
    products = get_data.get("products") if isinstance(get_data, dict) else None
    if not isinstance(products, list) or len(products) != 5:
        raise DataBlocked("Top-5 requires exactly five ranked website products")
    if not isinstance(live_rows, list) or len(live_rows) != 5:
        raise DataBlocked("Live-price request must return five rows")
    if spec["brand"] and (get_data.get("fallbackApplied") or get_data.get("partialBrandFill")):
        raise DataBlocked("Website returned brand fallback")
    if get_data.get("category") not in (None, spec["category"]):
        raise DataBlocked("API category mismatch")
    by_id = {}
    for row in live_rows:
        if not isinstance(row, dict):
            raise DataBlocked("Invalid live row")
        pid = str(row.get("id") or "")
        if pid in by_id or not re.fullmatch("[a-fA-F0-9]{24}", pid):
            raise DataBlocked("Bad / duplicate live ID")
        by_id[pid] = row
    norm=[]
    for rank, p in enumerate(products, 1):
        if not isinstance(p, dict):
            raise DataBlocked("Invalid Top-5 item")
        pid = str(p.get("id") or "")
        if not re.fullmatch("[a-fA-F0-9]{24}", pid) or pid not in by_id:
            raise DataBlocked("Top-5 and live price IDs differ")
        if "rank" in p and (type(p["rank"]) is not int or p["rank"] != rank):
            raise DataBlocked("Authoritative ranking mismatch")
        row = by_id[pid]
        live = row.get("live")
        if row.get("deleted") is True or p.get("is_active") is False or p.get("in_stock") is False:
            raise DataBlocked("Product removed, inactive or out of stock")
        # Older platform implementations return catalog-only values for Croma;
        # never claim them as current live prices in a paid/product video.
        if not isinstance(live, dict) or live.get("status") != "ok":
            raise DataBlocked("Price unavailable or catalog fallback; ad withheld")
        a = amount(live.get("price_inr"))
        if a > Decimal(spec["budget_inr"]):
            raise DataBlocked("Price exceeds advertised budget")
        stamp = valid_time(live.get("checked_at") or live.get("priced_at"), now)
        brand = str(p.get("brand") or "").strip()
        title = str(p.get("title") or "").strip()
        if not brand or not title:
            raise DataBlocked("Missing product name / brand")
        if spec["brand"] and brand.casefold() != spec["brand"].casefold():
            raise DataBlocked("Wrong brand in brand-budget campaign")
        specs = p.get("specifications") or {}
        if not isinstance(specs, dict):
            specs = {}
        safe_specs = {str(k).strip(): str(v).strip() for k, v in specs.items()
                      if isinstance(k, str) and isinstance(v, (str, int, float))
                      and not isinstance(v, bool) and k.strip() and len(str(v)) <= 80}
        norm.append({"rank":rank,"id":pid,"category":spec["category"],"title":title,"brand":brand,
                     "price_inr":str(a),"price_source":"website_live_price_api","live_price_status":"ok",
                     "live_checked_at":stamp,"in_stock":True,"is_active":True,
                     "platform":str(p.get("platform") or ""),"image_url":image_url(p),
                     "specifications":safe_specs})
    if set(by_id) != {x["id"] for x in norm}:
        raise DataBlocked("Unmatched live price product IDs")
    checked_at = valid_time(checked_at or now.isoformat(), now)
    return {"source":"trustfolio_live_api","category":spec["category"],"budget_inr":spec["budget_inr"],
            "mode":spec["mode"],"brand":spec["brand"],"checked_at":checked_at,"products":norm,
            "snapshot_sha256":sha({"spec":spec,"products":norm})}


def check_receipt(receipt, *, now=None, allow_demo=False):
    """Validate normalized provenance/freshness even when loaded from a JSON file."""
    if not isinstance(receipt, dict):
        raise DataBlocked("Receipt must be object")
    source = receipt.get("source")
    if source != "trustfolio_live_api" and not (allow_demo and source=="synthetic_test_only"):
        raise DataBlocked("No verified TrustFolio live API provenance")
    spec = campaign(receipt.get("category"), receipt.get("budget_inr"), receipt.get("mode"), receipt.get("brand", ""))
    if source == "trustfolio_live_api":
        valid_time(receipt.get("checked_at"), now)
    p=receipt.get("products")
    if not isinstance(p,list) or len(p)!=5:
        raise DataBlocked("Exactly five products required")
    ids=set()
    for rank,v in enumerate(p,1):
        if not isinstance(v,dict) or v.get("rank")!=rank or type(v.get("rank")) is not int:
            raise DataBlocked("Rank order wrong")
        pid=v.get("id")
        if not isinstance(pid,str) or not re.fullmatch("[a-fA-F0-9]{24}",pid) or pid in ids:
            raise DataBlocked("Bad / duplicate ID")
        ids.add(pid)
        if v.get("category") != spec["category"] or not v.get("brand") or not v.get("title"):
            raise DataBlocked("Bad product category / brand / title")
        if spec["brand"] and str(v["brand"]).casefold()!=spec["brand"].casefold():
            raise DataBlocked("Brand mismatch")
        if amount(v.get("price_inr")) > spec["budget_inr"]:
            raise DataBlocked("Above budget")
        if v.get("in_stock") is not True or v.get("is_active") is not True:
            raise DataBlocked("Product not confirmed available")
        if v.get("live_price_status")!="ok" or v.get("price_source")!="website_live_price_api":
            raise DataBlocked("Price status not live")
        if source == "trustfolio_live_api":
            valid_time(v.get("live_checked_at"),now)
        for k,x in (v.get("specifications") or {}).items():
            if not isinstance(k,str) or not isinstance(x,str) or len(x)>80:
                raise DataBlocked("Unsafe spec")
        u=urlsplit(str(v.get("image_url") or ""))
        if u.scheme!="https" or u.hostname not in IMAGE_HOSTS or u.username or u.password or u.port not in (None,443):
            raise DataBlocked("Unapproved image")
    if receipt.get("snapshot_sha256")!=sha({"spec":spec,"products":p}):
        raise DataBlocked("Receipt fingerprint mismatch")
    return receipt


def fetch_live(category, budget, mode="budget", brand="", *, opener=None, now=None):
    """One explicitly requested GET followed by the real, matching five-ID POST.
    The POST may cause live-price refresh/API cost. No retries and no publishing.
    """
    spec=campaign(category,budget,mode,brand)
    query={"category":spec["category"],"budget":str(spec["budget_inr"]),"limit":"5"}
    if spec["brand"]:
        query["brand"]=spec["brand"]
    get_url=ORIGIN+"/api/products/top?"+urlencode(query)
    get=_get_json(get_url,opener=opener)
    data=get.get("data")
    if not isinstance(data,dict) or not isinstance(data.get("products"),list) or len(data["products"])!=5:
        raise DataBlocked("Top-5 HTTP result did not contain exactly five products")
    ids=[str(v.get("id") or "") for v in data["products"]]
    if len(set(ids))!=5 or any(not re.fullmatch('[a-fA-F0-9]{24}', x) for x in ids):
        raise DataBlocked("Bad Top-5 IDs before live price POST")
    price=_get_json(ORIGIN+"/api/live-prices",body={"ids":ids},opener=opener)
    rows=price.get("data")
    if not isinstance(rows,list):
        raise DataBlocked("Missing live price rows")
    now=now or datetime.now(timezone.utc)
    receipt=normalize_live(data,rows,spec=spec,now=now)
    receipt["api_evidence"]={"get_response_sha256":sha(get),"post_response_sha256":sha(price),
                             "top5_api_url":get_url,"live_endpoint":"POST /api/live-prices",
                             "note":"No image/spec accuracy independently guaranteed; QA before use"}
    return receipt
