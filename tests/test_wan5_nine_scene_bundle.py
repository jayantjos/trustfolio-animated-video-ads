"""Check transfer from approved creative art to immutable nine-scene GPU input."""
import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
from PIL import Image

from scripts.wan5_nine_scene_bundle import package
from scripts.wan5_nine_scene_gpu_worker import validate_manifest
from trustfolio_video.washing30 import build30,verify_reference_images
from trustfolio_video.contract import Blocked
from trustfolio_video.clean_gpu_gate import sha256

def story():
    data={"campaign":{"category":"washing-machines","budget":40000,"brand":"","mode":"budget"},
          "products":[{
            "id":f"{i:024x}","rank":i,"brand":f"Test{i}","title":f"Test washing unit {i}",
            "platform":"Test retailer","price_source":"website_live_price_api",
            "live_price_status":"ok","in_stock":True,"price_inr":38000-i*1000,
            "main_image":"https://m.media-amazon.com/images/I/fixture.jpg"}
            for i in range(1,6)],
          "source_sha256":"f"*64,
          "live_price_refresh_completed":True,"observed_at":datetime.now(timezone.utc).isoformat()}
    return build30(data,references=verify_reference_images())

class BundleTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
        self.story_path=self.base/"story.json"
        self.story_path.write_text(json.dumps(story()))
        self.platemeta=self.base/"plates.json"
        self.plates=[]
        pic=Image.effect_noise((720,1280),60).convert("RGB")
        for i in range(1,10):
            p=self.base/f"scene{i:02d}.png"
            pic.save(p)
            self.plates.append({"scene_id":f"scene{i:02d}","path":str(p),
              "visual_sha256":sha256(p),
              "status":"CLEAN_TEXT_FREE_PLATE_HUMAN_QA_APPROVED",
              "expression_visual_qa_approved":True,
              "contains_no_baked_brand_guaranteed":True,
              "character_identity_match_approved":True})
        self.doc={"version":1,"num_scenes":9,"new_gpu_authorized":False,"scenes":self.plates}
        self.platemeta.write_text(json.dumps(self.doc))
    def test_cpu_copy_job_ready_no_billing(self):
        out=self.base/"transfer"
        result=package(self.story_path,self.platemeta,out)
        payload=json.loads(result.read_text())
        self.assertFalse(payload["paid_gpu_authorized"])
        self.assertFalse(payload["published"])
        self.assertEqual(9,len(payload["shots"]))
        self.assertEqual(9,len(validate_manifest(payload,root=out)))
        self.assertTrue(all("price" not in s for s in payload["shots"]))
    def test_draft_plate_must_stop(self):
        self.doc["scenes"][2]["expression_visual_qa_approved"]=False
        self.platemeta.write_text(json.dumps(self.doc))
        with self.assertRaisesRegex(Blocked,"EXPRESSION_VISUAL_QA_REQUIRED"):
            package(self.story_path,self.platemeta,self.base/"stop")

if __name__=="__main__":unittest.main()
