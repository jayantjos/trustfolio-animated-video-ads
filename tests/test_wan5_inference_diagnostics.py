"""GPU-free tests for streaming inference diagnostics and hard timeout."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import wan5_gpu_worker as w


class StreamDiagnosticsTests(unittest.TestCase):
    def test_subprocess_error_preserves_only_bounded_tail_and_classifies_oom(self):
        with tempfile.TemporaryDirectory() as directory:
            script = "import sys; print('torch.OutOfMemoryError: CUDA out of memory'); sys.exit(1)"
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(subprocess.CalledProcessError) as cm:
                    w.run_inference_streamed(
                        [sys.executable, "-c", script], cwd=directory,
                        env=os.environ.copy(), timeout=10)
            self.assertEqual(cm.exception.returncode, 1)
            self.assertLessEqual(len(cm.exception.output), 32768)
            self.assertEqual(w.classify_inference_failure(cm.exception.output),
                             "CUDA_OUT_OF_MEMORY")

    def test_success_keeps_live_streaming(self):
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = w.run_inference_streamed(
                    [sys.executable, "-c", "print('GPU_INFERENCE_SMOKE_CPU_ONLY')"],
                    cwd=directory, env=os.environ.copy(), timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn("GPU_INFERENCE_SMOKE_CPU_ONLY", stdout.getvalue())

    def test_timeout_kills_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.TimeoutExpired):
                w.run_inference_streamed(
                    [sys.executable, "-c", "import time; time.sleep(4)"],
                    cwd=directory, env=os.environ.copy(), timeout=0.25)

    def test_persisted_subprocess_evidence_is_safe_bounded_and_useful(self):
        import hashlib
        import json
        from unittest.mock import patch
        raw = b"private credential=HIDE_THIS" + bytes([10]) + b"RuntimeError: unexpected model error" + bytes([10])
        details = w.sanitized_inference_evidence(raw, 1)
        self.assertEqual(details["python_exception_type"], "RuntimeError")
        self.assertEqual(details["subprocess_output_tail_bytes"], len(raw))
        self.assertEqual(details["subprocess_output_tail_sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertIsNone(details["process_termination_signal"])
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "scene01.failure.json"
            with patch.object(w, "OUTDIR", Path(directory)), patch.object(w, "FAILURE", failure):
                w.write_failure_receipt("GPU_INFERENCE_OR_TOOLS_FAILED", 1, details)
            saved = json.loads(failure.read_text())
            self.assertEqual(saved["subprocess_diagnostics"]["python_exception_type"],
                             "RuntimeError")
            self.assertNotIn("credential", failure.read_text().lower())
            self.assertNotIn("HIDE_THIS", failure.read_text())

    def test_unknown_child_output_and_sigkill_are_not_assumed_oom(self):
        details = w.sanitized_inference_evidence(
            b"some arbitrary unmatched data", -9)
        self.assertEqual(details["python_exception_type"], "UNKNOWN")
        self.assertEqual(details["process_termination_signal"], 9)
        self.assertEqual(w.classify_inference_failure(b"unknown"), 
                         "GPU_INFERENCE_OR_TOOLS_FAILED")
        self.assertEqual(w.classify_inference_failure(
            b"std::bad_alloc"), "HOST_OR_DEVICE_MEMORY_EXHAUSTED")
        self.assertEqual(w.classify_inference_failure(
            b"RuntimeError: CUDA error: device-side assert triggered"),
            "CUDA_RUNTIME_FAILURE")

    def test_ansi_rank_tagged_traceback_is_detected_without_raw_text(self):
        import json
        from unittest.mock import patch
        raw = (b"private=DO_NOT_PRINT\\n"
               + bytes([27]) + b"[31m[rank0]: RuntimeError: secret token hidden"
               + bytes([27]) + b"[0m\\n"
               + b"Traceback (most recent call last):\\n")
        # Re-normalize the fixture's literal slash-n markers.
        raw = raw.replace(bytes([92, 110]), bytes([10]))
        details = w.sanitized_inference_evidence(raw, 1)
        self.assertEqual(details["python_exception_type"], "RuntimeError")
        self.assertTrue(details["traceback_marker_present"])
        with tempfile.TemporaryDirectory() as directory:
            failure = Path(directory) / "scene01.failure.json"
            with patch.object(w, "OUTDIR", Path(directory)), patch.object(w, "FAILURE", failure):
                w.write_failure_receipt("GPU_INFERENCE_OR_TOOLS_FAILED", 1,
                                        details, stage="WAN_INFERENCE")
            data = json.loads(failure.read_text())
            self.assertEqual(data["last_worker_stage"], "WAN_INFERENCE")
            self.assertEqual(data["subprocess_diagnostics"]["python_exception_type"],
                             "RuntimeError")
            self.assertNotIn("secret", failure.read_text().lower())
            self.assertNotIn("DO_NOT_PRINT", failure.read_text())

    def test_missing_colon_assertion_and_untrusted_stage_are_safely_handled(self):
        result = w.sanitized_inference_evidence(
            b"[rank2]: AssertionError" + bytes([10]), 1)
        self.assertEqual(result["python_exception_type"], "AssertionError")
        with tempfile.TemporaryDirectory() as directory:
            from unittest.mock import patch
            failure = Path(directory) / "scene01.failure.json"
            with patch.object(w, "OUTDIR", Path(directory)), patch.object(w, "FAILURE", failure):
                w.write_failure_receipt("UNEXPECTED_ERROR", stage="stage=PRIVATE_TOKEN")
            self.assertNotIn("stage=PRIVATE_TOKEN", failure.read_text())

    def test_all_safe_markers_are_from_fixed_allowlist(self):
        raw = (b"credential=NOT_LOGGED" + bytes([10])
               + b"std::bad_alloc; torch.distributed.elastic; segmentation fault;"
               + b" size mismatch for layer" + bytes([10]))
        report = w.sanitized_inference_evidence(raw, 1)
        self.assertEqual(report["safe_error_markers"], [
            "HOST_OOM_TEXT", "TORCH_DISTRIBUTED_ERROR_TEXT",
            "NATIVE_CRASH_TEXT", "MODEL_SHAPE_TEXT"
        ])
        self.assertNotIn("credential", repr(report))
        self.assertNotIn("NOT_LOGGED", repr(report))

    def test_diagnostics_are_allowlisted_no_raw_traceback(self):
        examples = {
            b"ModuleNotFoundError: No module named 'flash_attn'": "PYTHON_DEPENDENCY_MISSING",
            b"usage: generate.py error: unrecognized arguments: --wrong": "WAN_CLI_ARGUMENT_MISMATCH",
            b"FileNotFoundError: [Errno 2] No such file or directory": "MODEL_WEIGHT_OR_INPUT_MISSING",
            b"RuntimeError: CUDA error: invalid device function": "CUDA_RUNTIME_FAILURE",
            b"safetensors_rust.SafetensorError: issue loading": "MODEL_LOADING_FAILURE",
            b"my super secret password in random failure": "GPU_INFERENCE_OR_TOOLS_FAILED",
        }
        for output, reason in examples.items():
            with self.subTest(reason=reason):
                self.assertEqual(w.classify_inference_failure(output), reason)
        with tempfile.TemporaryDirectory() as directory:
            from unittest.mock import patch
            failure = Path(directory) / "scene01.failure.json"
            with patch.object(w, "OUTDIR", Path(directory)), patch.object(w, "FAILURE", failure):
                w.write_failure_receipt(
                    w.classify_inference_failure(b"secret password: CUDA out of memory"), 1)
            import json
            saved = json.loads(failure.read_text())
            self.assertEqual(saved["failure_reason"], "CUDA_OUT_OF_MEMORY")
            self.assertNotIn("secret", failure.read_text().lower())


if __name__ == "__main__":
    unittest.main()
