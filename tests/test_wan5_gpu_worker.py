import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import wan5_gpu_worker as w

class DummyFinished:
    def __init__(self, stdout=""):
        self.stdout = stdout

class WorkerTests(unittest.TestCase):
    def test_pinned_hero_and_model_shard_missing_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            img=Path(tmp)/"img.png"
            img.write_bytes(b"x")
            with self.assertRaisesRegex(w.RenderError,"HERO_MISSING_OR_SIZE_WRONG"):
                w.ensure_approved_files(img,Path(tmp),Path(tmp))
    def test_real_model_names_expected(self):
        self.assertEqual(len(w.MODEL_FILES), 9)
        self.assertEqual(sum(w.MODEL_FILES.values()), 34180083066)
    def test_gpu_min_vram_fail_closed(self):
        def fake(args, **kwargs):return DummyFinished("16384\n")
        with self.assertRaisesRegex(w.RenderError,"GPU_MIN_24GB_NOT_VERIFIED"):
            w.gpu_check(fake)
    def test_gpu_min_vram_pass(self):
        self.assertEqual(w.gpu_check(lambda args,**kwargs:DummyFinished("24564\n")),24564)
    def test_real_wan_image_to_video_generation_command(self):
        cmd=w.generate_command(Path("/tmp/scene01.pending.mp4"))
        self.assertEqual(cmd[cmd.index("--task")+1],"ti2v-5B")
        self.assertEqual(cmd[cmd.index("--frame_num")+1],"121")
        self.assertEqual(cmd[cmd.index("--size")+1],"704*1280")
        self.assertIn("--image",cmd)
        self.assertNotIn("--audio",cmd)
    def test_private_environment_required_without_gpu(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(w.RenderError,"PRIVATE_QA_ENV_NOT_ARMED"):
                w.render()
    def test_job_id_required_without_gpu(self):
        with patch.dict(os.environ,{"TRUSTFOLIO_PRIVATE_QA":"yes"},clear=True):
            with self.assertRaisesRegex(w.RenderError,"UNAPPROVED_PAID_GPU_JOB_ID"):
                w.render()
    def test_no_invalid_runtime(self):
        with patch.dict(os.environ,{"TRUSTFOLIO_PRIVATE_QA":"yes",
                                     "TRUSTFOLIO_GPU_JOB_ID":w.JOB_ID},clear=True):
            with self.assertRaisesRegex(w.RenderError,"RENDER_WALL_CLOCK_BOUND_INVALID"):
                w.render(seconds=3601)
    def test_ffprobe_fake_success(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"clip.mp4"
            p.write_bytes(b"x"*11000)
            fake=lambda *a,**k:DummyFinished(json.dumps({
                "streams":[{"codec_type":"video","height":1280,"width":704,"nb_frames":"121"}],
                "format":{"duration":"5.042"}}))
            self.assertEqual(w.check_video(p,fake),5.042)
    def test_ffprobe_rejects_fake_duration(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"clip.mp4";p.write_bytes(b"x"*11000)
            fake=lambda *a,**k:DummyFinished(json.dumps({
                "streams":[{"codec_type":"video","height":1280,"width":704}],
                "format":{"duration":"1.1"}}))
            with self.assertRaisesRegex(w.RenderError,"NOT_A_REAL_FIVE_SECOND_VIDEO"):
                w.check_video(p,fake)
    def test_missing_tokenizer_is_hard_pre_gpu_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(w.RenderError,"WAN_TOKENIZER_MISSING"):
                w.verify_tokenizer_dir(Path(tmp))
    def test_tokenizer_json_rejected_if_invalid_and_binary_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"google"/"umt5-xxl";folder.mkdir(parents=True)
            for name in w.TOKENIZER_FILES:
                (folder/name).write_bytes(b'{"ok":true}' if name.endswith(".json") else b"fake-model")
            with self.assertRaisesRegex(w.RenderError,"WAN_TOKENIZER_SHA256_MISMATCH"):
                w.verify_tokenizer_dir(root)
    def test_failure_receipt_has_only_safe_reason_not_raw_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt=Path(tmp)/"failure.json"
            with patch.object(w,"OUTDIR",Path(tmp)),patch.object(w,"FAILURE",receipt):
                w.write_failure_receipt("ModuleNotFoundError: secret PASSWORD",2)
            meta=json.loads(receipt.read_text())
            self.assertEqual(meta["status"],"FAILED_PRIVATE_WAN5")
            self.assertEqual(meta["return_code"],2)
            self.assertFalse(meta["social_publishing"])
            self.assertNotIn(":",meta["failure_reason"])

    def test_gpu_worker_never_uses_publishing(self):
        self.assertFalse(w.RECEIPT.name.endswith(".mp4"))
        self.assertEqual(w.JOB_ID,"wan5-laundry-first-20261021")

if __name__=="__main__":unittest.main()
