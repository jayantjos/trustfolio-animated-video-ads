#!/usr/bin/env python3
"""One-shot read-only live Top5 -> nine-scene creative manifest. No GPU, no posting."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

from trustfolio_video.contract import Blocked, campaign
from trustfolio_video.website_parity30 import build_verified_two_api
from trustfolio_video.washing30 import build30, verify_reference_images

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--budget",type=int,required=True)
    parser.add_argument("--mode",default="budget",choices=("budget","brand_budget","comparison"))
    parser.add_argument("--brand",default="")
    parser.add_argument("--output",default="output/washing30-live")
    args=parser.parse_args(argv)
    dest=Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    report={"checked_at":datetime.now(timezone.utc).isoformat(),
            "budget_inr":args.budget,"mode":args.mode,
            "gpu_created":False,"published":False}
    try:
        spec=campaign("washing-machines",args.budget,args.mode,args.brand)
        refs=verify_reference_images()
        approved=build_verified_two_api(spec)
        story=build30(approved,references=refs)
        (dest/"storyboard30.json").write_text(json.dumps(story,ensure_ascii=False,indent=2)+"
",encoding="utf-8")
        # Save the validated snapshot for auditable render inputs; private QA only.
        (dest/"live-top5-snapshot.json").write_text(json.dumps(approved,ensure_ascii=False,indent=2)+"
",encoding="utf-8")
        report.update(status="VERIFIED_LIVE_STORYBOARD_READY",scenes=9,
                      approved_snapshot_sha256=approved["source_sha256"],
                      live_price_count=approved["live_price_count"],
                      catalog_fallback_count=approved["catalog_fallback_count"],
                      video_rendered=False,voice_rendered=False)
    except (Blocked,ValueError,TypeError,KeyError,OSError) as exc:
        report.update(status="BLOCKED_NO_FAKE_DATA",reason=str(exc),video_rendered=False)
    (dest/"validation30.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"
",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report["status"]=="VERIFIED_LIVE_STORYBOARD_READY" else 2

if __name__=="__main__":
    sys.exit(main())
