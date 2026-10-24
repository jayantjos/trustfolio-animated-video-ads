import copy
from datetime import datetime,timezone,timedelta
import unittest

from trustfolio_video.contract import Blocked
from trustfolio_video.washing30 import build30,verify_reference_images
from trustfolio_video.wan5_nineshot import verified_plan,TIMES

def scene_data():
    now=datetime.now(timezone.utc).isoformat()
    products=[dict(id=f"{i:024x}",rank=i,title=f"Unbranded Test Washer {i}",brand=f"Test{i}",
                   platform="Test retailer",price_inr=39000-i*1000,main_image="https://m.media-amazon.com/images/I/example.jpg",
                   price_source="website_catalog" if i==3 else "website_live_price_api",
                   live_price_status="not_available" if i==3 else "ok",
                   website_catalog_fallback=(i==3),in_stock=True) for i in range(1,6)]
    a=dict(campaign=dict(category="washing-machines",budget=40000,mode="budget",brand=""),
           products=products,source_sha256="a"*64,observed_at=now,
           live_price_refresh_completed=True,live_price_count=4,catalog_fallback_count=1)
    return build30(a,references=verify_reference_images())

class TestNineWanShots(unittest.TestCase):
    def test_full_scene_timeline_and_hard_bounds(self):
        s=scene_data();m=verified_plan(s)
        self.assertEqual(9,len(m["shots"]))
        self.assertEqual(30,m["total_seconds"])
        self.assertEqual(list(TIMES),[(x["start"],x["end"]) for x in m["shots"]])
        self.assertEqual([5,4,3,2,1],[x["dynamic_rank"] for x in m["shots"][2:7]])
        self.assertEqual("RUNPOD_GPU_RENDER_PLAN_ONLY",m["kind"])
        self.assertFalse(m["new_paid_gpu_authorized"])
        self.assertFalse(m["published"])
        self.assertFalse(m["complete_motion_video_exists"])
        self.assertTrue(all(not shot["gpu_output_verified"] for shot in m["shots"]))
        self.assertTrue(all("no price labels" in shot["motion_prompt"] for shot in m["shots"]))

    def test_catalog_fallback_requires_disclosure(self):
        s=scene_data()
        s["scenes"][4]["dynamic"]["price_label"]="Website API live price"
        with self.assertRaisesRegex(Blocked,"Catalog price"):verified_plan(s)

    def test_stale_top5_is_never_used_for_paid_gpu(self):
        s=scene_data()
        s["data_observed_at"]=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        with self.assertRaisesRegex(Blocked,"stale"):verified_plan(s)

    def test_refuses_hardcoded_source_art_and_rank_swap(self):
        s=scene_data();s["scenes"][2]["reference_only"]=False
        with self.assertRaises(Blocked):verified_plan(s)
        s=scene_data();s["scenes"][2]["dynamic"]["rank"]=1
        with self.assertRaises(Blocked):verified_plan(s)

    def test_refuses_publish_enabled_and_misleading_photos(self):
        s=scene_data();s["publishing_enabled"]=True
        with self.assertRaises(Blocked):verified_plan(s)
        s=scene_data()
        with self.assertRaises(Blocked):verified_plan(s,photo_mode="ai_repaint")

    def test_cloned_asset_manifest_hash_is_deterministic(self):
        s=scene_data();first=verified_plan(s)
        second=verified_plan(copy.deepcopy(s))
        self.assertEqual(first["motion_job_hash"],second["motion_job_hash"])
        self.assertEqual(first["campaign_id"],second["campaign_id"])

if __name__=="__main__":unittest.main()
