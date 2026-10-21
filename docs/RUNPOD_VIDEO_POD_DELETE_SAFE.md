# GPU Pod termination safety implementation (dry-run only)

This stage adds a **client-side per-job cleanup script**, not a deployed reaper and not an authorized GPU purchase. `scripts/runpod_video_pod_cleanup.py` defaults to no network call.

After an authorized future GPU render:
- Owner MUST store the exact Pod ID (not arbitrary provider Pods) and job ID in the authenticated job ledger.
- First GET `https://api.runpod.io/v2/pods/{id}` and match name `trustfolio-video-{job_id}`, matching network volume `1bch597yrz`.
- After verified MP4+SHA on S3, DELETE only `/v2/pods/{id}`; on render failure/emergency skip MP4 presence check to prevent continued GPU charges.
- Require explicit `--apply`, separate `RUNPOD_POD_WRITE_KEY` (never share in chat), and `TRUSTFOLIO_POD_DELETE_ARMED=yes`. Refuse all arbitrary Pod IDs.
- Poll GET until 404; deletion without subsequent 404 is a critical alert, **NOT** proof stopped billing.
- No call ever deletes network-volume `1bch597yrz`. The 100GB persistent volume continues $7/month independently.
- Provider auto-`terminate-after` and an independent scheduled external watcher must still be integrated to cover total worker failures and instance crashes. Until those exist, **GPU_CREATE_DISABLED**.
- The returned Pod fields `networkVolumeId` / `mounts.networkVolume.id` are conservative accepted ownership shapes; confirm actual API v2 GET shape in a read-only check against an authorized test Pod before trusting live cleanup.
- Official API mapping: `DELETE /v2/pods/{id}`, https://github.com/runpod/runpod-plugins-official/blob/main/plugins/runpod/skills/runpod-migrate/reference/graphql-to-v2.md

Do not attach a broad write key just to run dry-run tests. No GPU Pod created or destroyed by this workflow.
