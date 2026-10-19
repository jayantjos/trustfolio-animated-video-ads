"""Director tests: 20 distinct film motifs x three genuine ad modes.

Synthetic products here are test fixtures only; no demo claims from fixtures
are ever published, voiced, or used as product recommendations.
"""
import copy
import json
from pathlib import Path
import unittest

from trustfolio_video.cinematic_director import WORLD_ACTION, cinematic_plan
from trustfolio_video.contract import Blocked

ROOT=Path(__file__).resolve().parents[1]
MASTER=json.loads((ROOT/"config/category_education_30.json").read_text("utf-8"))
ACTIVE=[x for x in MASTER["slots"] if x["enabled"]]

def fixture(category,mode):
    brand="Samsung" if mode=="brand_budget" else ""
    return {
       "campaign":{"category":category,"mode":mode,"budget":35000,"brand":brand},
       "source_sha256":"a"*64,"demo_only":True,
       "products":[{
          "id":f"{i:024x}","rank":i,"price_inr":19999+i,
          "brand":brand or "Example","title":f"TEST MODEL {i}",
          "platform":"croma","specifications":{"Capacity":"7 kg","Energy Rating":"5 Star"},
          "is_active":True,"in_stock":True
       } for i in range(1,6)]
    }

class CinematicDirectorTests(unittest.TestCase):
    def test_twenty_unique_story_actions_and_camera_worlds(self):
        self.assertEqual(len(ACTIVE),20)
        self.assertEqual(set(WORLD_ACTION),{x["backend_slug"] for x in ACTIVE})
        self.assertEqual(len({x[0] for x in WORLD_ACTION.values()}),20)
        self.assertEqual(len({x[3] for x in WORLD_ACTION.values()}),20)

    def test_60_category_mode_combinations_source_bound(self):
        count=0
        for cat in ACTIVE:
            for mode in ("budget","brand_budget","comparison"):
                with self.subTest(category=cat["backend_slug"],mode=mode):
                    approved=fixture(cat["backend_slug"],mode)
                    result=cinematic_plan(approved,master=MASTER)
                    self.assertEqual(result["status"],"DIRECTOR_SHOT_PLAN_NOT_A_RENDERED_MOVIE")
                    self.assertFalse(result["video_created"])
                    self.assertFalse(result["publishing_enabled"])
                    self.assertEqual(result["source_sha256"],approved["source_sha256"])
                    self.assertEqual(result["ranked_source_ids"],[x["id"] for x in approved["products"]])
                    self.assertEqual(result["format"]["seconds"],30)
                    self.assertEqual(len(result["shots"]),9)
                    self.assertEqual([x["rank"] for x in result["shots"] if "rank" in x],[5,4,3,2,1])
                    self.assertEqual(result["shots"][0]["shot"],"human_problem_hook")
                    self.assertEqual(result["shots"][-1]["shot"],"trustfolio_branded_cta")
                    self.assertEqual(result["shots"][6]["end_sec"],22)
                    self.assertEqual(result["shots"][7]["start_sec"],22)
                    for shot in result["shots"]:
                        self.assertLess(shot["start_sec"],shot["end_sec"])
                    for shot in result["shots"][2:7]:
                        self.assertIn(shot["partner_product_id"],result["ranked_source_ids"])
                        self.assertIn(shot["product_id"],result["ranked_source_ids"])
                        for fact in shot["spec_claims"]:
                            self.assertEqual(fact["source_product_id"],shot["product_id"])
                    count+=1
        self.assertEqual(count,60)

    def test_three_modes_have_distinct_hooks(self):
        cat="washing-machines"
        hooks=[cinematic_plan(fixture(cat,mode),master=MASTER)["shots"][0]["dialogue"]
               for mode in ("budget","brand_budget","comparison")]
        self.assertEqual(len(set(hooks)),3)

    def test_brand_squad_cross_brand_is_blocked(self):
        approved=fixture("smart-phones","brand_budget")
        approved["products"][2]["brand"]="Other"
        with self.assertRaises(Blocked):
            cinematic_plan(approved,master=MASTER)

    def test_price_above_budget_cannot_be_used(self):
        approved=fixture("washing-machines","budget")
        approved["products"][0]["price_inr"]=49999
        with self.assertRaises(Blocked):
            cinematic_plan(approved,master=MASTER)

    def test_rank_reordering_refused(self):
        approved=fixture("washing-machines","comparison")
        approved["products"].reverse()
        with self.assertRaises(Blocked):
            cinematic_plan(approved,master=MASTER)

    def test_disabled_creative_category_refused(self):
        approved=fixture("future-cameras","budget")
        with self.assertRaises(Blocked):
            cinematic_plan(approved,master=MASTER)

    def test_story_does_not_claim_better_without_evidence(self):
        approved=fixture("washing-machines","budget")
        for prod in approved["products"]:
            prod["specifications"]={}
        plan=cinematic_plan(approved,master=MASTER)
        self.assertTrue(all(x["verified_feature"] is None for x in plan["shots"][2:7]))
        self.assertTrue(all("सत्यापित नहीं" in x["dialogue"] for x in plan["shots"][2:7]))

if __name__=="__main__":
    unittest.main()
