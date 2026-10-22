"""GPU-free Hindi audio codec and duration regression checks."""
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.wan5_audio_preflight import AudioQAError, inspect_mp3_bytes


FFMPEG_TOOLS_PRESENT = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


class AudioTechnicalQATests(unittest.TestCase):
    def synthetic_mp3(self, seconds):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "synthetic-tone-not-human-speech.mp3"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-y",
                 "-f", "lavfi", "-i", "sine=frequency=440:duration=" + str(seconds),
                 "-codec:a", "libmp3lame", "-ar", "24000", "-qscale:a", "3",
                 str(target)], check=True, timeout=20)
            return target.read_bytes()

    @unittest.skipUnless(FFMPEG_TOOLS_PRESENT, 'ffmpeg absent; exercised in dedicated GPU-free CI')
    def test_compatible_mp3_passes_decode_without_human_qa_claim(self):
        report = inspect_mp3_bytes(self.synthetic_mp3(4))
        self.assertTrue(report["technical_qa_passed"])
        self.assertTrue(3.9 < report["seconds"] < 4.2)
        self.assertNotIn("listening_qa_passed", report)

    @unittest.skipUnless(FFMPEG_TOOLS_PRESENT, 'ffmpeg absent; exercised in dedicated GPU-free CI')
    def test_six_second_dialogue_is_blocked_before_gpu(self):
        with self.assertRaisesRegex(AudioQAError, "FIVE_SECOND_COMPATIBLE"):
            inspect_mp3_bytes(self.synthetic_mp3(6))

    def test_invalid_mp3_is_blocked_before_gpu(self):
        with self.assertRaises(AudioQAError):
            inspect_mp3_bytes(b"not an MP3" * 3000)


if __name__ == "__main__":
    unittest.main()
