# Wan2.2 TI2V-5B: traced FlashAttention assertion and safe fix

## Evidence and scope

- Diagnostic billable RunPod attempt: [GitHub Actions #39941800036](https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/39941800036).
- Worker reached `WAN_INFERENCE`, exited with `AssertionError`; captured upstream allowlisted traceback frame: `wan/modules/model.py:145`.
- This frame is the **call site**, not necessarily the innermost assertion. The worker's historical safe-frame allowlist excluded `wan/modules/attention.py`, so that exact inner frame was not retained in the public receipt.
- Exact upstream source is pinned to Wan-Video/Wan2.2 commit `1ea34ff48f87168174e12956e200b1d908b1c5ff`.
- Pinned [model.py:145](https://github.com/Wan-Video/Wan2.2/blob/1ea34ff48f87168174e12956e200b1d908b1c5ff/wan/modules/model.py#L143-L150) calls `flash_attention()` **directly** (not the optional `attention()` wrapper with math-SDPA fallback).
- Pinned [attention.py:112](https://github.com/Wan-Video/Wan2.2/blob/1ea34ff48f87168174e12956e200b1d908b1c5ff/wan/modules/attention.py#L93-L127) asserts `FLASH_ATTN_2_AVAILABLE` if FA3 is unavailable. CPU Docker logs independently show `WAN_ATTENTION_FA2_AVAILABLE=False` and `WAN_ATTENTION_FA3_AVAILABLE=False`.
- The upstream caller line, missing installed backends, and source assertion together identify the **missing FlashAttention implementation as the cause** of the observed assertion. Image dimensions and CUDA failure are not established as that assertion's root cause.
- The controller confirmed `PILOT_GPU_DELETE_RESULT=DELETE_GET_404_CONFIRMED`. No genuine MP4 was produced by this attempt.

## Fixed implementation and limits

- `gpu/patch_wan_attention.py` changes exactly the pinned FlashAttention 2 assertion path into `_trustfolio_fused_sdpa_fallback` with strict source-anchor validation.
- The fallback enforces PyTorch `SDPBackend.FLASH_ATTENTION` on CUDA, **not** the quadratic math attention backend, to avoid quietly exploding VRAM consumption for 121 frames. It rejects unsupported windows and malformed varlen shapes.
- Both `gpu/Dockerfile.wan5` and `gpu/Dockerfile.wan5-overlay` install the patch. The overlay is the CPU-QA-tested deployment approach.
- [Free worker watchdog QA #39943953864](https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/39943953864) succeeded on the pinned source/container. It reports `WAN5_VARLEN_TORCH_SDPA_CPU_EQUIVALENCE=PASS`, real MP3 CPU decode, Wan model config construction, and all jobs green.
- Controller, paid workflow, and the image-pinning regression test all use the **same immutable CPU-tested overlay** `ghcr.io/jayantjos/trustfolio-wan5-worker@sha256:77ad3c7235ccf9ea6fedbf32c7ad2198388f2004b66b6ed6768fd7acaa3f431f`.

## Remaining unverified requirement

**Do not claim GPU success from CPU tests.** The fused CUDA SDPA path still requires a *fresh user-approved* budget-limited paid GPU test with unchanged RunPod owner/volume restrictions, independent reaper, Pod auto-delete, and S3-GET / SHA-256 MP4 verification. In particular, CUDA fused kernel support for the actual 24 GiB GPU and full video-memory behavior is not proven by the CPU equivalence test. Publishing stays disabled. No follow-up paid test was launched for this fix.
