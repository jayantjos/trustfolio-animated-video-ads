# RunPod Live Account Preflight — 2026-10-21

Evidence: [GitHub Actions Run 39574259330](https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/39574259330) and artifact `runpod-storage-readonly-inventory` (7-day retention).

- Read-only GitHub secret authentication: PASS.
- GET /v2/pods: PASS, 0 Pods.
- GET /v2/network-volumes: PASS, **0 existing Network Volumes and 0 GB allocated**.
- GET /v2/catalog/datacenters?include=GPU_AVAILABILITY: PASS.
- All four local RunPod read-only safety tests: PASS.
- No POST, PATCH, DELETE, GPU charge, storage creation, MP3 generation, or video rendering.

## 5 matching datacenter options at the time of query

| Data Center | Region | GPU from live catalog | VRAM | Availability |
|---|---|---|---:|---|
| EU-CZ-1 | Europe | RTX 3090 | 24 GB | LOW |
| EU-RO-1 | Europe | RTX 4090 | 24 GB | MEDIUM |
| EUR-IS-1 | Europe | RTX 4090 | 24 GB | LOW |
| US-IL-1 | North America | RTX 4090 | 24 GB | LOW |
| US-MO-1 | North America | L40S | 48 GB | LOW |

Other datacenters or GPU models might be available; the first candidate discovery script intentionally only covers a conservative small list of Wan2.2-suitable 24GB/48GB cards. The availability labels are **not binding reservations**. Candidate GPU pricing by region is **not verified in the account**.

The best STOCK shown was RTX 4090 at EU-RO-1 (MEDIUM), but it is 24 GB VRAM with possible real-world OOM for 5B. US-MO-1 has 48GB L40S with more memory margin but LOW availability. **Do not create a region-bound Network Volume until a preferred GPU/region is selected with live pricing and exact model QA.**

## Storage sizing and charge

- Wan2.2 TI2V-5B weights/model repository: ~34.2GB, from https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B/tree/main.
- Additional files needed: lip-sync weights (not yet chosen/downloaded), fixed master images, Hindi audio, code, package/cache, all scene video intermediate outputs and final MP4.
- Preliminary Standard Network Volume proposal: 100 GB. Public Standard storage fee $0.07/GB/month → about **$7/month while the Volume exists**, whether or not the GPU is running. Need confirm room for intermediates before paying.
- Some RunPod SKU 24GB GPUs may need CPU offload and can still OOM, especially multi-scene workflows. Exact fit/performance untested. https://github.com/Wan-Video/Wan2.2.
- Actual GPU hourly rate and storage region billed quote require a separate write-authorized account-specific preflight, not yet done.

**Current approved scope:** Read-only preparation only. `config/runpod_washing_gpu_policy.json` keeps paid GPU provisioning, storage creation, and publishing disabled. Before any purchase: confirm storage size, output transfer plan, GPU hourly price, spending cap and a verified crash-safe GPU cleanup process. Continue the first Washing Machine category only after those gates.

No change to TrustFolio existing image ad system or Meta/YouTube publishing.
