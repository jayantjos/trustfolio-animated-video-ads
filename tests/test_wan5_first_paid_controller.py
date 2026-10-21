import hashlib
import io
import json
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from scripts import wan5_first_paid_controller as c

class DummyBody(io.BytesIO): pass
class FakeS3:
    def __init__(self,data):self.data=data
    def get_object(self,*,Bucket,Key):
        assert Bucket==c.VOLUME
        if Key not in self.data:
            e=Exception("absent")
            e.response={"Error":{"Code":"NoSuchKey"}}
            raise e
        b=self.data[Key]
        return {"Body":DummyBody(b),"ContentLength":len(b)}

class Tests(unittest.TestCase):
    def test_paid_worker_image_matches_successful_build(self):
        from pathlib import Path
        expected="ghcr.io/jayantjos/trustfolio-wan5-worker@sha256:24432e652fcc50c5a00d85d42da45200a9c3bf2e793c7c2069a6686f6c629971"
        self.assertEqual(c.IMAGE,expected)
        workflow=Path(".github/workflows/wan5-first-paid-gpu-pilot.yml").read_text()
        self.assertIn(expected,workflow)
        self.assertNotIn("sha256:5f920321ce5cd6485e560a670b3b53f8f69cc07b2b71b10caa28723eea15cdf1",workflow)

    def test_no_blackwell_cuda_architecture_risk(self):
        # Worker base torch 2.6 / cu124 supports Ada 4090, not sm_120.
        self.assertEqual(c.GPU_PREFERENCE,("NVIDIA GeForce RTX 4090",))

    def test_fixed_scope_and_budget(self):
        self.assertEqual(c.POD_PROVIDER_TTL_MINUTES,38)
        self.assertLess(c.MAX_ACCEPTED_RATE_USD_PER_HR*c.POD_PROVIDER_TTL_MINUTES/60,1)
        self.assertEqual(c.VOLUME,"1bch597yrz")
    def test_graphql_provider_deadline(self):
        now=datetime(2026,10,21,14,0,tzinfo=timezone.utc)
        p=c.make_graphql_payload("registry_12345",now)
        self.assertEqual(p["terminateAfter"],"2026-10-21T14:38:00Z")
        self.assertEqual(p["networkVolumeId"],c.VOLUME)
        self.assertEqual(p["imageName"],c.IMAGE)
        self.assertEqual(p["gpuTypeId"],"NVIDIA GeForce RTX 4090")
    def test_no_pod_get_if_no_owned(self):
        f=lambda key,path,method="GET",data=None:{"pods":[]}
        self.assertEqual(c.kill_owned_pods("k",requester=f),"NO_OWNED_GPU_POD")
    def test_refuse_wrong_pod_mount(self):
        wrong={"name":c.NAME,"id":"pod0123456",
               "dataCenterId":c.DATACENTER,
               "mounts":{"network":[{"volumeId":"other","path":"/workspace"}]}}
        with self.assertRaisesRegex(c.PilotError,"MOUNT_WRONG"):
            c.validate_target(wrong)
    def test_deletes_only_exact_owned_pod_after_double_verify(self):
        target={"name":c.NAME,"id":"pod0123456",
                "dataCenterId":c.DATACENTER,
                "mounts":{"network":[{"volumeId":c.VOLUME,"path":"/workspace"}]}}
        calls=[]
        def f(key,path,method="GET",data=None):
            calls.append((path,method))
            if path=="/pods":return {"pods":[target,{"name":"other"}]}
            if method=="DELETE":return {}
            if len(calls)>=4:return {"deleted":True}
            return target
        self.assertEqual(c.kill_owned_pods("k",requester=f,sleep=lambda n:None),
                         "DELETE_GET_404_CONFIRMED")
        self.assertEqual(calls,[("/pods","GET"),("/pods/pod0123456","GET"),
                                ("/pods/pod0123456","DELETE"),
                                ("/pods/pod0123456","GET")])
    def test_cleanup_rejects_different_pod_id(self):
        pod={"name":c.NAME,"id":"wrongpod999",
             "dataCenterId":c.DATACENTER,
             "mounts":{"network":[{"volumeId":c.VOLUME,"path":"/workspace"}]}}
        calls=[]
        def requester(key,path,method="GET",data=None):
            calls.append((path,method))
            return {"pods":[pod]}
        with self.assertRaisesRegex(c.PilotError,"POD_ID_CHANGED"):
            c.kill_owned_pods("k",requester=requester,
                              expected_pod_id="originalpod123")
        self.assertEqual(calls,[("/pods","GET")])

    def test_live_log_fatal_aborts_before_waiting_or_spending_more(self):
        pod={"name":c.NAME,"id":"pod123456",
             "dataCenterId":c.DATACENTER,
             "mounts":{"network":[{"volumeId":c.VOLUME,"path":"/workspace"}]},
             "status":"RUNNING"}
        with patch.object(c,"get_object",return_value=None), \\
             patch.object(c,"find_owned_pods",return_value=[pod]):
            with self.assertRaisesRegex(c.PilotError,"GPU_FATAL_LOG_MISSING_DEPENDENCY"):
                c.polling_for_mp4(object(),"k","pod123456",
                    read_key="read",now=lambda:0,
                    sleep=lambda _:self.fail("must abort immediately"),
                    log_scanner=lambda key,pid:{"available":True,
                                               "events":1,"fatal":"MISSING_DEPENDENCY"})

    def test_log_visibility_timeout_aborts_if_unmonitored(self):
        pod={"name":c.NAME,"id":"pod123456",
             "dataCenterId":c.DATACENTER,
             "mounts":{"network":[{"volumeId":c.VOLUME,"path":"/workspace"}]},
             "status":"RUNNING"}
        ticks=iter([0, 0, 100, 181, 181, 181, 181, 181])
        with patch.object(c,"get_object",return_value=None), \\
             patch.object(c,"find_owned_pods",return_value=[pod]):
            with self.assertRaisesRegex(c.PilotError,"GPU_LOG_VISIBILITY_TIMEOUT_ABORT"):
                c.polling_for_mp4(object(),"k","pod123456",
                    read_key="read",now=lambda: next(ticks),
                    interval=0,sleep=lambda _:None,
                    log_scanner=lambda key,pid:{"available":False,
                                               "events":0,"fatal":None})

    def test_pod_identity_change_aborts_before_log_read(self):
        pod={"name":c.NAME,"id":"pod_other",
             "dataCenterId":c.DATACENTER,
             "mounts":{"network":[{"volumeId":c.VOLUME,"path":"/workspace"}]}}
        with patch.object(c,"get_object",return_value=None), \\
             patch.object(c,"find_owned_pods",return_value=[pod]):
            with self.assertRaisesRegex(c.PilotError,"GPU_POD_IDENTITY_CHANGED"):
                c.polling_for_mp4(object(),"k","pod123456",now=lambda:0,
                    log_scanner=lambda *a:self.fail("wrong pod must not be read"))

    def test_wrong_creds_no_api(self):
        with self.assertRaisesRegex(c.PilotError,"KEY_MISSING"):
            c.safe_api("","/pods")
    def test_refuse_rest_unsafe_create(self):
        with self.assertRaisesRegex(c.PilotError,"REFUSE_REST_POD_CREATE"):
            c.safe_api("k","/pods","POST",data={})
    def test_refuse_second_paid_video(self):
        s3=FakeS3({c.RECEIPT:b"{}"})
        with self.assertRaisesRegex(c.PilotError,"PREEXISTING_VIDEO_RECEIPT"):
            c.check_fresh_output(s3)
    def test_remote_mp4_hash_required(self):
        payload=b"FAKE_BYTES_ONLY_UNIT_TEST"*1000
        report={"status":"VOLUME_MP4_WRITTEN_PENDING_S3_GET_VERIFICATION",
                "job_id":c.JOB_ID,"s3_key":c.MP4,
                "character_sha256":c.IMAGE_SHA,"social_publishing":False,
                "gpu_pod_destroyed":False,"sha256":hashlib.sha256(payload).hexdigest(),
                "bytes":len(payload),"seconds":5.03}
        f=FakeS3({c.MP4:payload})
        result=c.verify_mp4_s3(f,report)
        self.assertEqual(result["status"],"FIRST_GENUINE_WAN5_MP4_VERIFIED_PRIVATE_QA")
        bad=dict(report,sha256="0"*64)
        with self.assertRaisesRegex(c.PilotError,"SHA256_MISMATCH"):
            c.verify_mp4_s3(f,bad)
    def test_pilot_requires_arming(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaisesRegex(c.PilotError,"RUNPOD_READ_OR_WRITE_KEY_MISSING"):
                c.run()

if __name__=="__main__":unittest.main()
