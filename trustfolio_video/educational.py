"""Fact-checked category education, character interaction and 3 ad-mode scripts.

Never generates a fictional ranking or 'best because...' score. Facts come ONLY
from exact keys in the authoritative product's specifications dictionary. Can
build historical watermarked demos or strict-validator-approved previews, but
never enables publishing and never calls product substitution APIs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .contract import Blocked, MODES, canonical, money

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config" / "category_education_30.json"
WORLDS = ROOT / "config" / "worlds.json"
BACKEND_CATEGORIES = ROOT / "evidence" / "backend-categories.json"

HINDI_BRANDS = {
    "samsung": "सैमसंग", "lg": "एलजी", "godrej": "गोदरेज",
    "ifb": "आईएफबी", "haier": "हायर", "bosch": "बॉश",
    "oppo": "ओप्पो", "boat": "बोट", "croma": "क्रोमा",
    "sony": "सोनी", "doma": "डोमा", "acwo": "ऐक्वो",
}
HINDI_KEYS = {
    "capacity": "क्षमता", "wash capacity": "क्षमता", "net capacity": "क्षमता",
    "automation type": "ऑटोमैटिक सुविधा", "washing machine type": "ऑटोमैटिक सुविधा",
    "load type": "लोड टाइप", "energy rating": "एनर्जी रेटिंग",
    "star rating": "स्टार रेटिंग", "spin speed": "स्पिन स्पीड",
    "wash features": "वॉश फीचर", "battery capacity": "बैटरी",
    "battery life": "बैटरी लाइफ", "processor": "प्रोसेसर",
    "ram": "रैम", "storage": "स्टोरेज", "display": "डिस्प्ले",
    "screen size": "स्क्रीन साइज़", "camera": "कैमरा",
    "rear camera": "कैमरा", "water tank capacity": "पानी के टैंक की क्षमता",
    "power": "पावर", "power consumption": "पावर इस्तेमाल",
    "motor power": "मोटर पावर", "air delivery": "एयर डिलीवरी",
    "type": "टाइप", "number of jars": "जार",
    "bluetooth version": "ब्लूटूथ वर्ज़न", "playback time": "प्लेबैक टाइम",
    "noise cancellation": "नॉइज़ कैंसलेशन", "purification technology": "प्यूरिफ़िकेशन टेक्नोलॉजी",
}
HINDI_RANKS = {1:"नंबर वन",2:"नंबर टू",3:"नंबर थ्री",4:"नंबर फोर",5:"नंबर फाइव"}
SCENE_WINDOWS = ((0.4,4.0),(4.2,7.6),(7.8,11.3),(11.5,15.0),
                 (15.2,18.8),(19.0,24.0),(24.2,29.7))
ALLOWED_SCENES = ("hook","character","comparison","rank_reveal","cta")
PREVIEW_ONLY = "DEMO - NOT FOR PUBLICATION"


def load_master(path=CATALOG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def validate_master(master, worlds=None, backend=None):
    worlds = worlds or json.loads(WORLDS.read_text(encoding="utf-8"))
    backend = backend or json.loads(BACKEND_CATEGORIES.read_text(encoding="utf-8"))
    records = master.get("slots")
    if not isinstance(records, list) or len(records) != 30:
        raise Blocked("Exactly 30 category idea slots required")
    existing={x["slug"]:x for x in worlds["categories"] if x["enabled"]}
    # API category evidence: only these exact slug/IDs may be used in production.
    verified={x["slug"]:x["id"] for x in backend["categories"]}
    if set(existing)!=set(verified) or len(verified)!=20:
        raise Blocked("Existing worlds and historical backend registry disagree")
    enabled={};ids=set()
    for expected, slot in enumerate(records,1):
        if slot.get("slot") != expected:
            raise Blocked("Category slots must preserve stable numeric order")
        if not slot.get("enabled"):
            if expected<=20 or slot.get("backend_slug") is not None or slot.get("backend_category_id") is not None or not slot.get("disabled_reason"):
                raise Blocked("Unverified category accidentally enabled or assigned backend slug")
            continue
        slug=slot.get("backend_slug")
        if expected>20 or slug not in verified or slot.get("backend_category_id")!=verified[slug]:
            raise Blocked("Creative config must reuse a real verified backend category ID")
        if slug in enabled or verified[slug] in ids:
            raise Blocked("Duplicate category or backend ID")
        ids.add(verified[slug]);enabled[slug]=slot
        if slot.get("theme")!=existing[slug].get("world") and slot.get("theme") not in ("Bubble Laundry Kingdom","Neon Tech City","Freshness Ice Kingdom"):
            # editorial naming may intentionally change, while category identity cannot
            if not slot.get("environment",{}).get("location"):
                raise Blocked("Theme world lacks tangible environment")
        env=slot.get("environment") or {}
        ed=slot.get("education") or {}
        creative=slot.get("creative") or {}
        for entry in (env.get("location"),env.get("character_action"),
                      creative.get("problem_hook"),creative.get("problem_context"),
                      ed.get("product_role"),ed.get("why_best_policy"),slot.get("cta")):
            if not isinstance(entry,str) or not entry.strip():
                raise Blocked("Missing category-specific environment/story/educational detail")
        features=ed.get("feature_priority",[])
        if len(features)<3:
            raise Blocked("Need >=3 relevant feature targets per category")
        for f in features:
            if not f.get("key") or not f.get("accepted_source_keys"):
                raise Blocked("Feature rules need explicit source keys")
        if len(ed.get("user_personas",[]))<2:
            raise Blocked("Category must document user needs")
        if set(slot.get("modes",{}))!=set(MODES):
            raise Blocked("Three source modes required")
        if slot.get("publication")!="BLOCK_UNTIL_PRICE_AND_ASSET_RIGHTS_VERIFIED":
            raise Blocked("Ad may not claim publication approval")
    if set(enabled)!=set(verified):
        raise Blocked("Master must cover 20 verified categories exactly")
    return enabled


def _safe_value(value):
    if isinstance(value,bool) or value is None or not isinstance(value,(str,int,float)):
        return None
    clean=" ".join(str(value).split())
    if not clean or len(clean)>72 or _norm(clean) in ("unknown","na","n a","not specified","null","none","0"):
        return None
    if any(x in clean for x in ("<",">","{","}","\r","\n")):
        return None
    return clean


def exact_facts(product, category, *, limit=3):
    """Only accept the explicit source key, never infer a specification from title."""
    raw=product.get("specifications")
    if not isinstance(raw,dict):
        return []
    source={_norm(k):(str(k),v) for k,v in raw.items()}
    facts=[]
    used=set()
    for f in category["education"]["feature_priority"]:
        for name in f["accepted_source_keys"]:
            norm=_norm(name)
            if norm not in source:continue
            field,value=source[norm]
            clean=_safe_value(value)
            if clean is None or norm in used:continue
            facts.append({"key":f["key"],"field":field,"value":clean,
                         "source_product_id":product["id"],
                         "source_type":"product.specifications",
                         "claim_status":"EXACT_SOURCE_FIELD_ONLY"})
            used.add(norm)
            break
        if len(facts)>=limit:break
    return facts


def _brand_hi(brand):
    return HINDI_BRANDS.get(str(brand).casefold().strip(),str(brand))


def _feature_speech(fact):
    if fact is None:return None
    key=HINDI_KEYS.get(_norm(fact["field"]),fact["field"])
    return key+" "+fact["value"]


def _mode_hook(spec,category):
    if spec["mode"]=="brand_budget":
        return "एक ब्रांड, पाँच दोस्त! किसकी कौन सी खासियत? चलो देखें।"
    if spec["mode"]=="comparison":
        return "सबकी खासियत अलग है! कौन किस काम का? चलो तुलना करें।"
    # Category-specific problem first, never a flat rank enumeration.
    specific={
      "washing-machines":"अरे! कपड़ों का पहाड़ है। लॉन्ड्री गैंग तैयार है?",
      "smart-phones":"फोन की दुनिया में किसका कौन सा काम? चलो पता करें!",
      "refrigerators":"सब्ज़ी और दूध की चिंता? फ्रिज गैंग आ गई!",
      "headphones-earbuds":"म्यूज़िक की पार्टी में कौन लाया कौन सा फीचर?",
    }
    return specific.get(spec["category"], category["creative"]["problem_context"]+"! पाँच दोस्त तैयार हैं।")


def _title_line(product, fact, idx, mode):
    brand=_brand_hi(product.get("brand") or product["platform"])
    # Five different reacting characters, not repetitive 'panchwa bola' lines.
    reactions=(
       "अरे, ये देखो!", "वाह, ये काम की बात है!", "रुको, मेरा नंबर भी है!",
       "देखो, ये जानकारी याद रखना!", "और अब लिस्ट का टॉप दोस्त!"
    )
    if fact:
        feature=_feature_speech(fact)
        if mode=="comparison":
            return f"{brand}: {feature}। फीचर मिलाकर देखो!"
        if mode=="brand_budget":
            return f"{brand} टीम में {feature}। {reactions[idx]}"
        return f"{brand} में {feature}। {reactions[idx]}"
    # NO inferred 'better' if proof absent.
    return f"{brand} की जानकारी देखो; बाकी फीचर अभी सत्यापित नहीं हैं।"


def _fact_by_key(a,b):
    for fact in a:
        other=next((x for x in b if x["key"]==fact["key"]),None)
        if other:
            return {"label":fact["field"],"left":{"id":fact["source_product_id"],"value":fact["value"]},
                    "right":{"id":other["source_product_id"],"value":other["value"]},
                    "claim":"side-by-side only, no winner inferred"}
    return None


def build_educational_story(approved, master=None, *, duration=30, language="hinglish", variation=0):
    """Build source-bound 7-scene 30s story plus detailed educational paragraphs."""
    master=master if master is not None else load_master()
    supported=validate_master(master)
    spec=approved["campaign"]
    if not isinstance(spec,dict) or spec.get("mode") not in MODES or spec.get("category") not in supported:
        raise Blocked("Unknown/disabled category or ad mode")
    if duration!=30 or language!="hinglish":
        raise Blocked("Only reviewed 30s Hinglish educational pilot script supported")
    products=approved.get("products")
    if not isinstance(products,list) or len(products)!=5:
        raise Blocked("Five authority-ranked products required")
    ids=[x["id"] for x in products]
    if len(set(ids))!=5 or any(x.get("rank")!=i+1 for i,x in enumerate(products)):
        raise Blocked("Never substitute, duplicate or rerank products")
    if spec["mode"]=="brand_budget":
        brand=spec.get("brand")
        if not brand or any(str(p.get("brand","")).casefold()!=brand.casefold() for p in products):
            raise Blocked("Brand mode requires exactly five genuine matching-brand products")
    budget=money(spec["budget"])
    if any(money(p["price_inr"])>budget for p in products):
        raise Blocked("Over-budget product cannot be included even in historical demo")
    category=supported[spec["category"]]
    all_facts={p["id"]:exact_facts(p,category) for p in products}
    scenes=[{"kind":"hook","start":SCENE_WINDOWS[0][0],"end":SCENE_WINDOWS[0][1],
             "text":_mode_hook(spec,category),"visual":category["environment"]["location"],
             "action":category["environment"]["character_action"],
             "claim_status":"EDITORIAL_PROBLEM_HOOK_NOT_A_PRODUCT_FACT"}]
    education=[]
    ordered=list(reversed(products))
    for idx,p in enumerate(ordered):
        rank=p["rank"]
        facts=all_facts[p["id"]]
        chosen=facts[0] if facts else None
        counterpart=ordered[idx-1] if idx>0 else ordered[-1]
        paired=_fact_by_key(facts,all_facts[counterpart["id"]]) if spec["mode"]=="comparison" else None
        lines=_title_line(p,chosen,idx,spec["mode"])
        scene={"kind":"rank_reveal" if rank==1 else ("comparison" if spec["mode"]=="comparison" else "character"),
               "start":SCENE_WINDOWS[idx+1][0],"end":SCENE_WINDOWS[idx+1][1],
               "text":lines,"rank":rank,"product_id":p["id"],
               "price_inr":p["price_inr"],"price_is_historical":bool(approved.get("demo_only")),
               "evidence":chosen,"comparison":paired,
               "character_action":category["environment"]["character_action"],
               "partner_product_id":counterpart["id"],
               "all_verified_facts":facts}
        scenes.append(scene)
        factual="; ".join(f["field"]+": "+f["value"] for f in facts)
        if not factual:factual="Specific features unavailable in source record; do not guess."
        education.append({
            "product_id":p["id"],"rank":rank,"title":p["title"],
            "what_it_does":category["education"]["product_role"],
            "verified_specs":facts,
            "why_a_user_might_consider":"Actual specs: "+factual+
                ". Need to compare with your intended usage and current offer.",
            "possible_user_needs":category["education"]["user_personas"],
            "user_fit_is_not_proven":True,
            "why_ranked":f"TrustFolio source API recorded rank #{rank}; scoring factors not supplied. No causal winner claim.",
            "price_inr":p["price_inr"],
            "price_evidence":"historical snapshot, NOT verified current offer" if approved.get("demo_only")
                             else "review production price validator output",
        })
    scenes.append({"kind":"cta","start":SCENE_WINDOWS[-1][0],"end":SCENE_WINDOWS[-1][1],
                   "text":"ज़रूरत अलग, बजट अलग! ट्रस्टफ़ोलियो पर तुलना करो।",
                   "url":"https://www.trustfolio.in","disclaimer":"Recorded prices can change; verify live offers."})
    if len(scenes)!=7 or [s["rank"] for s in scenes if "rank" in s]!=[5,4,3,2,1]:
        raise Blocked("Bad 5-to-1 source scene mapping")
    source_sha=approved["source_sha256"]
    campaign_id=hashlib.sha256(canonical({"source":source_sha,"mode":spec["mode"],
             "category":spec["category"],"brand":spec.get("brand",""),
             "duration":duration,"variation":variation,"format":"educational-v1"}).encode()).hexdigest()
    return {"version":1,"campaign_id":campaign_id,"campaign":spec,
            "category_world":category["theme"],"environment":category["environment"],
            "education_role":category["education"]["product_role"],
            "feature_guidance":category["education"]["feature_priority"],
            "audio_notes":{"voice_language":"hi-Deva planned / Hinglish style",
                           "human_naturalness_approved":False,
                           "scene_sound_motifs":category["creative"]["sfx"]},
            "scenes":scenes,"expanded_product_explanations":education,
            "ranked_source_ids":ids,"source_sha256":source_sha,
            "demo_only":bool(approved.get("demo_only")),
            "watermark":PREVIEW_ONLY if approved.get("demo_only") else "QA PREVIEW - NO PUBLICATION",
            "publishing_enabled":False,
            "eligibility":"HISTORICAL_QA_ONLY" if approved.get("demo_only") else "PENDING_ASSET_AND_HUMAN_QA",
            "duration_seconds":duration,"fps":24}
