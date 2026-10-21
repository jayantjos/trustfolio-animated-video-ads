import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from trustfolio_video.contract import Blocked
from trustfolio_video.fixed_pilot import check_registry,create_plan,verify_hero
from trustfolio_video.hindi_voice import google_cloud_mp3

class FixedPilotTests(unittest.TestCase):
    def test_all_twenty_have_unique_cast_and_world(self):
        result=check_registry()
        self.assertEqual(len(result),20)
        self.assertEqual(result["washing-machines"]["character_id"],
                         "trustfolio-washing-machines-lead-v1")
        self.assertEqual(len({x["world"] for x in result.values()}),20)
    def test_pilot_is_complete_story_but_not_a_fake_render(self):
        job=create_plan()
        self.assertEqual(len(job["scenes"]),4)
        self.assertEqual(sum(x["seconds"] for x in job["scenes"]),30)
        self.assertEqual(job["scenes"][2]["rank_order"],[5,4,3,2,1])
        self.assertFalse(job["production_publishing"])
        self.assertFalse(job["gpu_ran"])
        self.assertFalse(job["lip_sync_verified"])
        self.assertEqual(job["ranked_source_ids"],[])
        self.assertTrue(job["missing_assets"])
    def test_wrong_cast_or_disabled_slot_fails_closed(self):
        cast=json.loads(Path("config/characters_fixed.json").read_text())
        cast["categories"][0]["hero_asset"]=cast["categories"][1]["hero_asset"]
        with self.assertRaises(Blocked):check_registry(cast=cast)
        with self.assertRaises(Blocked):create_plan(category="unknown")
        with self.assertRaises(Blocked):create_plan(category="smart-phones")
    def test_canonical_hero_hash_must_match(self):
        with tempfile.TemporaryDirectory() as d:
            image=Path(d)/"hero.png";image.write_bytes(b"wrong")
            with self.assertRaises(Blocked):verify_hero(image,"0"*64)
    def test_google_tts_is_disabled_before_any_request(self):
        with tempfile.TemporaryDirectory() as d:
            def forbidden(*args,**kwargs):
                raise AssertionError("no billed API should be called")
            with self.assertRaises(Blocked):
                google_cloud_mp3("नमस्ते",Path(d)/"voice.mp3",environ={},opener=forbidden)
            self.assertFalse((Path(d)/"voice.mp3").exists())
    def test_google_tts_requires_token_even_after_billing_ack(self):
        with self.assertRaises(Blocked):
            google_cloud_mp3("नमस्ते","/tmp/trustfolio-test-voice.mp3",
              environ={"TRUSTFOLIO_ALLOW_BILLABLE_TTS":"I_ACCEPT_POSSIBLE_CHARGES"})

if __name__=="__main__":unittest.main()
