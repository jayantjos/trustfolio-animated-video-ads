"""Safe CLI: export source-bound educational scripts for real, historical Top-5 QA."""
import argparse
import json
from pathlib import Path

from .contract import validate, Blocked
from .demo import approve_historical_demo
from .educational import build_educational_story, load_master


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--snapshot",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--mode",choices=["demo","strict"],default="demo")
    ap.add_argument("--duration",type=int,choices=[30],default=30)
    args=ap.parse_args()
    source=Path(args.snapshot)
    dest=Path(args.output)
    envelope=json.loads(source.read_text(encoding="utf-8"))
    # Demo=historical immutable snapshot; strict=trustworthy fresh-time validator.
    approved=approve_historical_demo(envelope) if args.mode=="demo" else validate(envelope)
    story=build_educational_story(approved,load_master(),duration=args.duration)
    if args.mode=="demo":
        assert story["demo_only"] and not story["publishing_enabled"]
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(story,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("EDUCATIONAL_STORY_CREATED="+str(dest))
    print("CAMPAIGN="+json.dumps(story["campaign"],ensure_ascii=False))
    print("SOURCE_PRODUCT_IDS="+",".join(story["ranked_source_ids"]))
    print("EXACT_VERIFIED_SPEC_COUNT="+str(sum(len(p["verified_specs"]) for p in story["expanded_product_explanations"])))
    print("PUBLISHING_ENABLED=false")
    print("HISTORICAL_DEMO_ONLY="+str(story["demo_only"]).lower())


if __name__=="__main__":
    try:
        main()
    except (Blocked, KeyError, ValueError) as e:
        print("BLOCKED: "+str(e))
        raise SystemExit(2)
