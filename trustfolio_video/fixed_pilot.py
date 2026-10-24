"""Pinned category-specific cast and auditable washing-machine pilot plan.

Planning is CPU-only and requires no accounts or GPU. Render/publish gates are separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
from .contract import Blocked, campaign, fetch, validate
from .storyboard import validate_registry

ROOT = Path(__file__).resolve().parent.parent

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def check_registry(cast=None, worlds=None):
    cast = cast or load(ROOT / "config/characters_fixed.json")
    worlds = worlds or load(ROOT / "config/worlds.json")
    validate_registry(worlds)
    expected = {w["slug"] for w in worlds["categories"] if w["enabled"]}
    records = cast["categories"]
    if len(records) != 20 or {r["category"] for r in records} != expected:
        raise Blocked("Cast registry must match all 20 enabled worlds exactly")
    shared = cast.get("shared_character", {})
    if (shared.get("id") != "trustfolio-pink-kurta-lady-v1"
            or shared.get("sha256") != "7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6"):
        raise Blocked("Approved common lead is not pinned to the original reference")
    for key in ("location_asset", "seed"):
        if len({str(r[key]) for r in records}) != 20:
            raise Blocked("Every category needs its own location/seed: " + key)
    if ({r["character_id"] for r in records} != {shared["id"]}
        or {r["hero_asset"] for r in records} != {shared["hero_asset"]}):
        raise Blocked("Same pink-kurta woman required across all 20 categories")
    for r in records:
        if not r["fixed_character"] or not r["fixed_location_per_scene"]:
            raise Blocked("Fixed character/location rules must remain enabled")
        for key in ("hero_asset", "location_asset"):
            if not r[key].startswith("assets/") or ".." in Path(r[key]).parts:
                raise Blocked("Unsafe asset path")
    return {r["category"]: r for r in records}

def create_plan(*, category="washing-machines", budget=35000, live=False, root=ROOT):
    cast = check_registry()
    if category not in cast:
        raise Blocked("Unsupported or disabled category")
    if category != "washing-machines":
        raise Blocked("First pilot is washing-machines only; other 19 require visual QA")
    spec = campaign(category, budget)
    pilot = load(root / "config/pilots/washing-machines.json")
    if pilot["character_id"] != cast[category]["character_id"]:
        raise Blocked("Pilot character mismatch")
    if pilot["canonical_image"] != cast[category]["hero_asset"]:
        raise Blocked("Character image mismatch")
    if sum(s["seconds"] for s in pilot["scene_blueprint"]) != pilot["total_seconds"]:
        raise Blocked("Invalid storyboard timing")
    if pilot["scene_blueprint"][2]["rank_order"] != [5,4,3,2,1]:
        raise Blocked("Rank order may not change")
    assets = sorted({s["image_asset"] for s in pilot["scene_blueprint"]})
    missing = [p for p in assets if not (Path(root) / p).is_file()]
    output = {"category":category, "campaign":spec,"character_id":pilot["character_id"],
              "world":cast[category]["world"], "scenes":pilot["scene_blueprint"],
              "asset_paths":assets, "missing_assets":missing,
              "production_publishing":False,"full_video_rendered":False,
              "lip_sync_verified":False,"gpu_ran":False,
              "render_status":"ASSETS_PENDING" if missing else "ASSETS_PRESENT_GPU_NOT_RUN"}
    if live:
        snap = fetch(spec)
        good = validate(snap)
        output["live_source_sha256"] = good["source_sha256"]
        output["ranked_source_ids"] = [p["id"] for p in good["products"]]
        output["verified_at"] = good["observed_at"]
    else:
        output["live_source_sha256"] = None
        output["ranked_source_ids"] = []
    return output

def verify_hero(asset, expected_sha):
    data = Path(asset).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise Blocked("Approved hero asset SHA256 mismatch")
    return True

def main(argv=None):
    p=argparse.ArgumentParser(description="Offline character/world story plan; not a video render")
    p.add_argument("--category", default="washing-machines")
    p.add_argument("--budget",type=int,default=35000)
    p.add_argument("--live",action="store_true",help="Validate authoritative current Top 5; never fake prices")
    p.add_argument("--output",default="output/washing-machines-plan.json")
    args=p.parse_args(argv)
    plan=create_plan(category=args.category,budget=args.budget,live=args.live)
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"plan":str(dest),"status":plan["render_status"],
       "missing_assets":plan["missing_assets"],"publishing_enabled":False},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
