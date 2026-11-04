import unittest
from pathlib import Path
import tempfile,json,hashlib
from final_master.scripts.release_gate import check

class GateTests(unittest.TestCase):
 def test_incomplete_git_video_never_publishes(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[];snap="a"*64
   for i in range(1,6):
    p=Path(d)/f"rank_{i:02d}.wav";p.write_bytes(b"RIFF"+bytes([i])*60)
    (Path(d)/f"rank_{i:02d}.json").write_text(json.dumps({"rank":i,"product_id":str(i),
      "source_snapshot_sha256":snap,"wav_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
      "seconds":7.2,"fits_ten_seconds":True,"voice_approved":False}))
    rows.append({"rank":i,"product_id":str(i),"price_label":"LIVE","live_price_status":"ok","image_url":"https://example.com/x.png"})
   payload={"products":rows,"budget_inr":35000,"snapshot_sha256":snap}
   r=check(payload,d,{"duration_seconds":82.12,"source_snapshot_sha256":snap})
   self.assertFalse(r["publish_allowed"])
   self.assertNotIn("invalid natural-duration video",r["failures"])
   self.assertIn("required original scenes or product chapters missing",r["failures"])
   self.assertTrue(any("lip_sync_verified" in f for f in r["failures"]))
 def test_product_voice_mismatch_blocks(self):
  r=check({"products":[],"budget_inr":35000,"snapshot_sha256":"a"*64},"/missing",{})
  self.assertFalse(r["publish_allowed"])
  self.assertTrue(r["failures"])
if __name__=="__main__":unittest.main()
