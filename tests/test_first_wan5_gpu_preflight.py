import unittest
from scripts.first_wan5_gpu_preflight import evaluate,check_catalog,price_within_usd_one

VOL={"id":"1bch597yrz","size":100,"dataCenter":"EU-RO-1","type":"STANDARD"}
P={"gpu_usd_spend_approved":1.0}
M={"objects":[{} for _ in range(9)]}
CAT={"quote_usd_hour":0.6,"stock":"MEDIUM","rate_within_cap":True}
class FirstFiveSecondTest(unittest.TestCase):
    def test_exact_usd_cap(self):
        self.assertTrue(price_within_usd_one(0.6,60))
        self.assertFalse(price_within_usd_one(1.01,60))
        self.assertFalse(price_within_usd_one("unknown",60))
        self.assertFalse(price_within_usd_one(-1,60))
    def test_catalog_gpu_region_stock(self):
        g={"gpus":[{"id":"NVIDIA GeForce RTX 4090","price":{"secure":0.6}}]}
        c={"dataCenters":[{"id":"EU-RO-1","gpuAvailability":[
            {"id":"NVIDIA GeForce RTX 4090","availability":"MEDIUM"}]}]}
        self.assertTrue(check_catalog(g,c)["rate_within_cap"])
    def test_no_write_key_means_not_ready(self):
        r=evaluate(P,M,VOL,{"pods":[]},CAT,False,False)
        self.assertIn("RUNPOD_POD_WRITE_KEY_NOT_IN_GITHUB_SECRETS",r["blockers"])
        self.assertFalse(r["gpu_pod_created"])
    def test_stale_pod_detected(self):
        pods={"pods":[{"name":"trustfolio-video-washing-20261021-001","status":"RUNNING"}]}
        r=evaluate(P,M,VOL,pods,CAT,True,True)
        self.assertIn("POSSIBLE_EXISTING_VIDEO_POD",r["blockers"])
    def test_wrong_volume_and_art_blocks(self):
        r=evaluate(P,M,dict(VOL,size=99),{"pods":[]},CAT,False,True)
        self.assertIn("EXISTING_VOLUME_NOT_VERIFIED",r["blockers"])
        self.assertIn("ORIGINAL_MASTER_ART_NOT_ON_S3",r["blockers"])
    def test_preflight_always_no_bill(self):
        r=evaluate(P,M,VOL,{"pods":[]},CAT,True,True)
        self.assertFalse(r["mp4_rendered"])
        self.assertFalse(r["gpu_pod_created"])
        self.assertIn("PINNED_WAN_GPU_WORKER_NOT_DEPLOYED",r["blockers"])
if __name__=="__main__":unittest.main()
