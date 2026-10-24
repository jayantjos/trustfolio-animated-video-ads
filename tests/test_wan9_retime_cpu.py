"""Real CPU ffmpeg verification of low-cost 49-frame Wan2.2 output retiming.

Creates SYNTHETIC color-test frames, never represents them as GPU animation.
No RunPod keys, no network, and no provider billing.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts import wan5_nine_scene_gpu_worker as w

class TestWan9FFmpegRetime(unittest.TestCase):
    def test_exact_native_49_frame_wan_shape_stretches_to_five_second_video(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.fail("ffmpeg and ffprobe required for paid GPU readiness")
        with tempfile.TemporaryDirectory() as td:
            raw=Path(td)/"synthetic-49.mp4"
            final=Path(td)/"retimed-private-qa.mp4"
            subprocess.run(["ffmpeg","-v","error","-nostdin","-y",
                "-f","lavfi","-i","testsrc2=size=288x512:rate=24",
                "-frames:v","49","-c:v","libx264","-preset","ultrafast",
                "-pix_fmt","yuv420p",str(raw)],
                check=True,timeout=65)
            metadata=w.retime_native_wan_to_five_seconds(raw,final)
            self.assertEqual(49,metadata["native_model_frames"])
            self.assertEqual(8,metadata["native_sampling_steps"])
            self.assertFalse(metadata["is_original_native_121_frame_quality"])
            self.assertTrue(metadata["artificial_frames_used"])
            self.assertTrue(raw.exists())
            self.assertTrue(final.exists())
            d=w.check_video(final)
            self.assertTrue(4.8<=d<=5.3)
            self.assertGreater(final.stat().st_size,10000)

if __name__=="__main__":
    unittest.main()
