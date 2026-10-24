"""Regression tests for fixed nine-scene visual blueprint and dynamic live-price binding."""
import copy
from datetime import datetime,timezone,timedelta
from pathlib import Path
import unittest

from trustfolio_video.contract import Blocked
from trustfolio_video.washing30 import build30, verify_reference_images

def verified_topfive():
    now=datetime.now(timezone.utc).isoformat()
    products=[]
    for rank in range(1,6):
        products.append({
            "id":f"{rank:024x}","rank":rank,"title":f"Verified Test Model {rank}",
            "brand":f"Brand{rank}","platform":"Sample retailer",
            "price_inr":39000-rank*2000,
            "in_stock":True,"price_source":"website_live_price_api",
            "live_price_status":"ok",
            "main_image":"https://m.media-amazon.com/images/I/test.jpg",
            "specifications":{"capacity":f"{rank+5} kg","promotional_claim":"Cures allergies"},
        })
    return {"campaign":{"category":"washing-machines","budget":40000,"brand":"","mode":"budget"},
            "products":products,"source_sha256":"a"*64,"observed_at":now}

class NineSceneDynamicStoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.references=verify_reference_images()

    def make(self,approved=None):
        return build30(approved or verified_topfive(),references=self.references)

    def test_exact_nine_30s_sections_and_fixed_cta(self):
        plan=self.make()
        self.assertEqual(9,len(plan["scenes"]))
        self.assertEqual([(0,3),(3,6),(6,10),(10,14),(14,18),(18,22),(22,26),(26,28),(28,30)],
                         [(s["start"],s["end"]) for s in plan["scenes"]])
        self.assertEqual([5,4,3,2,1],[s["dynamic"]["rank"] for s in plan["scenes"][2:7]])
        self.assertEqual("https://www.trustfolio.in",plan["scenes"][8]["url"])
        self.assertEqual("happy_smiling_pointing_phone",plan["scenes"][8]["emotion"])
        self.assertEqual(False,plan["publishing_enabled"])
        self.assertEqual(False,plan["runpod_gpu_launch_approved"])
        self.assertTrue(all(s["must_erase_all_baked_text_and_products"] for s in plan["scenes"]))

    def test_rank_product_price_and_source_ids_are_bound_not_reference(self):
        plan=self.make()
        for scene in plan["scenes"][2:7]:
            p=scene["dynamic"]
            expected=39000-p["rank"]*2000
            self.assertEqual(p["price_inr"],expected)
            self.assertEqual(p["source_product_id"],f'{p["rank"]:024x}')
            self.assertEqual(p["verified_spec"]["claim_level"],"catalog_spec_only_not_independently_tested")
            self.assertNotIn("Cures allergies",str(scene))
            self.assertNotIn("Haier",str(scene))
            self.assertNotIn("₹ 38,990",str(scene))

    def test_missing_live_price_or_out_of_budget_refuses(self):
        for key,val in (("live_price_status","error"),("price_inr",45000),("in_stock",False)):
            with self.subTest(key=key):
                a=verified_topfive()
                a["products"][0][key]=val
                with self.assertRaises(Blocked):self.make(a)

    def test_stale_snapshot_refuses(self):
        x=verified_topfive()
        x["observed_at"]=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
        with self.assertRaisesRegex(Blocked,"expired"):self.make(x)

    def test_duplicate_rank_and_bad_hash_refuse(self):
        a=verified_topfive()
        a["products"][4]["rank"]=1
        with self.assertRaises(Blocked):self.make(a)
        a=verified_topfive();a["source_sha256"]="not-valid"
        with self.assertRaises(Blocked):self.make(a)

    def test_all_nine_real_reference_assets_present(self):
        self.assertEqual(9,len(self.references))
        self.assertEqual(9,len({r["sha256"] for r in self.references}))
        for r in self.references:self.assertTrue(Path(r["path"]).is_file())

    def test_no_brand_hardcoding_after_swapping_all_five(self):
        x=verified_topfive()
        for i,p in enumerate(x["products"]):
            p["title"]=f"Changed Unique SKU {i}"
            p["brand"]=f"FreshBrand{i}"
        plan=self.make(x)
        names=[x["dynamic"]["title"] for x in plan["scenes"][2:7]]
        self.assertEqual(["Changed Unique SKU 4","Changed Unique SKU 3","Changed Unique SKU 2",
                          "Changed Unique SKU 1","Changed Unique SKU 0"],names)

if __name__=="__main__":unittest.main()
