"""Data-led storyboards: comedy never becomes a fabricated product benchmark."""
import hashlib
from .contract import Blocked, MODES, canonical

STYLES = ('funny', 'cartoon', 'storytelling', 'premium')


def validate_registry(registry):
    worlds = registry['categories']
    if len(worlds) != 30 or len({w['slot'] for w in worlds}) != 30:
        raise Blocked('Thirty unique slots required')
    enabled = [w for w in worlds if w['enabled']]
    if len({w['slug'] for w in enabled}) != len(enabled):
        raise Blocked('Duplicate category')
    for w in worlds:
        if not w['enabled']:
            if not w.get('disabled_reason'):
                raise Blocked('Disabled slot requires reason')
            continue
        for key in ('slug','backend_category_id','world','palette','music_mood','sfx','personality','hooks','dialogue','reveal','cta','templates','character_presentation','animation_style'):
            if not w.get(key):
                raise Blocked('World missing '+key)
        if len(w['dialogue']) != 5 or len(w['templates']) < 3:
            raise Blocked('Five character lines and three alternate templates required')
    if len({w['world'] for w in enabled}) != len(enabled):
        raise Blocked('Worlds must be unique')
    return len(enabled)


def choose_template(world, history=()):
    for name in world['templates']:
        if name not in history[-2:]:
            return name
    return world['templates'][0]


def build(approved, world, *, duration=20, language='hinglish', style='funny', history=()):
    if not world['enabled'] or world['slug'] != approved['campaign']['category']:
        raise Blocked('World not enabled for this category')
    if duration not in (15,20,30) or language not in ('hinglish','hi','en') or style not in STYLES:
        raise Blocked('Unsupported duration, language or style')
    spec = approved['campaign']
    if spec['mode'] not in MODES:
        raise Blocked('Invalid mode')
    # Translation is intentionally gated until a reviewed language pack exists.
    if language != 'hinglish':
        raise Blocked('Reviewed Hindi/English language pack pending; do not auto-translate brand names')
    template = choose_template(world, history)
    scene_time = (duration-5)/5
    scenes = [{'start':0,'end':2,'kind':'hook','text':world['hooks'][world['templates'].index(template) % len(world['hooks'])]}]
    for index, product in enumerate(reversed(approved['products'])):
        rank = product['rank']
        start = 2+index*scene_time
        facts = product.get('specifications') or {}
        fact = next(((str(k),str(v)) for k,v in facts.items() if isinstance(v,(str,int,float)) and len(str(v)) < 65), None)
        dialogue = world['dialogue'][5-rank]
        if spec['mode'] == 'brand_budget':
            dialogue = spec['brand']+' squad! '+dialogue
        comparison = None
        if spec['mode'] == 'comparison':
            # Comparison displays literal source data; never declares a technical winner.
            comparison = {'label':fact[0], 'value':fact[1], 'source_id':product['id']} if fact else {'label':'Price','value':product['price_inr'],'source_id':product['id']}
        scenes.append({'start':start,'end':start+scene_time,'kind':'rank_reveal' if rank==1 else 'character',
                       'rank':rank,'source_product_id':product['id'],'name':product['title'],
                       'price_inr':product['price_inr'],'retailer':product['platform'],'image_url':product['main_image'],
                       'text':dialogue,'verified_fact':comparison,
                       'interaction':{'partner_rank':rank-1 if rank>1 else 2,'action':'wave_then_partner_reacts'},
                       'layers':['unaltered_product_photo','removable_eyes','removable_arms','speech_bubble','rank_badge']})
    scenes.append({'start':duration-3,'end':duration,'kind':'cta','text':world['cta'],
                   'url':'https://www.trustfolio.in','disclaimer':'Prices may change. Check current price before buying.'})
    identifier = hashlib.sha256(canonical({'spec':spec,'source':approved['source_sha256'],'template':template,'duration':duration,'style':style,'language':language}).encode()).hexdigest()
    return {'version':1,'campaign_id':identifier,'campaign':spec,'template':template,'style':style,
            'language':language,'world':world['world'],'duration':duration,'fps':24,'size':[1080,1920],
            'safe_zone':[90,220,900,1540],'source_sha256':approved['source_sha256'],
            'ranked_source_ids':[p['id'] for p in approved['products']], 'scenes':scenes,
            'publishing_enabled':False,'render_status':'awaiting_licensed_assets_and_voice'}
