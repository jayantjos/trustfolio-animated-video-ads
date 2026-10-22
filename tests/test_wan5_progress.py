import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import wan5_first_paid_controller as c
from scripts import wan5_gpu_worker as w
from scripts import wan5_live_log_guard as g

class ProgressTests(unittest.TestCase):
    def monitor(self, heartbeat, logs=None):
        ticks=[0]
        pod={"id":"pod123456", "name":c.NAME,"dataCenterId":c.DATACENTER,
             "mounts":{"network":[{"volumeId":c.VOLUME,"path":"/workspace"}]},"status":"RUNNING"}
        def obj(s3,key,cap):
            return json.dumps(heartbeat(ticks[0])).encode() if key==c.PROGRESS else None
        def sleep(_): ticks[0]+=30
        with patch.object(c,"get_object",side_effect=obj),patch.object(c,"find_owned_pods",return_value=[pod]):
            c.polling_for_mp4(None,"key","pod123456",attempt="attempt123",now=lambda:ticks[0],
                wall_now=lambda:1000+ticks[0],deadline_seconds=720,sleep=sleep,
                log_scanner=lambda *a:logs or {"available":False})

    def test_fresh_progress_survives_log_outage_but_total_deadline_holds(self):
        with self.assertRaisesRegex(c.PilotError,"GPU_RENDER_TIMEOUT_WITHIN_BUDGET"):
            self.monitor(lambda t:{"job_id":c.JOB_ID,"attempt_id":"attempt123",
                "sequence":t+1,"updated_at":1000+t})

    def test_stale_or_wrong_attempt_heartbeat_cannot_extend_billing(self):
        for attempt in ("attempt123","old_attempt"):
            with self.subTest(attempt=attempt),self.assertRaisesRegex(c.PilotError,"VISIBILITY_TIMEOUT"):
                self.monitor(lambda t:{"job_id":c.JOB_ID,"attempt_id":attempt,
                    "sequence":1,"updated_at":1000})

    def test_replayed_log_tail_cannot_extend_billing(self):
        with self.assertRaisesRegex(c.PilotError,"VISIBILITY_TIMEOUT"):
            self.monitor(lambda t:{}, {"available":True,"fingerprint":"same-tail"})

    def test_progress_is_atomic_and_attempt_bound(self):
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"TRUSTFOLIO_ATTEMPT_ID":"attempt123"}):
            with w.Progress(Path(td)) as progress:
                progress.checkpoint("INFERENCE")
            data=json.loads((Path(td)/"scene01.progress.json").read_text())
            self.assertEqual(data["attempt_id"],"attempt123")
            self.assertEqual(data["stage"],"INFERENCE")
            self.assertGreater(data["sequence"],1)
            self.assertFalse((Path(td)/"scene01.progress.json.tmp").exists())

    def test_no_audio_without_exact_text_and_listening_qa(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"audio.json";p.write_text(json.dumps({"text":"wrong","listening_qa_passed":True}))
            with patch.object(w,"AUDIO_MANIFEST",p),self.assertRaisesRegex(w.RenderError,"LISTENING_QA"):
                w.verified_audio()

    def test_heartbeat_sse_has_no_usable_log_content(self):
        for value in (b'data: {}\n',b'data: null\n',b'data: {"type":"heartbeat"}\n'):
            with self.subTest(value=value):
                result=g.scan_container_logs("key","pod123456",opener=lambda *a,**k:io.BytesIO(value))
                self.assertFalse(result["available"])

class CleanupTests(unittest.TestCase):
    def test_preexisting_pod_is_not_deleted_by_unstarted_attempt(self):
        env={"RUNPOD_API_KEY":"read", "RUNPOD_POD_WRITE_KEY":"write",
             "TRUSTFOLIO_PAID_FIRST_TEST":"yes", "TRUSTFOLIO_ATTEMPT_ID":"new-attempt",
             "TRUSTFOLIO_NEXT_ATTEMPT_APPROVED":"new-attempt",
             "TRUSTFOLIO_TESTED_WORKER_IMAGE":"ghcr.io/jayantjos/trustfolio-wan5-worker@sha256:"+("a"*64)}
        with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",env),\
             patch.object(c,"make_s3"),patch.object(c,"verify_hero"),\
             patch.object(c,"check_fresh_output"),patch.object(c,"verify_hindi_inputs"),\
             patch.object(c,"check_cost_and_availability",return_value={"gpu_type":"test","stock":"MEDIUM","rate_usd_per_hour":"0.89","max_gpu_usd_at_38m":"0.5637"}),\
             patch.object(c,"find_owned_pods",return_value=[{"id":"existing"}]),\
             patch.object(c,"kill_owned_pods") as kill:
            import os
            previous=os.getcwd()
            try:
                os.chdir(td)
                with self.assertRaisesRegex(c.PilotError,"ALREADY_EXISTING"):
                    c.run()
            finally:os.chdir(previous)
            kill.assert_not_called()

class AudioPreflightTests(unittest.TestCase):
    def test_missing_audio_approval_blocks_before_gpu(self):
        with patch.object(c,'get_object',return_value=None),self.assertRaisesRegex(c.PilotError,'MANIFEST_MISSING'):
            c.verify_hindi_inputs(None)

    def test_audio_hash_mismatch_blocks_before_gpu(self):
        meta={'text':w.DIALOGUE,'listening_qa_passed':True,
              's3_key':'assets/audio/washing-machines/hindi_neural_v1/clip.mp3','sha256':'0'*64}
        with patch.object(c,'get_object',side_effect=[json.dumps(meta).encode(),b'changed audio']),self.assertRaisesRegex(c.PilotError,'READBACK_MISMATCH'):
            c.verify_hindi_inputs(None)
