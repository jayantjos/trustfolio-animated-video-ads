"""No-charge SHA guard and safety checks for RunPod S3 scene staging."""
from datetime import datetime,timezone
import unittest
from trustfolio_video.washing30 import build30,verify_reference_images
from scripts.stage_washing30_s3 import run,validate_stage

def approved():
    products=[]
    for r in range(1,6):
        products.append({"id":f"{r:024x}","rank":r,"title":f"QA Washing Product {r}",
                         "brand":f"TestBrand{r}","price_inr":30000+r*1000,
                         "platform":"QA Shop","in_stock":True,
                         "price_source":"website_live_price_api","live_price_status":"ok",
                         "main_image":"https://m.media-amazon.com/images/I/test.jpg",
                         "specifications":{}})
    return {"campaign":{"category":"washing-machines","budget":40000,"mode":"budget","brand":""},
            "products":products,"source_sha256":"a"*64,
            "observed_at":datetime.now(timezone.utc).isoformat(),
            "live_price_refresh_completed":True,"live_price_count":5,"catalog_fallback_count":0}

class StageTest(unittest.TestCase):
    def test_manifest_9_shas_and_private_qas(self):
        story=build30(approved(),references=verify_reference_images())
        report=run(story,dry_run=True)
        self.assertEqual(report["status"],"DRY_RUN_VERIFIED")
        self.assertEqual(9,len(report["assets"]))
        self.assertFalse(report["gpu_created"])
        self.assertFalse(report["published"])
        self.assertIn(story["campaign_id"],report["manifest_key"])
        self.assertEqual(64,len(report["manifest_sha256"]))
    def test_malformed_reference_rejected(self):
        story=build30(approved(),references=verify_reference_images())
        story["scenes"][2]["reference_sha256"]="0"*64
        with self.assertRaises(AssertionError):
            run(story,dry_run=True)
    def test_invalid_publication_flag_rejected(self):
        story=build30(approved(),references=verify_reference_images())
        story["publishing_enabled"]=True
        with self.assertRaises(AssertionError):
            run(story,dry_run=True)

if __name__=="__main__":unittest.main()
