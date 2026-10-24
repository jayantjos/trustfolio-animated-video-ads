"""USD1 ceiling: test executable provider-bound cost limits with no Pods."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import unittest

from trustfolio_video.wan9_dollar1_budget import (
    BudgetBlocked, quote_guard, deployment_guard, require_clean_gpu_inputs,
    MAX_SCENE_SECONDS, MAX_RATE_USD_PER_HOUR,POD_PROVIDER_TTL_MINUTES,
    WORKER_WALL_SECONDS,GPU_LIMIT_USD
)
class TestUnderDollarWan9(unittest.TestCase):
    def test_realistic_quote_has_safety_margin_and_worker_ends_earlier(self):
        obj=quote_guard("0.89")
        self.assertLess(Decimal(obj["predicted_upper_gpu_cost_usd"]),Decimal(".50"))
        self.assertEqual("1.00",obj["max_gpu_budget_usd"])
        self.assertFalse(obj["paid_gpu_would_start"])
        self.assertLess(WORKER_WALL_SECONDS,POD_PROVIDER_TTL_MINUTES*60)
        self.assertLess(MAX_SCENE_SECONDS,WORKER_WALL_SECONDS)
        self.assertEqual(1,1)
        self.assertLess(Decimal("1.50")*Decimal(30)/Decimal(60)+Decimal(".10"),GPU_LIMIT_USD)

    def test_rate_guard_refuses_overspend_and_invalid_quotes(self):
        for value in (0,-1,"nan","Inf","garbage",None,2.0,1.9):
            with self.subTest(value=value),self.assertRaises(BudgetBlocked):
                quote_guard(value)
        with self.assertRaises(BudgetBlocked):
            quote_guard("1.49",ttl_minutes=31)
        with self.assertRaises(BudgetBlocked):
            quote_guard("0.89",remaining_budget=".10")
        with self.assertRaises(BudgetBlocked):
            quote_guard("0.89",remaining_budget="3")

    def test_provider_ttl_and_exact_target_required(self):
        now=datetime.now(timezone.utc)
        x={"gpuTypeId":"NVIDIA GeForce RTX 4090","gpuCount":1,
            "dataCenterId":"EU-RO-1","networkVolumeId":"1bch597yrz",
            "volumeMountPath":"/workspace","cloudType":"SECURE",
            "startJupyter":False,"startSsh":False,
            "terminateAfter":(now+timedelta(minutes=29)).isoformat().replace("+00:00","Z")}
        self.assertEqual("1.00",deployment_guard(x,quoted_rate=".89")["max_gpu_budget_usd"])
        for key,val in (("gpuCount",2),("gpuTypeId","NVIDIA B200"),
            ("dataCenterId","US-CA-2"),("networkVolumeId","other"),
            ("startSsh",True),("terminateAfter",(now+timedelta(minutes=40)).isoformat())):
            with self.subTest(key=key),self.assertRaises(BudgetBlocked):
                deployment_guard({**x,key:val},quoted_rate=".89")

    def test_never_gpu_launch_on_unapproved_branded_reference_candidates(self):
        all_ok=dict(all_nine_plates_clean=True,image_identity_qa=True,
                    independent_reaper_recent_success=True,source_digest_pinned=True)
        self.assertTrue(require_clean_gpu_inputs(**all_ok))
        for field in all_ok:
            with self.subTest(field=field),self.assertRaises(BudgetBlocked):
                require_clean_gpu_inputs(**{**all_ok,field:False})

if __name__=="__main__":unittest.main()
