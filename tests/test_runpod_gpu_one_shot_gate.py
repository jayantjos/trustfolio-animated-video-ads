import copy,json,unittest
from pathlib import Path
from scripts.runpod_gpu_one_shot_gate import require_safe,Unsafe
class SafetyGate(unittest.TestCase):
    def setUp(self):self.p=json.loads(Path("config/runpod_gpu_one_shot_policy.json").read_text())
    def test_current_state_never_rents_gpu(self):
        with self.assertRaisesRegex(Unsafe,"GPU_SPEND"):require_safe(self.p)
    def test_reject_wrong_network_volume(self):
        self.p["network_volume_id"]="some_other_id"
        with self.assertRaisesRegex(Unsafe,"WRONG_PERSISTENT"):require_safe(self.p)
    def test_reject_no_reaper(self):
        self.p["must_independent_reaper"]=False
        with self.assertRaisesRegex(Unsafe,"MISSING_GUARD"):require_safe(self.p)
    def test_reject_publishing(self):
        self.p["publishing_enabled"]=True
        with self.assertRaisesRegex(Unsafe,"PUBLISHING"):require_safe(self.p)
    def test_reject_multiple_or_long_lived_pods(self):
        self.p["max_concurrent_pods"]=2
        with self.assertRaisesRegex(Unsafe,"ONE_POD"):require_safe(self.p)
if __name__=="__main__":unittest.main()
