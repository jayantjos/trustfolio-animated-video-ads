"""Historical-only pilot input: never a production-price approval or publishable asset."""
import hashlib
import re
from urllib.parse import urlsplit
from .contract import Blocked, campaign, canonical, api_url, money, timestamp

APPROVED_IMAGE_HOSTS = {
    "m.media-amazon.com", "images-na.ssl-images-amazon.com",
    "rukminim1.flixcart.com", "rukminim2.flixcart.com", "media.tatacroma.com",
}

def approve_historical_demo(envelope):
    """Preserve exactly the original five IDs/prices; require original snapshot integrity.

    Historical catalog prices are *not* treated as live-verified. Production must
    always use contract.validate independently. Demo output is permanently
    watermarked and has no publication adapter.
    """
    if not isinstance(envelope, dict):
        raise Blocked("Invalid historical envelope")
    spec = campaign(**envelope["request"])
    if envelope.get("source_url") != api_url(spec):
        raise Blocked("Historical API URL mismatch")
    timestamp(envelope.get("observed_at"))
    raw = envelope.get("response")
    if not isinstance(raw, dict) or raw.get("success") is not True:
        raise Blocked("Invalid archived response")
    source_sha = hashlib.sha256(canonical(raw).encode()).hexdigest()
    if source_sha != envelope.get("response_sha256"):
        raise Blocked("Historical snapshot tampered")
    data = raw.get("data") or {}
    if data.get("category") != spec["category"] or data.get("budget") != spec["budget"]:
        raise Blocked("Category/budget mismatch")
    products = data.get("products")
    if not isinstance(products, list) or len(products) != 5:
        raise Blocked("Archived demo needs exactly 5 source-ranked products")
    if spec["brand"] and (data.get("fallbackApplied") or data.get("partialBrandFill")):
        raise Blocked("Mixed-brand fallback cannot make brand demo")
    seen = set()
    for rank, p in enumerate(products, 1):
        if not isinstance(p, dict):
            raise Blocked("Invalid historical product")
        pid = p.get("id", "")
        if not isinstance(pid, str) or not re.fullmatch(r"[0-9a-fA-F]{24}", pid) or pid in seen:
            raise Blocked("Missing or duplicate source product ID")
        seen.add(pid)
        if p.get("rank") != rank or p.get("product_category") != spec["category"]:
            raise Blocked("Wrong historical ranking/category")
        if not p.get("title") or not p.get("platform"):
            raise Blocked("Missing product identity")
        if p.get("is_active") is not True or p.get("in_stock") is not True:
            raise Blocked("Inactive/out of stock historical product")
        if money(p.get("price_inr")) > spec["budget"]:
            raise Blocked("Historical product over budget")
        if spec["brand"] and str(p.get("brand", "")).casefold() != spec["brand"].casefold():
            raise Blocked("Historical product different brand")
        u = urlsplit(str(p.get("main_image", "")))
        if (u.scheme != "https" or u.hostname not in APPROVED_IMAGE_HOSTS
            or u.username or u.password or u.port not in (None, 443)):
            raise Blocked("Unapproved product image origin")
    return {
        "campaign": spec,
        "products": products,
        "source_sha256": source_sha,
        "source_observed_at": envelope["observed_at"],
        "demo_only": True,
        "watermark": "DEMO - NOT FOR PUBLICATION",
        "publishing_enabled": False,
        "price_evidence": [
            {"product_id": p["id"], "price_inr": p["price_inr"],
             "price_source": p.get("price_source", "unknown"),
             "live_price_status": p.get("live_price_status"),
             "live_checked_at": p.get("live_checked_at") or p.get("live_priced_at")}
            for p in products
        ],
    }
