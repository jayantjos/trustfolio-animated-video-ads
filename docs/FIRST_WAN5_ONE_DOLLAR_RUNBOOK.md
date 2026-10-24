# First paid Wan2.2 genuine image-to-video test: authorized cap $1

User approved up to **$1 total GPU cost** for one first 5-second silent scene with their original pink-kurta lady. This replaces prior 0 GPU spending consent ONLY for this one job, not recurring paid GPU jobs. Network Volume billing of ~$7/month continues separately. No publication is authorized.

Input art:
- original `pink_kurta_lady_v1.png` exactly 2,484,010 bytes
- SHA-256 `7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6`
- S3 path `assets/characters/shared/pink_kurta_lady_v1.png`; current GH/S3 audit shows MISSING.
- The 30s panel storyboard the user sent is a visual story reference, NOT the single original character hero frame.
- Wan2.2 weights are 9 files 34,180,083,066 bytes verified on S3; one 5sec clip still requires real inference.

Preflight workflow `.github/workflows/first-wan5-gpu-preflight.yml` checks **GET-only** RunPod GPU catalog price, candidate region, existing volume, one test-specific Pod secret presence (never value), S3 original art, and no existing video pods. No Pod POST, no GPU spend.

Blocks for real paid test: approved original binary must be uploaded to GitHub or S3; separate RunPod Pods write-key stored as `RUNPOD_POD_WRITE_KEY` without sharing it in chat; real GPU worker and verified provider-side termination plus independent cleanup/reaper and a credit/budget cap. RunPod API v2 Create Pod's published request schema does not currently promise a `terminateAfter` body property. RunPod CLI documents `--terminate-after` but does not mean raw REST supports it, so never assume. Do not use STOP as substitute for DELETE. The exact live hourly GPU quote, not user estimate, must be checked to stay under $1.

Read-only probes do not test ability to CREATE/DELETE using key, nor does a working model S3 artifact guarantee 24 GB GPU inference will fit.
