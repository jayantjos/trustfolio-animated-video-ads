"""Strict pinned-Wan2.2 source patch for missing FlashAttention 2/3.

WanSelfAttention calls flash_attention() directly, which otherwise reaches
assert FLASH_ATTN_2_AVAILABLE on an image without flash-attn installed.
Use PyTorch CUDA FUSED FLASH SDP only, never the huge math backend on GPU.
The CPU path exists solely for tiny deterministic QA.
"""
from pathlib import Path

SOURCE = Path("/opt/Wan2.2/wan/modules/attention.py")
HELPER = '''
def _trustfolio_fused_sdpa_fallback(q, k, v, q_lens, k_lens, batch, lq,
                                   causal, dropout_p, softmax_scale, window_size):
    """Unpadded varlen SDPA with forced fused kernel on CUDA; no math GPU OOM."""
    from contextlib import nullcontext
    if window_size != (-1, -1):
        raise RuntimeError("WAN_SDPA_WINDOW_NOT_SUPPORTED")
    q_sizes = [int(n) for n in q_lens.tolist()]
    k_sizes = [int(n) for n in k_lens.tolist()]
    if (len(q_sizes) != batch or len(k_sizes) != batch
            or any(n != lq or n <= 0 for n in q_sizes)
            or any(n <= 0 for n in k_sizes)
            or sum(q_sizes) != q.size(0)
            or sum(k_sizes) != k.size(0)
            or sum(k_sizes) != v.size(0)):
        raise RuntimeError("WAN_SDPA_VARLEN_SHAPE_INVALID")
    output = []
    qp = kp = 0
    for qn, kn in zip(q_sizes, k_sizes):
        query = q[qp:qp + qn].transpose(0, 1).unsqueeze(0).contiguous()
        key = k[kp:kp + kn].transpose(0, 1).unsqueeze(0).contiguous()
        value = v[kp:kp + kn].transpose(0, 1).unsqueeze(0).contiguous()
        # A forced fused CUDA backend prevents falling back to O(N^2) math
        # attention that can exhaust VRAM on portrait 121-frame videos.
        context = (
            torch.nn.attention.sdpa_kernel(
                backends=[torch.nn.attention.SDPBackend.FLASH_ATTENTION])
            if query.is_cuda else nullcontext()
        )
        with context:
            y = torch.nn.functional.scaled_dot_product_attention(
                query, key, value, dropout_p=dropout_p,
                is_causal=causal, scale=softmax_scale)
        output.append(y.squeeze(0).transpose(0, 1).contiguous())
        qp += qn
        kp += kn
    return torch.cat(output, dim=0).unflatten(0, (batch, lq))


'''
ANCHOR = '        assert FLASH_ATTN_2_AVAILABLE\n'
ENTRY = 'def flash_attention(\n'


def patched_source(original: str) -> str:
    if (original.count(ANCHOR) != 1 or original.count(ENTRY) != 1
            or '_trustfolio_fused_sdpa_fallback' in original):
        raise ValueError("WAN_OFFICIAL_SOURCE_UNEXPECTED_OR_ALREADY_PATCHED")
    new = original.replace(ENTRY, HELPER + ENTRY, 1)
    new = new.replace(
        ANCHOR,
        '        if not FLASH_ATTN_2_AVAILABLE:\n'
        '            x = _trustfolio_fused_sdpa_fallback(\n'
        '                q, k, v, q_lens, k_lens, b, lq, causal,\n'
        '                dropout_p, softmax_scale, window_size)\n'
        '            return x.type(out_dtype)\n',
        1,
    )
    compile(new, "wan/modules/attention.py", "exec")
    return new


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    SOURCE.write_text(patched_source(source), encoding="utf-8")
    print("WAN5_PINNED_ATTENTION_FUSED_TORCH_SDP_FALLBACK_PATCH=PASS")


if __name__ == "__main__":
    main()
