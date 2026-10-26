"""GET-only TrustFolio website ranking for Google Flow PREVIEW editing.

Preserves website Top 5 and its displayed/stored prices. Never certifies
catalog prices as live or enables social publishing.
"""
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode, urlsplit
import re
from .live import ORIGIN, IMAGE_HOSTS, DataBlocked, _get_json, campaign, amount, image_url, sha, valid_time, check_receipt

SOURCE = "trustfolio_website_display"


def _usable(row, rank, spec, seen):
    if not isinstance(row, dict):
        raise DataBlocked("Invalid website product object")
    pid = str(row.get("id") or "")
    if not re.fullmatch(r"[a-fA-F0-9]{24}", pid) or pid in seen:
        raise DataBlocked("Missing / duplicate website product ID")
    seen.add(pid)
    if "rank" in row and (type(row["rank"]) is not int or row["rank"] != rank):
        raise DataBlocked("Website ranking order mismatch")
    if row.get("product_category", spec["category"]) != spec["category"]:
        raise DataBlocked("Product category mismatch")
    if row.get("is_active") is False or row.get("in_stock") is False:
        raise DataBlocked("Inactive or out-of-stock product")
    title = str(row.get("title") or "").strip()
    brand = str(row.get("brand") or "").strip()
    platform = str(row.get("platform") or "").strip()
    if not title or not brand or not platform:
        raise DataBlocked("Missing title / brand / retailer")
    if spec["brand"] and brand.casefold() != spec["brand"].casefold():
        raise DataBlocked("Brand-only website product mismatch")
    price = amount(row.get("price_inr"))
    if price > Decimal(spec["budget_inr"]):
        raise DataBlocked("Displayed price exceeds advertised budget")
    specs = row.get("specifications") or {}
    if not isinstance(specs, dict):
        specs = {}
    safe = {str(k).strip(): str(v).strip() for k, v in specs.items()
            if isinstance(k, str) and k.strip()
            and isinstance(v, (str, int, float)) and not isinstance(v, bool)
            and 0 < len(str(v)) <= 80}
    return {"rank": rank, "id": pid, "category": spec["category"],
            "title": title, "brand": brand, "platform": platform,
            "price_inr": str(price), "price_source": "website_displayed_price",
            "live_price_status": "not_verified_for_video", "live_checked_at": None,
            "price_label": "TrustFolio-listed price (not independently live verified)",
            "in_stock": True, "is_active": True, "image_url": image_url(row),
            "specifications": safe}


def normalize_website_display(get_data, *, spec, now=None, evidence=None):
    now = now or datetime.now(timezone.utc)
    spec = campaign(spec["category"], spec["budget_inr"], spec.get("mode", "budget"), spec.get("brand", ""))
    if not isinstance(get_data, dict):
        raise DataBlocked("Invalid website response")
    if get_data.get("category") not in (None, spec["category"]):
        raise DataBlocked("Wrong category")
    if get_data.get("budget") is not None and amount(get_data["budget"]) != spec["budget_inr"]:
        raise DataBlocked("Budget echoed incorrectly")
    if spec["brand"] and (get_data.get("fallbackApplied") or get_data.get("partialBrandFill")):
        raise DataBlocked("Brand fallback not allowed")
    products = get_data.get("products")
    if not isinstance(products, list) or len(products) != 5:
        raise DataBlocked("Website did not return exactly five products")
    seen = set()
    norm = [_usable(p, rank, spec, seen) for rank, p in enumerate(products, 1)]
    doc = {"source": SOURCE, "category": spec["category"], "budget_inr": spec["budget_inr"],
           "mode": spec["mode"], "brand": spec["brand"], "checked_at": now.isoformat(),
           "products": norm, "snapshot_sha256": sha({"spec": spec, "products": norm}),
           "publishable": False, "pricing_verification": "WEBSITE_LISTED_ONLY",
           "note": "GET website Top5 only. No POST /api/live-prices. No live-price verification."}
    if evidence:
        doc["api_evidence"] = evidence
    return doc


def check_site_display(doc, *, now=None):
    if not isinstance(doc, dict) or doc.get("source") != SOURCE:
        raise DataBlocked("Not a website display receipt")
    spec = campaign(doc.get("category"), doc.get("budget_inr"), doc.get("mode"), doc.get("brand", ""))
    valid_time(doc.get("checked_at"), now)
    if doc.get("publishable") is not False or doc.get("pricing_verification") != "WEBSITE_LISTED_ONLY":
        raise DataBlocked("Display-only receipt must block publishing")
    products = doc.get("products")
    if not isinstance(products, list) or len(products) != 5:
        raise DataBlocked("Expected exactly five displayed products")
    ids = set()
    for rank, p in enumerate(products, 1):
        if not isinstance(p, dict) or type(p.get("rank")) is not int or p["rank"] != rank:
            raise DataBlocked("Rank order changed")
        pid = p.get("id")
        if not isinstance(pid, str) or not re.fullmatch(r"[a-fA-F0-9]{24}", pid) or pid in ids:
            raise DataBlocked("Invalid or repeated ID")
        ids.add(pid)
        if p.get("category") != spec["category"] or not p.get("title") or not p.get("brand") or not p.get("platform"):
            raise DataBlocked("Missing product identity")
        if spec["brand"] and p["brand"].casefold() != spec["brand"].casefold():
            raise DataBlocked("Wrong brand")
        if amount(p.get("price_inr")) > spec["budget_inr"]:
            raise DataBlocked("Above budget")
        if p.get("is_active") is not True or p.get("in_stock") is not True:
            raise DataBlocked("Unavailable")
        if (p.get("price_source") != "website_displayed_price" or
                p.get("live_price_status") != "not_verified_for_video" or
                p.get("live_checked_at") is not None):
            raise DataBlocked("False current live-price claim")
        for k, v in (p.get("specifications") or {}).items():
            if not isinstance(k, str) or not isinstance(v, str) or len(v) > 80:
                raise DataBlocked("Unsafe specification")
        u = urlsplit(str(p.get("image_url") or ""))
        if (u.scheme != "https" or u.hostname not in IMAGE_HOSTS or u.username or
                u.password or u.port not in (None, 443)):
            raise DataBlocked("Unapproved product image URL")
    if doc.get("snapshot_sha256") != sha({"spec": spec, "products": products}):
        raise DataBlocked("Receipt checksum mismatch")
    return doc


def check_flow_receipt(doc, *, now=None, allow_demo=False):
    if isinstance(doc, dict) and doc.get("source") == SOURCE:
        return check_site_display(doc, now=now)
    return check_receipt(doc, now=now, allow_demo=allow_demo)


def fetch_website_display(category, budget, mode="budget", brand="", *, opener=None, now=None):
    """One read-only GET; NO POST or external price refresh."""
    spec = campaign(category, budget, mode, brand)
    query = {"category": spec["category"], "budget": str(spec["budget_inr"]), "limit": "5"}
    if spec["brand"]:
        query["brand"] = spec["brand"]
    url = ORIGIN + "/api/products/top?" + urlencode(query)
    response = _get_json(url, opener=opener)
    receipt = normalize_website_display(response.get("data"), spec=spec, now=now,
        evidence={"top5_api_url": url, "get_response_sha256": sha(response),
                  "live_price_post_calls": 0, "method": "GET"})
    check_site_display(receipt, now=now)
    return receipt
