"""CPU-only media preflight. Never substitutes for human Hindi listening QA.

It checks the exact S3 bytes before a billable GPU can be created.
"""
import json
import subprocess
import tempfile
from pathlib import Path


class AudioQAError(RuntimeError):
    pass


def inspect_mp3_bytes(data):
    if not isinstance(data, bytes) or not 3000 <= len(data) <= 5 * 1024 * 1024:
        raise AudioQAError("HINDI_AUDIO_BAD_SIZE_NO_GPU")
    try:
        with tempfile.TemporaryDirectory(prefix="wan5-audio-qa-") as directory:
            source = Path(directory) / "exact-hindi-candidate.mp3"
            source.write_bytes(data)
            probed = subprocess.run(
                ["ffprobe", "-v", "error", "-print_format", "json",
                 "-show_entries", "format=duration:stream=codec_type,codec_name,sample_rate",
                 str(source)], capture_output=True, text=True, check=True, timeout=20)
            meta = json.loads(probed.stdout)
            streams = [s for s in meta.get("streams", []) if s.get("codec_type") == "audio"]
            duration = float(meta.get("format", {}).get("duration", 0))
            if len(streams) != 1 or streams[0].get("codec_name") != "mp3":
                raise AudioQAError("HINDI_AUDIO_NOT_SINGLE_MP3_STREAM_NO_GPU")
            if not 1.0 <= duration <= 5.0:
                raise AudioQAError("HINDI_DIALOGUE_NOT_FIVE_SECOND_COMPATIBLE_NO_GPU")
            if int(streams[0].get("sample_rate", 0)) < 16000:
                raise AudioQAError("HINDI_AUDIO_SAMPLE_RATE_INVALID_NO_GPU")
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(source),
                 "-f", "null", "-"],
                capture_output=True, check=True, timeout=30)
            return {"technical_qa_passed": True, "seconds": round(duration, 3),
                    "codec": "mp3", "sample_rate_hz": int(streams[0]["sample_rate"])}
    except AudioQAError:
        raise
    except (OSError, ValueError, TypeError, subprocess.SubprocessError, KeyError):
        raise AudioQAError("HINDI_AUDIO_CODEC_OR_DECODING_INVALID_NO_GPU") from None
