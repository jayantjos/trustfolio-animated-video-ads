import unittest
from datetime import datetime,timedelta,timezone
from scripts.wan5_independent_reaper import NAME,VOLUME,DATACENTER,ReaperBlock,valid_target,scan

NOW=datetime(2026,10,21,13,30,tzinfo=timezone.utc)
def target(age=40):
    return {"id":"abc123456","name":NAME,"dataCenterId":DATACENTER,
            "mounts":{"network":[{"volumeId":VOLUME,"path":"/workspace"}]},
            "createdAt":(NOW-timedelta(minutes=age)).isoformat(),"status":"RUNNING"}
class TestIndependentReaper(unittest.TestCase):
    def test_wrong_pod_untouched(self):
        p=target();p["name"]="different-pod"
        self.assertFalse(valid_target(p,NOW))
    def test_wrong_volume_blocks(self):
        p=target();p["mounts"]["network"][0]["volumeId"]="bad"
        with self.assertRaisesRegex(ReaperBlock,"VOLUME_MISMATCH"):
            valid_target(p,NOW)
    def test_fresh_never_deleted(self):
        p=target(5)
        self.assertFalse(valid_target(p,NOW))
    def test_stale_allowed_for_exact_name_and_mount(self):
        self.assertTrue(valid_target(target(45),NOW))
    def test_no_pod_no_delete(self):
        req=[]
        def f(*args):req.append(args);return {"pods":[]}
        self.assertEqual(scan("key",f,now=NOW,apply=True)["status"],"NO_TARGET_POD")
        self.assertEqual([("key","","GET")],req)
    def test_stale_dry_run_read_only(self):
        p=target()
        calls=[]
        def f(*args):calls.append(args);return {"pods":[p]}
        r=scan("key",f,now=NOW,apply=False)
        self.assertEqual(r["status"],"WOULD_DELETE_STALE_OWNED_POD")
        self.assertEqual(1,len(calls))
    def test_stale_ownership_checked_twice_then_deleted(self):
        p=target()
        calls=[]
        def f(key,path,method):
            calls.append((path,method))
            if not path:return {"pods":[p]}
            if method=="DELETE":return {"http_status":204}
            if len(calls)>=4:return {"deleted":True}
            return p
        r=scan("key",f,lambda _:None,now=NOW,apply=True)
        self.assertEqual(r["status"],"STALE_GPU_POD_DELETED_AND_404_CONFIRMED")
        self.assertEqual([("","GET"),("/abc123456","GET"),
                          ("/abc123456","DELETE"),("/abc123456","GET")],calls)
    def test_mismatch_recheck_refuses_deletion(self):
        p=target()
        altered=target()
        altered["mounts"]["network"][0]["volumeId"]="other"
        ops=[]
        def f(key,path,method):
            ops.append(method)
            return {"pods":[p]} if not path else altered
        with self.assertRaises(ReaperBlock):scan("k",f,now=NOW,apply=True)
        self.assertNotIn("DELETE",ops)
if __name__=="__main__":unittest.main()
