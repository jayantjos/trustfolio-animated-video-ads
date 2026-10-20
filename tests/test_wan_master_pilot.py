"""Real-asset SHA, private GPU gate and source-bound character-pilot tests."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from trustfolio_video.wan_master_pilot import (
    WAN_SHA,STORY_SHA,PARADE_SHA,MASTER_SHA,MODEL,PROMPTS,
    file_hash,guard_file,cuda_report,prepare,secure_real_run
)

ROOT=Path(__file__).resolve().parents[1]

class WanMasterPilotTests(unittest.TestCase):
    def test_verified_source_sha_receipts_are_fixed(self):
        self.assertEqual(len({STORY_SHA,PARADE_SHA,MASTER_SHA}),3)
        for sha in (STORY_SHA,PARADE_SHA,MASTER_SHA,WAN_SHA):
            self.assertEqual(len(sha),40 if sha==WAN_SHA else 64)
            self.assertTrue(all(ch in "0123456789abcdef" for ch in sha))

    def test_lady_and_machine_prompts_are_not_generic(self):
        self.assertEqual(set(PROMPTS),{"lady","washer"})
        self.assertIn("pink kurta",PROMPTS["lady"])
        self.assertIn("fingers",PROMPTS["lady"])
        self.assertIn("independently moving shoes and arms",PROMPTS["washer"])
        self.assertIn("no prices",PROMPTS["washer"].casefold())
        self.assertIn("no additional characters",PROMPTS["lady"].casefold())

    def test_modified_art_gets_rejected(self):
        with TemporaryDirectory() as work:
            file=Path(work)/"wrong-reference.png"
            file.write_bytes(b"not the approved master art")
            self.assertNotEqual(file_hash(file),MASTER_SHA)
            with self.assertRaises(ValueError):
                guard_file(file,MASTER_SHA)

    def test_no_late_api_cost_or_fake_gpu_preview(self):
        cap=cuda_report()
        self.assertIn("cuda_available",cap)
        self.assertEqual(cap["minimum_required_vram_gb"],24)
        with self.assertRaisesRegex(RuntimeError,"explicit"):
            secure_real_run("missing","missing","missing","missing",acknowledge=False)

    def test_missing_model_does_not_proceed_to_generation(self):
        cap=cuda_report()
        if not cap["gpu_meets_requirement"]:
            with self.assertRaisesRegex(RuntimeError,">=24GB"):
                secure_real_run("missing","missing","missing","missing",acknowledge=True)

    def test_no_forced_external_install_or_social_access(self):
        source=(ROOT/"trustfolio_video"/"wan_master_pilot.py").read_text(encoding="utf8")
        for forbidden in ("pip install","curl -fsSL","instagram.com",
                          "graph.facebook.com","youtube.videos.insert"):
            self.assertNotIn(forbidden,source)
        self.assertIn("if commit!=WAN_SHA",source)
        self.assertIn('"publishing_enabled":False',source)

    def test_prepare_with_simulated_preapproved_input(self):
        # Tests the crop and output manifest without needing to commit images
        # or claim that mock pixels are real product photographs.
        from PIL import Image
        with TemporaryDirectory() as work:
            dir=Path(work)
            for name,dim in (("story.png",(941,1672)),("parade.png",(941,1672)),
                             ("master.png",(1024,1536))):
                Image.new("RGB",dim,(90,120,155)).save(dir/name)
            def fake_guard(path,sha):
                return Path(path)
            with patch("trustfolio_video.wan_master_pilot.guard_file",fake_guard):
                data=prepare(dir/"story.png",dir/"parade.png",dir/"master.png",dir/"out")
            self.assertEqual(len(data["shots"]),2)
            self.assertTrue(data["style_frozen"])
            self.assertEqual(data["gpu_min_vram_gb"],24)
            self.assertFalse(data["publishing_enabled"])
            self.assertTrue(data["no_price_or_rank_claims"])
            for shot in data["shots"]:
                self.assertTrue((dir/"out"/shot["image_file"]).is_file())
                from PIL import Image
                self.assertEqual(Image.open(dir/"out"/shot["image_file"]).size,(704,1280))
                self.assertEqual(file_hash(dir/"out"/shot["image_file"]),shot["image_sha256"])

    def test_production_gate_requires_full_source_hashes(self):
        with TemporaryDirectory() as work:
            base=Path(work)
            for filename in ("lady.png","washer.png","master.png"):
                (base/filename).write_bytes(b"fake art")
            with self.assertRaises(ValueError):
                prepare(base/"lady.png",base/"washer.png",base/"master.png",base/"out")

if __name__=="__main__":
    unittest.main()
