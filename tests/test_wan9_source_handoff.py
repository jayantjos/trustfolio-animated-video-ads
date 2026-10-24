"""Nine reference-only images and story must map exactly into RunPod S3 handoff."""
import unittest,copy
from datetime import datetime,timezone
from trustfolio_video.washing30 import build30,verify_reference_images
from scripts.wan9_stage_source_handoff import build_payload,canonical

def build_fixture():
    products=[]
    for i in range(1,6):
        products.append({"id":f"{i:024x}","rank":i,"title":f"Verified Example Washer {i}",
            "brand":f"Brand{i}","platform":"Example retailer","price_inr":40000-i*500,
            "in_stock":True,"main_image":"https://m.media-amazon.com/images/I/image.jpg",
            "price_source":"website_live_price_api","live_price_status":"ok"})
    story=build30({"campaign":{"category":"washing-machines","budget":40000,"brand":"","mode":"budget"},
        "products":products,"source_sha256":"b"*64,
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "live_price_refresh_completed":True,"live_price_count":5,"catalog_fallback_count":0},
        references=verify_reference_images())
    refs=verify_reference_images()
    stage={"assets":[{"source":x["path"],"key":"videos/private-qa/test/"+x["path"].split("/")[-1],
                       "sha256":x["sha256"],"bytes":100000} for x in refs],
           "manifest_key":"videos/private-qa/test/manifest.json",
           "manifest_sha256":"a"*64}
    return story,stage

class TestBridge(unittest.TestCase):
    def test_nine_uploads_match_reference_hashes_and_3d_prompts(self):
        story,stage=build_fixture()
        result=build_payload(story,stage)
        self.assertEqual(9,len(result["shots"]))
        self.assertEqual([f"scene{i:02d}" for i in range(1,10)],
                         [x["scene"] for x in result["shots"]])
        self.assertEqual(30,result["total_duration_seconds"])
        self.assertEqual([5,4,3,2,1],result["ranking_order_in_scenes"])
        self.assertEqual("https://www.trustfolio.in",result["cta_website"])
        self.assertTrue(all(x["not_safe_directly_as_wan_image"] for x in result["shots"]))
        self.assertFalse(result["gpu_input_manifest_built"])
        self.assertFalse(result["paid_gpu_authorized"])
        self.assertNotIn(b"Test retailer",canonical(result))
    def test_reject_wrong_reference_hash(self):
        story,stage=build_fixture()
        stage["assets"][3]["sha256"]="0"*64
        with self.assertRaisesRegex(Exception,"INCONSISTENT"):
            build_payload(story,stage)
    def test_unchanged_price_fallback_is_not_in_prompts(self):
        story,stage=build_fixture()
        story["scenes"][2]["dynamic"]["price_inr"]=32323
        result=build_payload(story,stage)
        self.assertNotIn("32323",canonical(result).decode())
        self.assertNotIn("Brand5",canonical(result).decode())
if __name__=="__main__":unittest.main()
