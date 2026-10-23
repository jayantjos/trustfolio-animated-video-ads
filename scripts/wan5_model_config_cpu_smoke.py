"""CPU-only *real* upstream WanModel config instantiation with META tensors.

The approved Wan-AI/Wan2.2-TI2V-5B config.json is only 251 bytes. These
values come from the pinned original 921dbaf3 checkpoint already SHA256
verified on RunPod. No GPU, model weight loading, RunPod API or billing.
"""
import json
import torch
from wan.modules.model import WanModel

CONFIG = {
    "_class_name": "WanModel",
    "_diffusers_version": "0.33.0",
    "dim": 3072,
    "eps": 1e-6,
    "ffn_dim": 14336,
    "freq_dim": 256,
    "in_dim": 48,
    "model_type": "ti2v",
    "num_heads": 24,
    "num_layers": 30,
    "out_dim": 48,
    "text_len": 512,
}
assert not torch.cuda.is_available(), "CPU_ONLY_JOB_GPU_VISIBLE_REFUSE"
with torch.device("meta"):
    model = WanModel.from_config(CONFIG)
assert isinstance(model, WanModel)
assert model.model_type == "ti2v"
assert model.num_layers == 30
meta_params = list(model.parameters())
assert meta_params and all(param.is_meta for param in meta_params)
print("WAN_MODEL_5B_REAL_CONFIG_META_CONSTRUCTION=PASS")
print("WAN_MODEL_WEIGHTS_LOADED=FALSE_GPU_BILLING=FALSE")
