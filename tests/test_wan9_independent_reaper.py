"""No unrelated RunPod Pod or protected Network Volume may be modified."""
import unittest
from datetime import datetime,timedelta,timezone
from scripts import wan9_independent_reaper as mod

NOW=datetime(2026,10,24,7,0,tzinfo=timezone.utc)

def model(age):
    return {"id":"podtest12345","name":mod.NAME,"dataCenterId":mod.REGION,
            "createdAt":(NOW-timedelta(minutes=age)).isoformat(),
            "mounts":{"network":[{"volumeId":mod.VOLUME,"path":"/workspace"}]}}

class TestReaper(unittest.TestCase):
    def test_only_exact_pod_and_stale_27min_stop(self):
        d=[]
        def request(k,path,method):
            d.append((path,method))
            if not path:return {"pods":[model(28),{"id":"other123","name":"different-project"}]}
            if path=="/podtest12345" and method=="GET":return model(28) if d.count(("/podtest12345","GET"))<2 else {"deleted":True}
            if path=="/podtest12345" and method=="DELETE":return {"deleted":True}
            raise AssertionError("unrelated request")
        out=mod.reap("unit",client=request,now=NOW,apply=True,log_scanner=lambda k,i:{"fatal":False},sleep=lambda sec:None)
        self.assertTrue(out["deleted"])
        self.assertEqual([("/podtest12345","DELETE")],[x for x in d if x[1]=="DELETE"])
        self.assertFalse(any("network-volume" in x[0] for x in d))
    def test_no_action_on_live_or_foreign_pod(self):
        calls=[]
        def request(k,path,method):
            calls.append((path,method))
            return {"pods":[model(8)]}
        out=mod.reap("unit",client=request,now=NOW,apply=True,log_scanner=lambda k,i:{"fatal":False})
        self.assertFalse(out["deleted"])
        self.assertEqual([("","GET")],calls)
        unknown=model(44);unknown["mounts"]={"network":[{"volumeId":"NOT_OWNER","path":"/workspace"}]}
        with self.assertRaises(mod.ReaperBlock):
            mod.reap("unit",client=lambda k,p,m:{"pods":[unknown]},now=NOW,apply=True)
    def test_multiple_pods_fail_closed(self):
        with self.assertRaises(mod.ReaperBlock):
            mod.reap("unit",client=lambda k,p,m:{"pods":[model(29),model(30)]},now=NOW,apply=True)

if __name__=="__main__":unittest.main()
