"""Run against the pinned existing CUDA image, without a GPU or credentials."""
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
import torch
# Only the upstream import-time CUDA default argument needs a CPU test shim.
torch.cuda.current_device=lambda:0
import sys
sys.path.insert(0,'/opt/Wan2.2')
import wan
import generate
from transformers import AutoTokenizer
AutoTokenizer.from_pretrained('/qa/output/wan5-readonly/tokenizer',local_files_only=True)
spec=importlib.util.spec_from_file_location('worker','/qa/scripts/wan5_gpu_worker.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
try:w.render()
except w.RenderError as exc:assert str(exc)=='PRIVATE_QA_ENV_NOT_ARMED'
else:raise AssertionError('Unarmed startup allowed')
with tempfile.TemporaryDirectory() as td:
    root=Path(td);video=root/'synthetic-test-only.mp4';speech=root/'tone-test-only.wav';out=root/'mux-test-only.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=352x640:r=24:d=5','-c:v','libx264',str(video)],check=True)
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=4','-c:a','pcm_s16le',str(speech)],check=True)
    w.mux_hindi(video,speech,out)
    assert 4.8<=w.check_video(out)<=5.3
print('PINNED_IMAGE_IMPORTS_TOKENIZER_FFMPEG_FFPROBE_DECODE_AND_UNARMED_STARTUP=PASS')
print('SYNTHETIC_CODEC_TEST_ONLY_NOT_REAL_VIDEO_OR_HINDI_QA')
