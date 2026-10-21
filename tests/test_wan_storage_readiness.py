import json,unittest
from pathlib import Path
from scripts.wan_storage_readiness import check_structure,check_remote

class WanStorageReadiness(unittest.TestCase):
    def setUp(self):
        self.m=json.loads(Path("config/wan_verified_model_manifest.json").read_text())
    def test_total_and_immutability(self):
        s=check_structure(self.m)
        self.assertEqual(self.m["expected_total_bytes"],34180083066)
    def test_all_9_objects_checked(self):
        class Client:
            def __init__(self,size):self.size=size;self.seen=[]
            def head_object(self,Bucket,Key):
                self.seen.append((Bucket,Key))
                filename=Key.rsplit("/",1)[-1]
                return {"ContentLength":self.size[filename]}
        client=Client({x["name"]:x["bytes"] for x in self.m["objects"]})
        r=check_remote(self.m,client)
        self.assertEqual(len(client.seen),9)
        self.assertEqual(r["status"],"ALL_9_FILES_PRESENT_WITH_EXPECTED_SIZES")
        self.assertEqual(r["model_usable_by_inference"],"NOT_YET_TESTED")
    def test_missing_or_wrong_shard_fails(self):
        class C:
            def head_object(self,**kwargs):return {"ContentLength":1}
        with self.assertRaises(ValueError):check_remote(self.m,C())

if __name__=="__main__":unittest.main()
