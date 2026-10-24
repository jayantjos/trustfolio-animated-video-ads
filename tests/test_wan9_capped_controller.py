"""CPU-only fail-closed WAN9 observation: real S3 progress versus missing SSE.

No provider calls and absolutely no GPU authorization here.
"""
import json
import unittest
from unittest.mock import patch
from scripts import wan9_capped_controller as w

SHA="1"*64
ATTEMPT="wan9-one-shot-20261024"

class TestWan9SafeProgress(unittest.TestCase):
    def checkpoint(self,scene="scene01",at=1000.0,attempt=ATTEMPT,digest=SHA):
        return {"scene_id":scene,"stage":"WAN_INFERENCE",
                "time":at,"attempt_id":attempt,"job_hash":digest}

    def fake_load(self,at=1000.0,attempt=ATTEMPT,digest=SHA):
        entry=self.checkpoint(at=at,attempt=attempt,digest=digest)
        def f(_s3,key,_cap):
            if key.endswith("scene01.progress.json"):
                return json.dumps(entry).encode(),{}
            raise ValueError("Not found")
        return f

    def test_new_worker_stage_without_logs_counts_once_only(self):
        with patch.object(w,"load",side_effect=self.fake_load()):
            first=w.verified_worker_progress(None,job_hash=SHA,
                    attempt_id=ATTEMPT,now=1001)
            again=w.verified_worker_progress(None,job_hash=SHA,
                    attempt_id=ATTEMPT,now=1010)
        self.assertEqual(first,(1000.0,"scene01"))
        self.assertEqual(first,again)
        # Caller must compare the immutable marker and refuse to reset
        # its clock on a replay of exactly the same payload.
        last_marker=first
        self.assertFalse(again!=last_marker)

    def test_reject_stale_future_and_wrong_attempt(self):
        for data_now,attempt,digest in (
                (1200,ATTEMPT,SHA),(998,ATTEMPT,SHA),
                (1001,"wrong-attempt",SHA),(1001,ATTEMPT,"2"*64)):
            with self.subTest(data_now=data_now,attempt=attempt,digest=digest):
                with patch.object(w,"load",side_effect=self.fake_load(
                    attempt=attempt,digest=digest)):
                    self.assertIsNone(w.verified_worker_progress(None,
                        job_hash=SHA,attempt_id=ATTEMPT,now=data_now))

    def test_inference_stage_allows_six_minute_render_but_not_infinite(self):
        # Prior failure killed scene01 ~one minute after WAN_INFERENCE began,
        # because unavailable SSE was treated as no progress.
        w.enforce_observation_timeout(now=10400,started=9000,
            last_seen=10000,logs_ever=False,last_kind="worker_stage")
        with self.assertRaises(w.Wan9Blocked):
            w.enforce_observation_timeout(now=10441,started=9000,
                last_seen=10000,logs_ever=False,last_kind="worker_stage")

    def test_no_worker_stage_queued_pod_fails_550_seconds(self):
        w.enforce_observation_timeout(now=1549,started=1000,last_seen=1000,
                                      logs_ever=False,last_kind="startup")
        with self.assertRaises(w.Wan9Blocked):
            w.enforce_observation_timeout(now=1551,started=1000,
                last_seen=1000,logs_ever=False,last_kind="startup")

    def test_live_logs_do_not_silence_staleness(self):
        with self.assertRaises(w.Wan9Blocked):
            w.enforce_observation_timeout(now=1110,started=1000,
                last_seen=1000,logs_ever=True,last_kind="live_log")

    def test_wallcap_always_wins_even_with_new_progress(self):
        with self.assertRaises(w.Wan9Blocked):
            w.enforce_observation_timeout(now=1000+w.MONITOR_SECS+31,
                started=1000,last_seen=1000+w.MONITOR_SECS+30,
                logs_ever=False,last_kind="worker_stage")

if __name__=="__main__":
    unittest.main()
