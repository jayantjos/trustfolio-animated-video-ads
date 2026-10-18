"""Authoritative Top-5 ingestion. Never rerank, refresh separately, or fill gaps."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ORIGIN = 'https://api.trustfolio.in'
MAX_BYTES = 500_000
MODES = ('budget', 'brand_budget', 'comparison')


class Blocked(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked('API redirect rejected')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('timezone required')
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise Blocked('Missing or invalid timezone-aware price timestamp') from None


def money(value):
    if isinstance(value, bool):
        raise Blocked('Boolean price rejected')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise Blocked('Invalid money') from None
    if not number.is_finite() or number <= 0 or number > 10_000_000:
        raise Blocked('Invalid money')
    return number


def campaign(category, budget, mode='budget', brand=''):
    if not isinstance(category, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', category):
        raise Blocked('Invalid category')
    amount = money(budget)
    if amount != amount.to_integral_value():
        raise Blocked('Budget must be whole rupees')
    if mode not in MODES:
        raise Blocked('Unknown campaign mode')
    if not isinstance(brand, str) or len(brand) > 100 or any(ord(x) < 32 for x in brand):
        raise Blocked('Invalid brand')
    brand = brand.strip()
    if (mode == 'brand_budget') != bool(brand):
        raise Blocked('Brand is required only for brand_budget mode')
    return dict(category=category, budget=int(amount), mode=mode, brand=brand)


def api_url(spec):
    verified = campaign(**spec)
    query = {k: verified[k] for k in ('category', 'budget')}
    query['limit'] = 5
    if verified['brand']:
        query['brand'] = verified['brand']
    return ORIGIN + '/api/products/top?' + urlencode(query)


def fetch(spec, *, opener=None, sleep=time.sleep):
    """One authoritative GET; retry only network/429/5xx failures, at most twice."""
    url = api_url(spec)
    opener = opener or build_opener(NoRedirect()).open
    for attempt in range(3):
        try:
            req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'TrustFolioAnimatedQA/0.1'})
            with opener(req, timeout=35) as response:
                if response.status != 200 or 'application/json' not in response.headers.get('Content-Type', ''):
                    raise Blocked('API must return HTTP 200 application/json')
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise Blocked('API response too large')
            payload = json.loads(raw)
            return {'request': spec, 'source_url': url,
                    'observed_at': datetime.now(timezone.utc).isoformat(),
                    'response_sha256': hashlib.sha256(canonical(payload).encode()).hexdigest(),
                    'response': payload}
        except HTTPError as exc:
            if (exc.code != 429 and exc.code < 500) or attempt == 2:
                raise Blocked('API HTTP failure: ' + str(exc.code)) from None
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise Blocked('API unavailable after bounded retries') from None
        sleep(2 ** attempt)


def validate(envelope, *, now=None, max_age_seconds=900):
    """Missing freshness evidence is a blocker, never an implied successful refresh."""
    now = now or datetime.now(timezone.utc)
    spec = campaign(**envelope['request'])
    issues = []
    def require(condition, reason):
        if not condition:
            issues.append(reason)
    observed = timestamp(envelope.get('observed_at'))
    require(-60 <= (now-observed).total_seconds() <= max_age_seconds, 'snapshot_stale_or_future')
    require(envelope.get('source_url') == api_url(spec), 'source_url_mismatch')
    response = envelope.get('response', {})
    require(envelope.get('response_sha256') == hashlib.sha256(canonical(response).encode()).hexdigest(), 'snapshot_hash_mismatch')
    require(response.get('success') is True, 'api_unsuccessful')
    data = response.get('data')
    if not isinstance(data, dict):
        raise Blocked('API data missing')
    require(data.get('category') == spec['category'], 'category_mismatch')
    require(data.get('budget') == spec['budget'], 'budget_echo_mismatch')
    require(data.get('livePriceRefreshCompleted') is True, 'refresh_not_completed')
    if spec['brand']:
        require(not data.get('fallbackApplied') and not data.get('partialBrandFill'), 'brand_fallback')
        require(data.get('requestedBrand', '').casefold() == spec['brand'].casefold(), 'brand_echo_mismatch')
    products = data.get('products')
    if not isinstance(products, list) or len(products) != 5:
        raise Blocked('Exactly five authoritative products required; no client substitutions')
    seen = set()
    for rank, product in enumerate(products, 1):
        if not isinstance(product, dict):
            raise Blocked('Invalid product object')
        prefix = f'rank_{rank}:'
        pid = product.get('id')
        require(isinstance(pid, str) and bool(re.fullmatch(r'[a-fA-F0-9]{24}', pid or '')), prefix+'invalid_source_id')
        require(pid not in seen, prefix+'duplicate_id')
        seen.add(pid)
        require(type(product.get('rank')) is int and product['rank'] == rank, prefix+'rank_mismatch')
        require(product.get('product_category') == spec['category'], prefix+'category_mismatch')
        require(isinstance(product.get('title'), str) and bool(product['title'].strip()), prefix+'title_missing')
        require(bool(product.get('platform')), prefix+'retailer_missing')
        require(product.get('is_active') is True and product.get('in_stock') is True, prefix+'availability_unverified')
        try:
            require(money(product.get('price_inr')) <= spec['budget'], prefix+'over_budget')
        except Blocked:
            issues.append(prefix+'invalid_price')
        if spec['brand']:
            require(str(product.get('brand', '')).casefold() == spec['brand'].casefold(), prefix+'wrong_brand')
        image = urlsplit(str(product.get('main_image', '')))
        require(image.scheme == 'https' and image.hostname in {'m.media-amazon.com', 'images-na.ssl-images-amazon.com', 'rukminim2.flixcart.com', 'rukminim1.flixcart.com', 'media.tatacroma.com'} and not image.username and not image.password and image.port in (None, 443), prefix+'unapproved_image_url')
        require(product.get('price_source') == 'website_live_price_api' and product.get('live_price_status') == 'ok', prefix+'live_price_unverified')
        try:
            checked = timestamp(product.get('live_checked_at') or product.get('live_priced_at'))
            require(-60 <= (now-checked).total_seconds() <= max_age_seconds, prefix+'price_stale_or_future')
        except Blocked:
            issues.append(prefix+'price_timestamp_missing')
    if issues:
        raise Blocked('; '.join(issues))
    return {'campaign': spec, 'products': products, 'source_sha256': envelope['response_sha256'],
            'observed_at': envelope['observed_at'], 'publishing_enabled': False}
