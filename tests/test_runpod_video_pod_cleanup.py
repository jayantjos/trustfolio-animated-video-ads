import os,unittest
from unittest.mock import patch
from scripts.runpod_video_pod_cleanup import cleanup,validate_owned_pod,UnsafeCleanup

POD="abc123xyz"
JOB="washing-20261021-001"
class DeletionTests(unittest.TestCase):
    def obj(self,name=None,volume="1bch597yrz"):
        return {"id":POD,"name":name or "trustfolio-video-"+JOB,
                "mounts":{"network":[{"volumeId":volume,"path":"/workspace"}]}}
    def test_dryrun_never_contacts_runpod(self):
        def noapi(*a):raise AssertionError("unexpected network call")
        o=cleanup(POD,JOB,"",requester=noapi)
        self.assertEqual(o["status"],"DRY_RUN_NO_POD_TOUCHED")
    def test_only_exact_name_volume_and_id(self):
        self.assertTrue(validate_owned_pod(self.obj(),POD,JOB))
        for obj in (self.obj("some-other-user-pod"),self.obj(volume="not-our-volume")):
            with self.assertRaises(UnsafeCleanup):validate_owned_pod(obj,POD,JOB)
        with self.assertRaises(UnsafeCleanup):validate_owned_pod(self.obj(),"wrongID",JOB)
    def test_requires_private_enable_flag(self):
        with patch.dict(os.environ,{"TRUSTFOLIO_POD_DELETE_ARMED":"no"}):
            with self.assertRaises(UnsafeCleanup):cleanup(POD,JOB,"fake",apply=True,artifact_verified=True)
    def test_success_verified_delete(self):
        calls=[]
        def api(key,pod_id,method):
            calls.append(method)
            if method=="GET" and "DELETE" in calls:return {"deleted":True,"http_status":404}
            if method=="GET":return self.obj()
            return {"http_status":204}
        with patch.dict(os.environ,{"TRUSTFOLIO_POD_DELETE_ARMED":"yes"}):
            out=cleanup(POD,JOB,"write-key",apply=True,artifact_verified=True,requester=api,sleep=lambda t:None)
        self.assertEqual(calls,["GET","DELETE","GET"])
        self.assertTrue(out["network_volume_preserved"])
    def test_failed_render_uses_emergency_cleanup(self):
        calls=[]
        def api(key,pod_id,method):
            calls.append(method)
            if method=="GET" and "DELETE" in calls:return {"deleted":True,"http_status":404}
            if method=="GET":return self.obj()
            return {}
        with patch.dict(os.environ,{"TRUSTFOLIO_POD_DELETE_ARMED":"yes"}):
            result=cleanup(POD,JOB,"key",apply=True,forced_after_failure=True,requester=api,sleep=lambda t:None)
        self.assertIn("TERMINATED",result["status"])
    def test_no_verified_mp4_prevents_normal_cleanup(self):
        with patch.dict(os.environ,{"TRUSTFOLIO_POD_DELETE_ARMED":"yes"}):
            with self.assertRaisesRegex(UnsafeCleanup,"MP4_MUST"):
                cleanup(POD,JOB,"fake",apply=True,requester=lambda *a:None)
    def test_delete_never_called_on_foreign_pod(self):
        methods=[]
        def api(key,pod_id,method):
            methods.append(method)
            return self.obj(name="someone-elses-pod")
        with patch.dict(os.environ,{"TRUSTFOLIO_POD_DELETE_ARMED":"yes"}):
            with self.assertRaisesRegex(UnsafeCleanup,"NOT_OWNED"):
                cleanup(POD,JOB,"key",apply=True,forced_after_failure=True,requester=api)
        self.assertEqual(methods,["GET"])
if __name__=="__main__":unittest.main()
