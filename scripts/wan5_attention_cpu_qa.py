"""Inside the exact pinned PyTorch OCI image: test patched Flash SDPA semantics on CPU."""
import sys
from pathlib import Path
import torch
sys.path.insert(0, "/qa")
from gpu.patch_wan_attention import patched_source

original = Path("/opt/Wan2.2/wan/modules/attention.py").read_text(encoding="utf-8")
if "_trustfolio_fused_sdpa_fallback" in original:
    patched=original
else:
    patched=patched_source(original)
ns={"__name__":"wan.modules.attention"}
exec(compile(patched,"wan/modules/attention.py","exec"),ns)
helper=ns["_trustfolio_fused_sdpa_fallback"]
for batch, lq, lk in [(1,4,4),(1,4,3),(2,4,3)]:
    torch.manual_seed(42)
    heads, dim=2,8
    q=torch.randn(batch*lq,heads,dim)
    k=torch.randn(batch*lk,heads,dim)
    v=torch.randn(batch*lk,heads,dim)
    sizes_q=torch.tensor([lq]*batch,dtype=torch.int32)
    sizes_k=torch.tensor([lk]*batch,dtype=torch.int32)
    result=helper(q,k,v,sizes_q,sizes_k,batch,lq,False,0.0,None,(-1,-1))
    expected=torch.cat([
        torch.nn.functional.scaled_dot_product_attention(
            q[i*lq:(i+1)*lq].transpose(0,1).unsqueeze(0),
            k[i*lk:(i+1)*lk].transpose(0,1).unsqueeze(0),
            v[i*lk:(i+1)*lk].transpose(0,1).unsqueeze(0)
        ).squeeze(0).transpose(0,1)
        for i in range(batch)
    ],dim=0).unflatten(0,(batch,lq))
    assert torch.allclose(result,expected,atol=1e-5), (batch,lq,lk)
try:
    helper(torch.randn(4,2,8),torch.randn(3,2,8),torch.randn(3,2,8),
           torch.tensor([4]),torch.tensor([3]),1,4,False,0.,None,(8,8))
except RuntimeError as exc:
    assert str(exc)=="WAN_SDPA_WINDOW_NOT_SUPPORTED"
else:
    raise AssertionError("BAD_WINDOW_ACCEPTED")
assert "SDPBackend.FLASH_ATTENTION" in patched
assert not torch.cuda.is_available(), "CPU_ONLY_NO_GPU_EXPECTED"
print("WAN5_VARLEN_TORCH_SDPA_CPU_EQUIVALENCE=PASS")
print("WAN5_CUDA_WILL_FORCE_FUSED_FLASH_SDPA_NO_MATH_FALLBACK=VERIFIED_BY_SOURCE")
