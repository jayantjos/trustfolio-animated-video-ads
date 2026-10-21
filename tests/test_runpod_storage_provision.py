import json
import tempfile
import unittest
from pathlib import Path
from scripts.runpod_storage_provision import (
   build_dry_plan,check_policy,create,preflight,Blocked,REGION,NAME,SIZE,TYPE,CONFIRM)

class RunPodProvisionSafetyTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.file=Path(td.name)/"purchase.json"
        self.policy={"approval":"MONTHLY_STORAGE_COST_ONLY","name":NAME,
                     "data_center":REGION,"network_volume_type":TYPE,
                     "volume_size_gb":SIZE,"standard_public_price_usd_gb_month":0.07,
                     "max_estimated_usd_month":7,
                     "gpu_instance_creation_enabled":False,
                     "video_publishing_enabled":False}
        self.save()
    def save(self):
        self.file.write_text(json.dumps(self.policy))
    def test_dry_run_does_not_create(self):
        r=build_dry_plan(self.file)
        self.assertFalse(r["volume_created"])
        self.assertEqual(r["size_gb"],100)
        self.assertEqual(r["datacenter"],"EU-RO-1")
    def test_reject_wrong_size_region_tier_and_budget(self):
        for name,value in (("volume_size_gb",200),("data_center","US-MO-1"),
                           ("network_volume_type","HIGH_PERFORMANCE"),
                           ("max_estimated_usd_month",6)):
            original=self.policy[name]
            self.policy[name]=value;self.save()
            with self.assertRaises(Blocked):check_policy(self.file)
            self.policy[name]=original;self.save()
    def test_no_confirm_no_api_calls(self):
        def forbidden(*a,**kw):raise AssertionError("API not allowed")
        with self.assertRaisesRegex(Blocked,"EXACT_CONFIRMATION"):
            create("key",self.file,"not-approved",writer=forbidden,reader=forbidden)
    def test_no_key_no_api_calls(self):
        with self.assertRaisesRegex(Blocked,"WRITE_KEY_MISSING"):
            create("",self.file,CONFIRM)
    def test_stock_check_blocks_create(self):
        def reader(key,endpoint,query=None):
            if endpoint=="/network-volumes":
                return {"networkVolumes":[],"pagination":{"hasNextPage":False}}
            return {"dataCenters":[{"id":"EU-RO-1",
                      "networkVolumeTypes":["STANDARD"],
                      "gpuAvailability":[{"id":"NVIDIA GeForce RTX 4090","availability":"LOW"}]}]}
        with self.assertRaisesRegex(Blocked,"STOCK"):
            preflight("key",reader=reader)
    def test_no_double_creation(self):
        def reader(key,endpoint,query=None):
            if endpoint=="/network-volumes":
                return {"networkVolumes":[{"name":NAME,"dataCenter":REGION,
                                            "size":SIZE,"type":TYPE,"id":"ID"}]}
            raise AssertionError("not required")
        called=[]
        def writer(*a,**kw):called.append(1);raise AssertionError("no POST")
        result=create("test",self.file,CONFIRM,writer=writer,reader=reader)
        self.assertEqual(result["status"],"ALREADY_EXISTS")
        self.assertFalse(called)

if __name__=="__main__":
    unittest.main()
