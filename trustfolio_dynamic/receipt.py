"""Fail-closed normalized TrustFolio Top 5 receipt validation. No network access."""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

class InvalidReceipt(ValueError):
    pass

def price(value):
    if isinstance(value, bool): raise InvalidReceipt('Boolean price')
    try: amount = Decimal(str(value))
    except (InvalidOperation, ValueError): raise InvalidReceipt('Invalid price') from None
    if not amount.is_finite() or not 0 < amount <= 10000000: raise InvalidReceipt('Invalid price')
    return amount

def timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if not dt.tzinfo: raise ValueError('timezone missing')
        return dt.astimezone(timezone.utc)
    except (AttributeError, ValueError, TypeError):
        raise InvalidReceipt('Invalid price timestamp') from None

def validate(doc, *, demo=False, now=None):
    """Require exact Top 5, in-budget, available, fresh website_live_price_api receipts.

    A JSON receipt is not by itself proof that GET Top5 + POST live-prices were
    actually called. Production backend integration still must authenticate this.
    """
    if not isinstance(doc, dict): raise InvalidReceipt('Receipt must be object')
    category=doc.get('category'); mode=doc.get('mode'); brand=doc.get('brand', '')
    if not isinstance(category, str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', category): raise InvalidReceipt('Invalid category')
    if mode not in ('budget','brand_budget','comparison'): raise InvalidReceipt('Invalid mode')
    if not isinstance(brand,str) or len(brand)>100 or any(ord(c)<32 for c in brand): raise InvalidReceipt('Invalid brand')
    if (mode=='brand_budget') != bool(brand.strip()): raise InvalidReceipt('Brand mode mismatch')
    budget=price(doc.get('budget_inr'))
    if budget != budget.to_integral_value(): raise InvalidReceipt('Budget must be whole INR')
    if doc.get('source') != ('qa_fixture' if demo else 'trustfolio_live_api'): raise InvalidReceipt('Source status mismatch')
    now=now or datetime.now(timezone.utc)
    if not demo and not -60 <= (now-timestamp(doc.get('checked_at'))).total_seconds() <= 900: raise InvalidReceipt('Snapshot stale')
    products=doc.get('products')
    if not isinstance(products,list) or len(products)!=5: raise InvalidReceipt('Exactly 5 ranked products required')
    ids=set()
    for n,p in enumerate(products,1):
        if not isinstance(p,dict) or type(p.get('rank')) is not int or p['rank']!=n: raise InvalidReceipt('Rank mismatch')
        pid=p.get('id')
        if not isinstance(pid,str) or not re.fullmatch('[a-fA-F0-9]{24}',pid) or pid in ids: raise InvalidReceipt('Bad or duplicate ID')
        ids.add(pid)
        if p.get('category')!=category: raise InvalidReceipt('Category mismatch')
        if not isinstance(p.get('title'),str) or not p['title'].strip(): raise InvalidReceipt('Missing title')
        if not isinstance(p.get('brand'),str) or not p['brand'].strip(): raise InvalidReceipt('Missing brand')
        if mode=='brand_budget' and p['brand'].casefold()!=brand.casefold(): raise InvalidReceipt('Wrong brand')
        if price(p.get('price_inr'))>budget: raise InvalidReceipt('Over budget')
        if p.get('is_active') is not True or p.get('in_stock') is not True: raise InvalidReceipt('Unavailable product')
        if p.get('price_source')!='website_live_price_api' or p.get('live_price_status')!='ok': raise InvalidReceipt('Live price unverified')
        if not demo and not -60 <= (now-timestamp(p.get('live_checked_at'))).total_seconds() <= 900: raise InvalidReceipt('Price stale')
        specs=p.get('specifications',{})
        if not isinstance(specs,dict) or any(not isinstance(k,str) or not isinstance(v,(str,int,float)) or len(str(v))>70 for k,v in specs.items()): raise InvalidReceipt('Bad specifications')
    return products
