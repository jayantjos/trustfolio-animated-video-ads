"""30-category, three-mode educational storyboard and factual-claim safety QA."""
import copy
import json
from pathlib import Path
import unittest
from trustfolio_video.contract import Blocked
from trustfolio_video.demo import approve_historical_demo
from trustfolio_video.educational import (
    load_master, validate_master, exact_facts, build_educational_story
)

ROOT=Path(__file__).resolve().parents[1]

def historical(name):
    return approve_historical_demo(json.loads((ROOT/"evidence"/name).read_text(encoding="utf-8")))

def test_campaign(category, mode, brand="Samsung"):
    spec={"category":category,"budget":35000,"mode":mode,
          "brand":brand if mode=="brand_budget" else ""}
    products=[{
        "id":f"{i:024x}","rank":i,"title":f"TEST fixture model {i}",
        "brand":spec["brand"] if mode=="brand_budget" else "Example",
        "platform":"croma","price_inr":30000+i,
        "product_category":category,"is_active":True,"in_stock":True,
        "specifications":{"Capacity":"7 kg","Energy Rating":"5 Star","Load Type":"Front Load"}
    } for i in range(1,6)]
    return {"campaign":spec,"products":products,"source_sha256":"a"*64,
            "demo_only":True,"publishing_enabled":False}


class CategoryMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master=load_master()
        cls.enabled=validate_master(cls.master)

    def test_exact_twenty_verified_and_ten_disabled(self):
        self.assertEqual(len(self.master["slots"]),30)
        self.assertEqual(len(self.enabled),20)
        self.assertEqual(sum(not p["enabled"] for p in self.master["slots"]),10)
        self.assertTrue(all(p["backend_slug"] is None for p in self.master["slots"][20:]))

    def test_three_modes_and_story_depth_for_each_category(self):
        for cat in self.enabled.values():
            self.assertEqual(set(cat["modes"]),{"budget","brand_budget","comparison"})
            self.assertGreater(len(cat["creative"]["problem_hook"]),15)
            self.assertGreater(len(cat["environment"]["character_action"]),20)
            self.assertGreaterEqual(len(cat["education"]["feature_priority"]),3)
            self.assertIn("causal",cat["education"]["why_best_policy"].casefold())

    def test_unsupported_slot_cannot_become_live(self):
        bad=copy.deepcopy(self.master)
        bad["slots"][20]["enabled"]=True
        bad["slots"][20]["backend_slug"]="power-banks"
        with self.assertRaises(Blocked):
            validate_master(bad)

    def test_wrong_backend_id_is_rejected(self):
        bad=copy.deepcopy(self.master)
        bad["slots"][0]["backend_category_id"]="000000000000000000000000"
        with self.assertRaises(Blocked):
            validate_master(bad)

    def test_missing_category_explanation_rejected(self):
        bad=copy.deepcopy(self.master)
        bad["slots"][1]["education"]["product_role"]=""
        with self.assertRaises(Blocked):
            validate_master(bad)


class ExplanationStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master=load_master()
        cls.enabled=validate_master(cls.master)

    def test_sixty_mode_and_category_combinations_preserve_ranks(self):
        count=0
        for category in self.enabled:
            for mode in ("budget","brand_budget","comparison"):
                with self.subTest(category=category,mode=mode):
                    approved=test_campaign(category,mode)
                    story=build_educational_story(approved,self.master)
                    self.assertEqual(story["campaign"]["mode"],mode)
                    self.assertEqual(story["ranked_source_ids"],[f"{i:024x}" for i in range(1,6)])
                    self.assertEqual([s["rank"] for s in story["scenes"] if "rank" in s],[5,4,3,2,1])
                    self.assertFalse(story["publishing_enabled"])
                    self.assertIn("NOT FOR PUBLICATION",story["watermark"])
                    self.assertEqual(len(story["expanded_product_explanations"]),5)
                    self.assertEqual(len(story["scenes"]),7)
                    for s in story["scenes"]:
                        self.assertLess(s["start"],s["end"])
                        if s.get("evidence"):
                            self.assertEqual(s["evidence"]["source_product_id"],s["product_id"])
                    count+=1
        self.assertEqual(count,60)

    def test_real_historical_washing_specs_source_match(self):
        approved=historical("washing-machines-snapshot.json")
        story=build_educational_story(approved,self.master)
        self.assertEqual(story["campaign"]["mode"],"budget")
        for item in story["expanded_product_explanations"]:
            product=next(p for p in approved["products"] if p["id"]==item["product_id"])
            for fact in item["verified_specs"]:
                self.assertIn(fact["field"],product["specifications"])
                self.assertEqual(fact["value"],str(product["specifications"][fact["field"]]))
                self.assertEqual(fact["source_product_id"],product["id"])
            self.assertIn("scoring factors not supplied",item["why_ranked"])
            self.assertTrue(item["user_fit_is_not_proven"])
        self.assertTrue(story["demo_only"])
        self.assertFalse(story["publishing_enabled"])

    def test_three_historical_category_sources(self):
        for filename in ("washing-machines-snapshot.json","smart-phones-snapshot.json",
                         "headphones-earbuds-snapshot.json"):
            with self.subTest(filename=filename):
                approved=historical(filename)
                story=build_educational_story(approved,self.master)
                self.assertEqual(story["ranked_source_ids"],[p["id"] for p in approved["products"]])
                self.assertEqual(story["source_sha256"],approved["source_sha256"])
                self.assertTrue(all(x["product_id"] in story["ranked_source_ids"] for x in story["expanded_product_explanations"]))
                self.assertFalse(story["publishing_enabled"])

    def test_title_only_unverified_feature_cannot_be_claimed(self):
        cat=self.enabled["washing-machines"]
        fake={"id":"a"*24,"title":"Premium 9kg mega steam performance guarantee",
              "specifications":{}}
        self.assertEqual(exact_facts(fake,cat),[])
        fake["specifications"]={"Marketing tagline":"Best in India", "Capacity":"7 kg"}
        result=exact_facts(fake,cat)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["field"],"Capacity")
        self.assertEqual(result[0]["value"],"7 kg")

    def test_unknown_feature_triggers_evidence_unavailable_fallback(self):
        src=test_campaign("washing-machines","budget")
        for p in src["products"]:p["specifications"]={}
        story=build_educational_story(src,self.master)
        self.assertTrue(all(s["evidence"] is None for s in story["scenes"] if s.get("rank")))
        self.assertTrue(all(not e["verified_specs"] for e in story["expanded_product_explanations"]))
        self.assertTrue(any("सत्यापित नहीं" in s["text"] for s in story["scenes"] if s.get("rank")))

    def test_brand_fallback_refused(self):
        approved=test_campaign("smart-phones","brand_budget")
        approved["products"][0]["brand"]="Other"
        with self.assertRaises(Blocked):
            build_educational_story(approved,self.master)

    def test_budget_overrun_refused(self):
        approved=test_campaign("washing-machines","budget")
        approved["products"][2]["price_inr"]=90000
        with self.assertRaises(Blocked):
            build_educational_story(approved,self.master)

    def test_reordered_top_five_refused(self):
        approved=test_campaign("washing-machines","comparison")
        approved["products"].reverse()
        with self.assertRaises(Blocked):
            build_educational_story(approved,self.master)

    def test_comparison_never_asserts_technical_winner(self):
        approved=test_campaign("washing-machines","comparison")
        story=build_educational_story(approved,self.master)
        for scene in story["scenes"]:
            comp=scene.get("comparison")
            if comp:
                self.assertIn("no winner inferred",comp["claim"])
                self.assertEqual(comp["left"]["value"],"7 kg")
                self.assertEqual(comp["right"]["value"],"7 kg")

    def test_audio_script_timing_and_no_publication(self):
        story=build_educational_story(test_campaign("washing-machines","budget"),self.master)
        self.assertEqual(story["duration_seconds"],30)
        self.assertLessEqual(story["scenes"][-1]["end"],30)
        self.assertTrue(story["audio_notes"]["human_naturalness_approved"] is False)
        self.assertTrue(story["demo_only"])  # approval stays independent of render success


if __name__=="__main__":
    unittest.main()
