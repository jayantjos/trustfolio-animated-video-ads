import unittest
from datetime import datetime,timezone
from scripts.runpod_video_pod_watchdog import owned_stale_pods
NOW=datetime(2026,10,21,13,0,tzinfo=timezone.utc)
def pod(name="trustfolio-video-washing-20261021-001",vol="1bch597yrz",at="2026-10-21T12:00:00Z"):
 return {"name":name,"id":"abc123xyz","mounts":{"network":[{"volumeId":vol,"path":"/workspace"}]},
         "createdAt":at,"status":"RUNNING"}
class WatchdogTests(unittest.TestCase):
 def test_own_stale_flags_alert(self):
    r=owned_stale_pods([pod()],now=NOW)
    self.assertEqual(len(r),1)
    self.assertEqual(r[0]["age_minutes"],60)
 def test_never_match_other_owners(self):
    self.assertFalse(owned_stale_pods([pod(name="other-user-gpu")],now=NOW))
 def test_never_match_wrong_volume(self):
    self.assertFalse(owned_stale_pods([pod(vol="foreign")],now=NOW))
 def test_recent_job_no_alarm(self):
    self.assertFalse(owned_stale_pods([pod(at="2026-10-21T12:50:00Z")],now=NOW))
if __name__=="__main__":unittest.main()
