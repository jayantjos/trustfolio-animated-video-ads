"""Offline Wan2.2 parser contract against the exact upstream OCI environment.

Intentionally NO model loading, CUDA allocation, RunPod API, or billable GPU.
Only run this inside the already verified pinned Wan CUDA image with /qa mounted.
"""
import sys
from pathlib import Path

# Upstream's import-time device default probes CUDA. The shim affects only
# this no-GPU parser check and is NOT present in the paid inference worker.
import torch
torch.cuda.current_device = lambda: 0

sys.path.insert(0, "/opt/Wan2.2")
import generate
from scripts.wan5_gpu_worker import generate_command, MODEL, IMAGE, WAN_SOURCE

output = Path("/tmp/trustfolio_wan5_cli_parser_smoke_only.mp4")
command = generate_command(output)
original_argv = sys.argv
try:
    sys.argv = command[1:]
    parsed = generate._parse_args()
finally:
    sys.argv = original_argv

assert parsed.task == "ti2v-5B", "WRONG_WAN_TASK"
assert parsed.size == "704*1280", "UNSUPPORTED_VERTICAL_RESOLUTION"
assert parsed.frame_num == 121, "WRONG_FRAME_COUNT"
assert parsed.ckpt_dir == str(MODEL), "WRONG_MODEL_DIR"
assert parsed.image == str(IMAGE), "WRONG_IMAGE_INPUT"
assert parsed.save_file == str(output), "WRONG_VIDEO_OUTPUT"
assert parsed.sample_steps == 30, "WRONG_SAMPLING_STEPS"
assert parsed.offload_model is True, "CPU_OFFLOAD_DISABLED"
assert parsed.convert_model_dtype is True, "MODEL_DTYPE_CONVERSION_DISABLED"
assert parsed.t5_cpu is True, "T5_OFFLOAD_DISABLED"
assert not parsed.use_prompt_extend, "UNEXPECTED_EXTRA_MODEL_LOAD"
assert isinstance(parsed.prompt, str) and len(parsed.prompt) > 30
assert not output.exists(), "UNEXPECTED_VIDEO_GENERATION_DURING_PARSER_CHECK"
print("OFFLINE_UPSTREAM_WAN_CLI_ARGUMENTS_AND_IMPORTS=PASS")
print("NO_MODEL_LOADED_NO_GPU_NO_RENDER=TRUE")
