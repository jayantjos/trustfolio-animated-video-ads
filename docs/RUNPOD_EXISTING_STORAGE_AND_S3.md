# RunPod existing volume and S3 integration — 21 October 2026

**Already created manually by owner**, do not purchase duplicate.
- Volume name: `trustfolio-wan-models-v1`
- ID / S3 bucket: `1bch597yrz`
- Standard storage: 100 GB
- Location: EU-RO-1
- Volume browser screenshot: $7/month.
- S3 endpoint: https://s3api-eu-ro-1.runpod.io

After creating the storage, GitHub account read-only inventory returned 1 volume / 100 GB / 0 GPU Pods in run https://github.com/jayantjos/trustfolio-animated-video-ads/actions/runs/39574259330 . The new exact-volume GET verification is `python -m scripts.runpod_existing_volume`.

The original storage-purchase workflow was disabled because this volume ALREADY EXISTS. No RunPod storage write API key is required to connect GitHub to this existing volume.

## Separate S3 key — IMPORTANT
RunPod S3 credentials are **not** the existing `RUNPOD_API_KEY`.
1. Open https://console.runpod.io/user/credentials → **S3 API Keys** (not RunPod API Keys).
2. Create an S3 key for TrustFolio, save the access key and secret to a password manager. Do not screenshot, paste in chats, print in logs or commit credentials.
3. Under https://github.com/jayantjos/trustfolio-animated-video-ads/settings/secrets/actions create:
   `RUNPOD_S3_ACCESS_KEY_ID` = the RunPod S3 access-key ID (`user_...`).
   `RUNPOD_S3_SECRET_ACCESS_KEY` = the separately displayed RunPod S3 secret.
4. Run GitHub workflow `RunPod existing volume and S3 read-only verification`. It performs one GET of existing volume and one S3 list (MaxKeys=1), no writes. Without S3 secrets the workflow reports `S3_NOT_CONFIGURED`; its successful overall job is **not proof** of S3 connectivity unless status is `S3_CONNECTED_READ_ONLY`.

Official S3 docs: https://docs.runpod.io/storage/s3-api ; https://docs.runpod.io/storage/network-volumes

Once connected we can stage verified character, scenes and audio, and later pretrained model weights, directly to S3 without a GPU Pod. Models still require downloading and transferring to this network storage once (34.2 GB Wan2.2 checkpoint repo plus dependency/cache space); there has not yet been any model upload. S3 object paths map to `/workspace` when the volume is mounted on a Pod.

**No GPU Pod started, no Wan video rendered, no social publishing done.** Network volume storage billing accrues independently, and data loss can result if account balance cannot cover it.
