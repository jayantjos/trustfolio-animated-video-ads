"""Regression tests for safety-separated cartoon demo renderer."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from trustfolio_video.contract import Blocked, canonical, validate
from trustfolio_video.demo import approve_historical_demo
from trustfolio_video.cartoon import render_frame, DIALOGUE, W, H
from trustfolio_video.storyboard import validate_registry


ROOT = Path(__file__).resolve().parents[1]

def saved(name):
    return json.loads((ROOT/"evidence"/name).read_text(encoding="utf8"))

def rehash(snapshot):
    snapshot["response_sha256"] = hashlib.sha256(canonical(snapshot["response"]).encode()).hexdigest()

class HistoricalDemoTests(unittest.TestCase):
    cases=(
        ("washing-machines-snapshot.json","washing-machines","budget"),
        ("smart-phones-snapshot.json","smart-phones","brand_budget"),
        ("headphones-earbuds-snapshot.json","headphones-earbuds","comparison")
    )
    def test_three_real_snapshots_are_demo_only(self):
        for filename,category,mode in self.cases:
            with self.subTest(category=category):
                original=saved(filename)
                result=approve_historical_demo(original)
                self.assertEqual(result["campaign"]["mode"],mode)
                self.assertEqual(result["campaign"]["category"],category)
                self.assertEqual([p["id"] for p in result["products"]],
                                 [p["id"] for p in original["response"]["data"]["products"]])
                self.assertFalse(result["publishing_enabled"])
                self.assertTrue(result["demo_only"])
                self.assertIn("NOT FOR PUBLICATION",result["watermark"])
                self.assertEqual(len(result["price_evidence"]),5)
                # Historical validation must not accidentally approve missing price evidence.
                with self.assertRaises(Blocked):
                    validate(original)
    def test_tampered_snapshot_rejected(self):
        snap=saved(self.cases[0][0])
        snap["response"]["data"]["products"][0]["price_inr"]=100
        with self.assertRaisesRegex(Blocked,"tampered"):
            approve_historical_demo(snap)
    def test_no_client_side_reranking(self):
        snap=saved(self.cases[0][0])
        snap["response"]["data"]["products"].reverse()
        rehash(snap)
        with self.assertRaisesRegex(Blocked,"ranking"):
            approve_historical_demo(snap)
    def test_out_of_budget_rejected(self):
        snap=saved(self.cases[0][0])
        snap["response"]["data"]["products"][0]["price_inr"]=35001
        rehash(snap)
        with self.assertRaisesRegex(Blocked,"over budget"):
            approve_historical_demo(snap)
    def test_wrong_brand_rejected(self):
        snap=saved(self.cases[1][0])
        snap["response"]["data"]["products"][2]["brand"]="Other"
        rehash(snap)
        with self.assertRaisesRegex(Blocked,"different brand"):
            approve_historical_demo(snap)
    def test_untrusted_image_rejected(self):
        snap=saved(self.cases[0][0])
        snap["response"]["data"]["products"][0]["main_image"]="http://127.0.0.1/test"
        rehash(snap)
        with self.assertRaisesRegex(Blocked,"image origin"):
            approve_historical_demo(snap)
    def test_frames_change_with_character_pose_and_category(self):
        frames=[]
        for name,_,_ in self.cases:
            approved=approve_historical_demo(saved(name))
            blank={p["id"]:None for p in approved["products"]}
            im=render_frame(approved,blank,2,3.0,15,approved["campaign"]["category"])
            self.assertEqual(im.size,(W,H))
            frames.append(hashlib.sha256(im.tobytes()).hexdigest())
            other=render_frame(approved,blank,2,3.16,15,approved["campaign"]["category"])
            self.assertNotEqual(im.tobytes(),other.tobytes())
        self.assertEqual(len(set(frames)),3)
    def test_three_distinct_hinglish_pilot_scripts(self):
        scripts=[tuple(DIALOGUE[name]) for _,name,_ in self.cases]
        self.assertEqual(len(set(scripts)),3)
        self.assertTrue(all(len(s)==7 for s in scripts))
    def test_registry_still_twenty_enabled_and_ten_disabled(self):
        reg=json.loads((ROOT/"config/worlds.json").read_text())
        self.assertEqual(validate_registry(reg),20)
        self.assertEqual(sum(not x["enabled"] for x in reg["categories"]),10)

if __name__=="__main__":
    unittest.main()
