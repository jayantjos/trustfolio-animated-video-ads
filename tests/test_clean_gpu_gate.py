"""Production plates must be clean even when reference asset ZIP is valid."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,tempfile,unittest
from PIL import Image

from trustfolio_video.contract import Blocked
from trustfolio_video.washing30 import build30,verify_reference_images
from trustfolio_video.clean_gpu_gate import validate_clean_plates

def live_fixture():
    products=[]
    for i in range(1,6):
        products.append(dict(id=f"{i:024x}",rank=i,title=f"Sample unit {i}",
            brand=f"SampleBrand{i}",platform="Sample test retailer",main_image="https://m.media-amazon.com/images/I/image.jpg",
            price_inr=40000-i*1000,price_source="website_live_price_api",
            live_price_status="ok",in_stock=True))
    data={"campaign":{"category":"washing-machines","budget":40000,"mode":"budget","brand":""},
          "products":products,"source_sha256":"a"*64,
          "observed_at":datetime.now(timezone.utc).isoformat(),
          "live_price_refresh_completed":True,"live_price_count":5,"catalog_fallback_count":0}
    return build30(data,references=verify_reference_images())

class CleanGateTests(unittest.TestCase):
    def test_generated_candidates_never_grant_pod(self):
        story=live_fixture()
        manifest={"version":1,"num_scenes":9,"new_gpu_authorized":False,"scenes":[]}
        for i in range(1,10):
            manifest["scenes"].append(dict(scene_id=f"scene{i:02d}",status="CREATIVE_PLATE_CANDIDATE_NOT_YET_CLEARED_FOR_GPU",
                expression_visual_qa_approved=False,contains_no_baked_brand_guaranteed=False,
                visual_sha256="a"*64,path="output/clean-plates/scene.png"))
        with self.assertRaisesRegex(Blocked,"EXPRESSION_VISUAL_QA_REQUIRED"):
            validate_clean_plates(story,manifest)

    def test_verified_png_signed_candidate_can_be_prepared_cpu_only(self):
        story=live_fixture()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            records=[]
            dummy_png=root/"generic_test_pixels.png"\n            Image.effect_noise((720,1280),60).convert("RGB").save(dummy_png)
            for i in range(1,10):
                p=root/f"scene{i:02d}.png";p.write_bytes(dummy_png.read_bytes())
                records.append({"scene_id":f"scene{i:02d}","path":str(p),
                    "visual_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                    "expression_visual_qa_approved":True,
                    "contains_no_baked_brand_guaranteed":True,
                    "character_identity_match_approved":True,
                    "status":"CLEAN_TEXT_FREE_PLATE_HUMAN_QA_APPROVED"})
            meta={"version":1,"num_scenes":9,"new_gpu_authorized":False,"scenes":records}
            got=validate_clean_plates(story,meta)
            self.assertEqual("CLEAN_WAN_I2V_PLATES_VERIFIED_NO_GPU_CREATED",got["status"])
            self.assertEqual(9,len(got["clean_plates"]))
            self.assertFalse(got["paid_gpu_authorized"])
            records[5]["visual_sha256"]="0"*64
            with self.assertRaisesRegex(Blocked,"SHA_UNVERIFIED"):
                validate_clean_plates(story,meta)
            records[5]["visual_sha256"]=hashlib.sha256((root/"scene06.png").read_bytes()).hexdigest()
            records[5]["contains_no_baked_brand_guaranteed"]=False
            with self.assertRaisesRegex(Blocked,"BAKED_BRAND_TEXT_NOT_CLEARED"):
                validate_clean_plates(story,meta)

if __name__=="__main__": unittest.main()
