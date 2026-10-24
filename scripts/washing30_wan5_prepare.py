"""Verify the current live nine-scene brief and create a NO-GPU Wan job manifest.

Never runs render workers, opens GPU Pods, or republishes social posts.
"""
import argparse,json
from pathlib import Path
from trustfolio_video.contract import Blocked,campaign
from trustfolio_video.website_parity30 import build_verified_two_api
from trustfolio_video.washing30 import build30,verify_reference_images
from trustfolio_video.wan5_nineshot import verified_plan

def build_live(budget,mode,brand):
    spec=campaign("washing-machines",budget,mode,brand)
    verified=build_verified_two_api(spec)
    story=build30(verified,references=verify_reference_images())
    return verified_plan(story),story

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--budget",type=int,default=40000)
    p.add_argument("--mode",default="budget",choices=("budget","brand_budget","comparison"))
    p.add_argument("--brand",default="")
    p.add_argument("--out",default="output/wan5-nineshot-qa")
    a=p.parse_args()
    root=Path(a.out);root.mkdir(parents=True,exist_ok=True)
    try:
        plan,story=build_live(a.budget,a.mode,a.brand)
        (root/"motion-plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        result={"status":"NINE_SHOTS_READY_FOR_CLEAN_PLATE_AND_GPU_AUTHORIZATION",
                "campaign_id":plan["campaign_id"],"motion_job_hash":plan["motion_job_hash"],
                "scenes":len(plan["shots"]),"gpu_created":False,
                "total_estimated_gpu_cost_usd":None,
                "has_approved_new_gpu_spending_cap":False,"final_video_rendered":False,
                "source_observed_at":story["data_observed_at"],
                "product_price_sources":[v["dynamic"]["price_source"] for v in story["scenes"][2:7]],
                "all_factual_product_overlays_post_render":True}
        code=0
    except (Blocked,KeyError,TypeError,ValueError,OSError) as e:
        result={"status":"BLOCKED_NO_GPU_NO_FAKE_PRICES","reason":str(e),"gpu_created":False,
                "final_video_rendered":False}
        code=2
    (root/"safety-report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return code

if __name__=="__main__":
    raise SystemExit(main())
