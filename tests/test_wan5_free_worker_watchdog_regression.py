"""No-cost, no-network regression QA for GPU worker and log watchdog."""
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import wan5_gpu_worker as worker
from scripts import wan5_live_log_guard as guard


class TestWorkerAndWatchdogFreeQA(unittest.TestCase):
    def test_render_refuses_unarmed_execution_before_gpu(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(worker.RenderError, "PRIVATE_QA_ENV_NOT_ARMED"):
                worker.render()

    def test_generate_command_is_five_second_portrait_and_pinned(self):
        command = worker.generate_command(Path("/tmp/test.mp4"))
        self.assertEqual(command[command.index("--task")+1], "ti2v-5B")
        self.assertEqual(command[command.index("--frame_num")+1], "121")
        self.assertEqual(command[command.index("--size")+1], "704*1280")
        self.assertEqual(command[command.index("--sample_steps")+1], "30")
        self.assertIn("--image", command)
        self.assertIn("--t5_cpu", command)

    def test_ffprobe_rejects_invalid_duration_or_landscape(self):
        with tempfile.TemporaryDirectory() as d:
            mp4 = Path(d) / "clip.mp4"
            mp4.write_bytes(b"x" * 11000)
            def runner(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
                    "streams":[{"codec_type":"video","width":704,"height":1280}],
                    "format":{"duration":"5.04"}}))
            self.assertEqual(worker.check_video(mp4, runner), 5.04)
            def too_short(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps({
                    "streams":[{"codec_type":"video","width":704,"height":1280}],
                    "format":{"duration":"2.0"}}))
            with self.assertRaisesRegex(worker.RenderError, "NOT_A_REAL_FIVE_SECOND_VIDEO"):
                worker.check_video(mp4, too_short)

    def test_worker_failure_receipt_is_safe_and_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(worker, "OUTDIR", Path(d)), patch.object(worker, "FAILURE", Path(d)/"scene01.failure.json"):
                worker.write_failure_receipt("missing_dependency")
                report = json.loads((Path(d)/"scene01.failure.json").read_text())
                self.assertEqual(report["status"], "FAILED_PRIVATE_WAN5")
                self.assertEqual(report["failure_reason"], "MISSING_DEPENDENCY")
                self.assertFalse(report["social_publishing"])

    def test_empty_sse_is_not_heartbeat(self):
        class Stream(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        observation = guard.scan_container_logs("dummy", "pod123456",
            opener=lambda *args, **kwargs: Stream(b"data: \\n"), now=lambda: 0)
        # This test deliberately detects a current bug: an empty SSE data event
        # must not count as useful visibility.
        self.assertFalse(observation["available"])

if __name__ == "__main__":
    unittest.main()
