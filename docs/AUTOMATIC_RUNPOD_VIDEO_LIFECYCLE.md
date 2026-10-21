# GPU automatic create → existing storage → render → S3 verification → destroy

This is the **tested lifecycle controller** for the user-requested pipeline, NOT a paid GPU job. Entry: `scripts/runpod_video_lifecycle.py`. The default CLI does no HTTP requests and cannot provision a Pod. Its lifecycle runner requires injected, independently verified provider API / GPU worker / S3 checksum adapters.

Required stages:

1. Trusted other-VPS cron sends a live, validated fresh Top-5 event. Recheck freshness just before render; prevent duplicates via durable ledger.
2. Confirm approved account GPU rate, remaining budget, exact 60m lifetime, 1 Pod at a time, region EU-RO-1, RTX 4090 compatibility, plus completed asset QA.
3. POST `/v2/pods` with `mounts.network=[{"volumeId":"1bch597yrz","path":"/workspace"}]` and `dataCenterIds=["EU-RO-1"]`. Must attach ONLY existing volume and never create any new storage. If POST returns ambiguous failure, reconcile by unique Pod name and terminate orphan; never retry blindly.
4. On actual GPU worker, use pinned Wan2.2 model weights and approved character/locations and Hindi audio from network volume. Execute I2V/lip-sync using licensed pinned code. No inference worker is deployed yet.
5. Persist 30-sec MP4 and QA receipt to unique `videos/private-qa/<job_id>/` object paths on existing S3. Independently GET/hash verify. Final animated output has not been produced yet.
6. In `finally`: terminate exact video Pod (not merely stop) even on inference error. Confirm deleted via GET. Never delete network volume.
7. A separate independent reaper is required to survive process crashes and GPU container failure; GitHub hourly watchdog `runpod-video-pod-watchdog.yml` currently **READ ONLY ALERT**, not a production reaper. GitHub cron is best effort. Confirm provider-native `terminate-after` at actual provisioning and test true deletion. Do not allow paid creation without this.
8. Only when real video and lip sync pass separate QA would a later separately approved publishing pipeline become relevant. All publishing is disabled.

**Current blockers:** GPU spend not authorized ($0 separate from $7/month network volume), Pod write-scoped key unavailable, provider-native TTL not verified in v2, actual pinned worker container not created or tested, independent live reaper not configured, original pink-kurta master not uploaded to S3, 3 washing scene images missing, real API cron trigger not connected. No charged GPU Pod created.

RunPod v2 API contract: https://docs.runpod.io/api-reference-v2/pods/create-a-pod. Pod termination: https://docs.runpod.io/runpodctl/reference/runpodctl-remove-pods. The 100 GB network volume survives Pod termination and continues its $7/month storage charge.

The lifecycle unit tests simulate both success and failure and ensure termination is always requested in finally. **Simulated termination does not prove RunPod actually destroyed a GPU**. Any paid production activation requires another verified end-to-end run, user-approved spending threshold and secrets configured in protected GitHub environment.
