import copy,unittest
from decimal import Decimal
from scripts.runpod_video_lifecycle import make_pod_request,run_job,dry_run,GPUBlocked

BASE={
 "network_volume_id":"1bch597yrz","region":"EU-RO-1",
 "max_concurrent_pods":1,"max_gpu_lifetime_minutes":60,
 "publishing_enabled":False,"keep_s3_volume_after_delete":True,
 "must_provider_auto_terminate":True,"must_independent_reaper":True,
 "must_always_terminate_in_finally":True,"must_confirm_pod_deleted_after_render":True,
 "paid_gpu_instance_provisioning_enabled":True,"gpu_hourly_price_verified":True,
 "pod_api_write_key_connected":True,"separate_cron_vps_deploy_completed":True,
 "provider_auto_terminate_verified":True,"independent_reaper_live_verified":True,
 "worker_container_real_inference_verified":True,
 "gpu_spending_approved_usd":2.5,"max_gpu_cost_usd":1.5,
 "worker_image":"registry.example.com/trustfolio/wan-worker@sha256:"+"a"*64
}
JOB={"job_id":"washing-20261021-001","paid_gpu_authorized":True,
"gpu_started":False,"social_publishing_enabled":False,
"render_eligibility":"ALL_ASSETS_VERIFIED_FOR_PRIVATE_RENDER",
"idempotency_sha256":"b"*64}
class API:
 def __init__(self):self.calls=[]
 def create(self,p):
    self.calls.append("create")
    return {"id":"abc123xyz","name":p["name"],"dataCenterId":"EU-RO-1",
            "mounts":p["mounts"],"gpu":p["gpu"]}
 def wait_until_running(self,*a,**kw):self.calls.append("wait")
 def terminate_and_confirm_absent(self,*a,**kw):
    self.calls.append(("terminate",kw.get("emergency")))
class Worker:
 def __init__(self,fail=False):self.fail=fail
 def render(self,pid,job):
    if self.fail:raise RuntimeError("GPU inference failed")
    return {"status":"S3_MP4_COMPLETE","job_id":job["job_id"],
            "s3_key":"videos/private-qa/"+job["job_id"]+"/final.mp4",
            "sha256":"c"*64,"bytes":22000}
class S3:
 def check_sha256(self,*args):return True
class LifecycleTests(unittest.TestCase):
 def test_default_no_spend_no_calls(self):
    p=dict(BASE,paid_gpu_instance_provisioning_enabled=False,gpu_spending_approved_usd=0)
    self.assertEqual(dry_run(p)["status"],"DRY_RUN_NO_GPU_CREATED")
 def test_exact_volume_and_gpu_request(self):
    req=make_pod_request(JOB,BASE,quoted_usd_per_hour=1.0)
    self.assertEqual(req["mounts"]["network"],[{"volumeId":"1bch597yrz","path":"/workspace"}])
    self.assertEqual(req["dataCenterIds"],["EU-RO-1"])
    self.assertEqual(req["gpu"]["count"],1)
 def test_success_s3_first_then_pod_deleted(self):
    a=API(); r=run_job(JOB,BASE,a,Worker(),S3(),quote=1.0)
    self.assertEqual(r["status"],"VIDEO_MP4_VERIFIED_PENDING_LIPSYNC_HUMAN_QA")
    self.assertEqual(a.calls,["create","wait",("terminate",False)])
 def test_failure_always_terminates(self):
    a=API()
    with self.assertRaisesRegex(RuntimeError,"GPU inference"):
       run_job(JOB,BASE,a,Worker(fail=True),S3(),quote=1.0)
    self.assertEqual(a.calls[-1],("terminate",True))
 def test_budget_blocks_create(self):
    p=dict(BASE,max_gpu_cost_usd=0.5)
    with self.assertRaisesRegex(GPUBlocked,"QUOTE"):
       make_pod_request(JOB,p,quoted_usd_per_hour=0.9)
 def test_unverified_immutable_worker_blocks(self):
    p=dict(BASE,worker_image="runpod/pytorch:latest")
    with self.assertRaisesRegex(GPUBlocked,"PINNED"):
       make_pod_request(JOB,p,quoted_usd_per_hour=1.0)
 def test_unverified_provider_ttl_blocks(self):
    p=dict(BASE,provider_auto_terminate_verified=False)
    with self.assertRaisesRegex(GPUBlocked,"NOT_READY"):
       make_pod_request(JOB,p,quoted_usd_per_hour=1.0)
 def test_stale_asset_job_blocks(self):
    j=dict(JOB,render_eligibility="VALIDATED_LIVE_DATA_ART_QA_PENDING")
    with self.assertRaisesRegex(GPUBlocked,"RENDER_ASSETS_NOT_READY"):
       make_pod_request(j,BASE,quoted_usd_per_hour=1.0)
if __name__=="__main__":unittest.main()
