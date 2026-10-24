from datetime import datetime, timezone
import hashlib
import tempfile
from pathlib import Path
import unittest

from trustfolio_video.washing30 import build30,verify_reference_images
from trustfolio_video.final_motion_gate import verify_final_motion_inputs
from trustfolio_video.contract import Blocked

def fixture():
    p=[]
    for i in range(1,6):
        p.append({"id":f"{i:024x}","rank":i,"title":f"Demo {i}kg model {i}","brand":f"TEST{i}",
            "platform":"Example shop","main_image":"https://m.media-amazon.com/images/I/example.jpg",
            "price_inr":40000-i*500,"price_source":"website_live_price_api","live_price_status":"ok","in_stock":True})
    return build30({"campaign":{"category":"washing-machines","budget":40000,"mode":"budget","brand":""},
                    "products":p,"source_sha256":"b"*64,"observed_at":datetime.now(timezone.utc).isoformat(),
                    "live_price_refresh_completed":True,"live_price_count":5,"catalog_fallback_count":0},
                    references=verify_reference_images())

class FinalGuardTest(unittest.TestCase):
    def test_missing_clips_fails_closed(self):
        r=verify_final_motion_inputs(fixture(),[],{},qa={})
        self.assertEqual("FINAL_3D_VIDEO_NOT_READY",r["status"])
        self.assertIn("REQUIRE_NINE_GPU_RECEIPTS",r["missing_requirements"])
        self.assertIn("HUMAN_HINDI_QA_REQUIRED",r["missing_requirements"])
        self.assertFalse(r["publish_allowed"])

    def test_receipt_requires_original_gpu_and_s3_content_hash(self):
        from trustfolio_video.wan5_nineshot import verified_plan
        story=fixture()
        plan=verified_plan(story)
        with tempfile.TemporaryDirectory() as td:
            recs=[];files={}
            for scene in plan["shots"]:
                sid=scene["scene_id"]
                data=(b"not real MP4, unit fixture:"+sid.encode())*500
                f=Path(td)/(sid+".mp4")
                f.write_bytes(data)
                files[sid]=str(f)
                recs.append({"scene_id":sid,"sha256":hashlib.sha256(data).hexdigest(),
                    "bytes":len(data),"model":"Wan2.2-TI2V-5B",
                    "source_campaign_id":plan["campaign_id"],"motion_job_hash":plan["motion_job_hash"],
                    "scene_source_reference_sha256":scene["source_storyboard_sha256"],
                    "private_qa":True,"lip_sync_claimed":False,"s3_get_sha256_verified":True,
                    "pod_deleted_get_404":True,"public_publishing":False})
            qa=dict(hindi_narration_human_listening_approved=True,
                scene01_lipsync_verified=True,scene09_lipsync_verified=True,
                all_nine_motion_consistency_approved=True,
                cta_readable_and_final_two_seconds=True,
                no_fake_claims_or_baked_sample_prices=True)
            result=verify_final_motion_inputs(story,recs,files,qa)
            self.assertEqual("FINAL_RENDER_MEDIA_INPUTS_VERIFIED_PRIVATE_QA",result["status"])
            self.assertFalse(result["publish_allowed"])
            recs[2]["s3_get_sha256_verified"]=False
            self.assertIn("scene03_MISSING_REMOTE_VERIFY_OR_CLEANUP",
                          verify_final_motion_inputs(story,recs,files,qa)["missing_requirements"])
            recs[2]["s3_get_sha256_verified"]=True
            Path(files["scene04"]).write_bytes(b"tampered")
            self.assertIn("scene04_LENGTH_MISMATCH",
                          verify_final_motion_inputs(story,recs,files,qa)["missing_requirements"])
            recs[4]["model"]="fake"
            self.assertIn("scene05_UNTRUSTED_GPU_PROVENANCE",
                          verify_final_motion_inputs(story,recs,files,qa)["missing_requirements"])

if __name__=="__main__":unittest.main()
