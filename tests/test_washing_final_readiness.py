import unittest
import io,hashlib
from unittest.mock import patch
from scripts.washing_final_readiness import audit,audio_file_verified,CHARACTER,HERO_SHA,HERO_SIZE,REQUIRED_SCENES,BUCKET
AUDIO_KEYS=[]
class S3Mock:
    def __init__(self, missing=()):
        self.missing=set(missing)
        self.keys=[]
    def head_object(self, Bucket, Key):
        from botocore.exceptions import ClientError
        self.keys.append(Key)
        if Key in self.missing:
            raise ClientError({"Error":{"Code":"404","Message":"absent"}},"HeadObject")
        if Key==CHARACTER:
            return {"ContentLength":HERO_SIZE,"Metadata":{"sha256":HERO_SHA}}
        if Key in AUDIO_KEYS:
            record=next(r for r in M_AUDIO["clips"] if r["s3_key"]==Key)
            return {"ContentLength":record["bytes"],"Metadata":{"sha256":record["sha256"]}}
        if Key in REQUIRED_SCENES:
            return {"ContentLength":12000}
        return {"ContentLength":next(x["bytes"] for x in M["objects"] if Key.endswith("/"+x["name"]))}
import json
M=json.load(open("config/wan_verified_model_manifest.json"))
M_AUDIO=json.load(open("config/hindi_neural_verified_receipts.json"))
AUDIO_KEYS.extend([r["s3_key"] for r in M_AUDIO["clips"]])
class ReadinessTests(unittest.TestCase):
    def test_all_model_audio_and_scene_presence_does_not_claim_final_video(self):
        c=S3Mock()
        with patch('scripts.washing_final_readiness.audio_file_verified',side_effect=lambda client,clip: clip['s3_key'] not in client.missing):
            result=audit(c,M)
        self.assertEqual(result["model_files_verified"],9)
        self.assertEqual(result["neural_audio_clips_staged"],3)
        self.assertEqual(result["location_art_files_staged"],3)
        self.assertTrue(result["master_original_character_on_s3"])
        self.assertEqual(result["status"],"GPU_RENDER_BLOCKED")
        self.assertFalse(result["gpu_created"])
        self.assertFalse(result["published"])
    def test_missing_master_never_ready(self):
        c=S3Mock(missing={CHARACTER})
        with patch('scripts.washing_final_readiness.audio_file_verified',side_effect=lambda client,clip: clip['s3_key'] not in client.missing):
            result=audit(c,M)
        self.assertIn("MASTER_CHARACTER_NOT_VERIFIED_ON_S3",result["blockers"])
    def test_missing_audio_and_location_detected(self):
        c=S3Mock(missing={AUDIO_KEYS[0],REQUIRED_SCENES[0]})
        with patch('scripts.washing_final_readiness.audio_file_verified',side_effect=lambda client,clip: clip['s3_key'] not in client.missing):
            result=audit(c,M)
        self.assertEqual(result["neural_audio_clips_staged"],2)
        self.assertEqual(result["location_art_files_staged"],2)
    def test_audio_get_hash_verifies_real_bytes_and_rejects_corruption(self):
        body=b'original hindi clip mock'
        class S3Audio:
            def __init__(self,data):self.data=data
            def get_object(self,**kwargs):
                return {'ContentLength':len(self.data),'Body':io.BytesIO(self.data)}
        clip={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'s3_key':'test.mp3'}
        self.assertTrue(audio_file_verified(S3Audio(body),clip))
        self.assertFalse(audio_file_verified(S3Audio(b'incorrect'),clip))
if __name__=="__main__":unittest.main()
