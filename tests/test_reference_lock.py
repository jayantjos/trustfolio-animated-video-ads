"""User-approved cinematic-art contract is frozen across all 20 verified worlds.

Automated checks establish source/format isolation. A human is still required
to judge whether the glossy cartoon quality matches the user's references.
"""
import json
import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/"config"/"approved_premium_3d_visual_contract.json"
WORLDS=ROOT/"config"/"world_motion_20.json"
MASTER=ROOT/"config"/"category_education_30.json"

class UserApprovedPremiumReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.approved=json.loads(REFERENCE.read_text("utf-8"))
        cls.motion=json.loads(WORLDS.read_text("utf-8"))
        cls.categories=json.loads(MASTER.read_text("utf-8"))

    def test_lock_contains_two_reference_images_with_immutable_hashes(self):
        refs=self.approved["reference_assets"]
        self.assertEqual(len(refs),2)
        self.assertEqual(len(set(x["sha256"] for x in refs)),2)
        for asset in refs:
            self.assertRegex(asset["sha256"],r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(asset["width"],1024)
            self.assertGreaterEqual(asset["height"],1400)
        self.assertIn("NOT_YET_ACHIEVED",self.approved["state"])

    def test_exact_twenty_category_styles_in_visual_reference(self):
        intended=self.approved["category_order"]
        self.assertEqual(len(intended),20)
        self.assertEqual(len(set(intended)),20)
        supported={s["backend_slug"] for s in self.categories["slots"] if s["enabled"]}
        rendered={s["slug"] for s in self.motion["enabled_worlds"]}
        self.assertEqual(set(intended),supported)
        self.assertEqual(set(intended),rendered)
        self.assertEqual(sum(not s["enabled"] for s in self.categories["slots"]),10)

    def test_visual_hierarchy_in_every_approved_animation(self):
        visual=self.approved["fixed_brand_contract"]
        self.assertIn("top",visual["logo_position"])
        self.assertIn("bottom",visual["footer_position"])
        self.assertIn("purple",visual["headline"])
        self.assertIn("gold",visual["headline"])
        self.assertRegex(visual["palette"]["gold"],r"^#[0-9A-Fa-f]{6}$")

    def test_motion_is_real_cartoon_acting_not_still_pan_zoom(self):
        recipe=self.approved["story_contract"]
        self.assertEqual(recipe["delivery"],[1080,1920])
        self.assertEqual(recipe["fps"],24)
        self.assertEqual(recipe["durations_seconds"],[15,20,30])
        self.assertGreaterEqual(len(recipe["acting"]),5)
        self.assertGreaterEqual(len(recipe["cinematography"]),4)
        self.assertTrue(any("lip" in x or "mouth" in x for x in recipe["acting"]))
        self.assertTrue(any("5" in x or "five" in x.lower() for x in recipe["scene_roles"]))
        self.assertTrue(any("low-poly" in x for x in recipe["format_rules"]))

    def test_no_technical_qa_can_claim_reference_approval(self):
        approval=self.approved["scene_acceptance"]["current_approval_state"]
        self.assertEqual(set(approval.values()),{False})
        self.assertTrue(self.approved["scene_acceptance"]["block_publishing_if_unapproved"])
        self.assertTrue(self.approved["scene_acceptance"]["showreel_is_not_a_completed_ad"])
        self.assertIn("PRIVATE_DEMO_NOT_FOR_PUBLICATION",self.approved["scene_acceptance"]["expected_status_when_any_missing"])

    def test_commercial_claims_are_gated(self):
        listof=self.approved["fixed_brand_contract"]["prohibited_claims_without_evidence"]
        self.assertIn("Live Prices",listof)
        self.assertIn("Verified Products",listof)
        self.assertIn("Real User Reviews",listof)
        self.assertFalse(self.approved["scene_acceptance"]["current_approval_state"]["all_product_prices_fresh_verified"])

if __name__=="__main__":unittest.main()
