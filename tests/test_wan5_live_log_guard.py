import io
import json
import unittest
from unittest.mock import patch

from scripts import wan5_live_log_guard as lg


class Stream(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class TestLiveLogGuard(unittest.TestCase):
    def test_known_fatal_log_signatures(self):
        cases = {
            "ModuleNotFoundError: No module named 'librosa'": "MISSING_DEPENDENCY",
            "ImportError: cannot import name 'foo'": "MISSING_DEPENDENCY",
            "torch.OutOfMemoryError: CUDA out of memory": "GPU_OOM",
            "RuntimeError: GPU architecture unsupported": "FATAL_RUNTIME",
            "TRUSTFOLIO_WAN5=BLOCKED_GPU_INFERENCE_OR_TOOLS_FAILED": "WORKER_BLOCKED",
            "FileNotFoundError: missing model": "FATAL_RUNTIME",
        }
        for line, expected in cases.items():
            self.assertEqual(lg.fatal_classification(line), expected)

    def test_progress_and_warnings_are_not_false_fatal(self):
        for line in ["WAN5_RENDER_PROGRESS=42", "CUDA detected",
                     "UserWarning: flash attention unavailable",
                     "TRUSTFOLIO_WAN5=VOLUME_MP4_PENDING_S3_VERIFY"]:
            self.assertIsNone(lg.fatal_classification(line))

    def test_detects_real_sse_failure_and_does_not_return_raw_secrets(self):
        lines = [
            "data: " + json.dumps({"line": "Starting Wan model"}) + "\n",
            "data: " + json.dumps({"line": "ModuleNotFoundError: No module named 'librosa'"}) + "\n",
        ]
        observations = []
        def opener(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertIn("/pods/pod123456/logs?", request.full_url)
            self.assertEqual(timeout, 5)
            observations.append(request.full_url)
            return Stream("".join(lines).encode())
        data = lg.scan_container_logs("sensitive-key", "pod123456",
                                      opener=opener, now=lambda: 0)
        self.assertEqual(data, {"available": True, "events": 2,
                                "fatal": "MISSING_DEPENDENCY"})
        self.assertNotIn("sensitive-key", str(data))
        self.assertEqual(len(observations), 1)

    def test_empty_events_are_not_treated_as_healthy(self):
        data = lg.scan_container_logs("k", "pod123456",
                         opener=lambda *a, **k: Stream(b""), now=lambda: 0)
        self.assertFalse(data["available"])

    def test_rejects_bad_pod_id_before_network_call(self):
        with self.assertRaisesRegex(ValueError, "BAD_POD_ID"):
            lg.scan_container_logs("key", "../other-pod")

    def test_json_nested_or_raw_sse(self):
        self.assertEqual(lg._event_line("data: " + json.dumps(
            {"data": {"line": "RuntimeError: GPU launch failed"}})),
            "RuntimeError: GPU launch failed")
        self.assertEqual(lg.fatal_classification("RuntimeError: GPU launch failed"),
                         "FATAL_RUNTIME")

    def test_network_outage_is_unavailable_not_success(self):
        def opener(*args, **kwargs):
            raise OSError("connection unavailable")
        data = lg.scan_container_logs("k","pod123456",opener=opener)
        self.assertEqual(data, {"available": False, "events": 0, "fatal": None, "error": "NETWORK_OR_STREAM_ERROR"})


if __name__ == "__main__":
    unittest.main()

