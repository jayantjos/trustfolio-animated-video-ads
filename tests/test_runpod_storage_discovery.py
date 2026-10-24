import json, unittest
from scripts.runpod_storage_discovery import inventory, summarize, get_json, Blocked

class RunPodDiscoveryTests(unittest.TestCase):
    def test_readonly_calls(self):
        calls=[]
        def reader(k,endpoint,params=None):
            calls.append((endpoint,params))
            if endpoint=="/pods":return {"pods":[],"pagination":{"hasNextPage":False}}
            if endpoint=="/network-volumes":return {"networkVolumes":[],"pagination":{"hasNextPage":False}}
            return {"dataCenters":[]}
        result=inventory("test",reader)
        self.assertEqual([x[0] for x in calls],
                         ["/pods","/network-volumes","/catalog/datacenters"])
        self.assertEqual(calls[2][1],{"include":"GPU_AVAILABILITY"})
        self.assertEqual(result["storage_volume_count"],0)
        self.assertFalse(result["charged_resources_created"])
    def test_sanitization_and_compatibility(self):
        result=summarize([{"id":"PRIVATE_POD","status":"RUNNING","env":{"TOKEN":"VERY_SECRET"}}],
          [{"id":"PRIVATE_VOLUME","size":100}],
          [{"id":"AS-1","region":"ASIA","networkVolumeTypes":["STANDARD"],
            "gpuAvailability":[{"id":"NVIDIA GeForce RTX 4090","availability":"HIGH"}]},
           {"id":"XX","region":"EUROPE","networkVolumeTypes":["HIGH_PERFORMANCE"],
            "gpuAvailability":[{"id":"NVIDIA GeForce RTX 4090","availability":"HIGH"}]}])
        self.assertEqual(result["candidate_count"],1)
        self.assertEqual(result["existing_storage_gb"],100)
        self.assertEqual(result["running_pods"],1)
        self.assertNotIn("PRIVATE",json.dumps(result))
        self.assertNotIn("VERY_SECRET",json.dumps(result))
    def test_paginated_incomplete_fail_closed(self):
        def reader(k,path,params=None):return {"pods":[],"pagination":{"hasNextPage":True}}
        with self.assertRaises(Blocked):inventory("test",reader)
    def test_get_nonread_endpoint_refused_without_network(self):
        with self.assertRaises(Blocked):
            get_json("test","/pods/new",opener=lambda *a,**kw: self.fail("network"))
if __name__=="__main__":unittest.main()
