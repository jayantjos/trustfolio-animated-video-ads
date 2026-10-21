# TrustFolio Wan2.2 pinned model → RunPod S3 streaming transfer

**Initial phase: ONLY \`config.json\` smoke upload and downloaded checksum verification.** No GPU, no new volume, no Meta publishing. Existing volume \`1bch597yrz\`, 100GB Standard EU-RO-1, verified with GitHub Read Only API.

Official model: https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B, Apache-2.0. Pinned SHA \`921dbaf3f1674a56f47e83fb80a34bac8a8f203e\`, total 34.2GB. Use SHA-pinned paths, not dynamic \`main\`.

Standard private GitHub Actions runner has 14GB disk, too small to store the whole Wan model. The upload utility instead streams one Hugging Face file into S3 using boto3 TransferConfig multipart for files larger than 64MB, with one transfer thread. After upload, checks upstream Hugging Face LFS SHA256 for weights, size and remote GET SHA256 byte-for-byte. No 34GB temporary files on the runner. For long uploads, GitHub Actions minutes and network usage should be tracked; *GPU zero cost is not equivalent to zero overall compute/network cost*.

- Script: \`scripts/runpod_model_transfer.py\`.
- Unit tests: \`tests/test_runpod_model_transfer.py\`.
- GitHub workflow: \`.github/workflows/wan-model-upload-test.yml\`.
- Configuration: \`config/wan_model_transfer.json\`.
- Destination: \`s3://1bch597yrz/models/Wan2.2-TI2V-5B/921dbaf3f1674a56f47e83fb80a34bac8a8f203e/\`.
- Existing secrets: \`RUNPOD_S3_ACCESS_KEY_ID\`, \`RUNPOD_S3_SECRET_ACCESS_KEY\`, already read-tested; do not paste into chat.

Runpod documents its multipart S3 API for >500MB weights: https://docs.runpod.io/storage/s3-api. Files are visible under \`/workspace/models/Wan2.2-TI2V-5B/...\` when a compatible Pod mounts the volume.

The transfer uses immutable object keys, checks exact source SHA256 and remote integrity, and refuses silently replacing existing mismatched objects. The small config phase **does not make a complete useable model**. Next separate stages need VAE, diffusion three shards, T5, index+configuration JSON, each with capacity/usage limits, independent per-file checks and resumable skip-if-verified behavior.

No assets or Hindi MP3 are uploaded in this phase; they will be staged separately. Do not start GPU or rendering from partial model weights.
