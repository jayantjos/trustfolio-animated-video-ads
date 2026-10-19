"""Approved master theme must be immutable, not mis-sold as a completed 3D ad."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"evidence"/"master_theme_8s_camera_qa.json"
SOURCE=ROOT/"trustfolio_video"/"master_motion.py"

class MasterThemeMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=json.loads(MANIFEST.read_text("utf-8"))
        cls.source=SOURCE.read_text("utf-8")
    def test_final_visual_reference_hashes_locked(self):
        self.assertEqual(self.meta["art_assets"][0]["sha256"],
          "c5ce062090f34ab414a125d91c3ad39ff81f37a8ad4e629726e5ced0f3458ba1")
        self.assertEqual(self.meta["art_assets"][1]["sha256"],
          "bcc90bf85a9c2f4fee8b57b0c02b78e5b80f4c8a184b5d528ccb21a1ca934e0c")
        self.assertIn("input_lock",self.source)
        self.assertIn("do not silently substitute",self.source)
    def test_real_render_not_skeletal_film(self):
        self.assertFalse(self.meta["genuine_skeletal_3d_rigged_chars"])
        self.assertEqual(self.meta["motion_evidence"]["duration_seconds"],8)
        self.assertEqual(self.meta["motion_evidence"]["resolution"],[1080,1920])
        self.assertEqual(self.meta["motion_evidence"]["fps"],24)
        self.assertIn("five cutout",self.meta["motion_evidence"]["technique"].lower().replace("5 cutout","five cutout"))
    def test_source_and_price_claims_protected(self):
        self.assertFalse(self.meta["verified_sku_rank_and_price"])
        self.assertFalse(self.meta["commercial_advertising_asset_rights_verified"])
        self.assertIn("clean_baked_illustrative_prices",self.source)
        self.assertIn("DEMO",self.source)
        self.assertFalse(self.meta["publishing_enabled"])
        self.assertFalse(self.meta["production_approved"])
    def test_renderer_has_actual_motion_not_card_pan(self):
        for token in ("face_layers","CHAR_POLYGONS","animate_layer","camera(stage,t)",
                      "overlay(stage,brand,t)","ffmpeg","-t","24","source"):
            with self.subTest(token=token):
                self.assertIn(token,self.source)
    def test_no_social_or_production_deploy(self):
        for token in ("instagram.upload","youtube.upload","token=os.environ","deploy-prod"):
            self.assertNotIn(token,self.source)
    def test_next_gate_cinematic_quality_not_assumed(self):
        self.assertFalse(self.meta["creative_approval"])
        self.assertFalse(self.meta["human_listened_hindi_naturalness_approved"])
        self.assertIn("low-poly",self.meta["next_acceptance_gate"])
        self.assertGreaterEqual(len(self.meta["blockers"]),5)

if __name__=="__main__":
    unittest.main()
