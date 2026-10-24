# Approved-cost-only RunPod Network Volume stage

User confirmed the estimated $7/month for a 100GB Standard network volume on Oct 21, 2026. This is **not** the purchase execution. A separate write-scoped API key and safe datacenter verification are still missing. Existing readonly key RUNPOD_API_KEY stays unchanged.

Last live API refresh: 0 network volumes, 0 running GPU Pods, 3 compatible data centers. EU-RO-1 RTX 4090 24GB MEDIUM; EUR-IS-1 RTX 4090 LOW; US-IL-1 RTX 4090 LOW. These labels can change.

Planned volume: trustfolio-wan-models-v1, 100GB STANDARD in EU-RO-1. Estimated price from public RunPod docs is 100*$0.07=$7/month. Standard Network Volume outlives GPU termination and accumulates charges while idle. The volume cannot be moved to a different data center or shrunk.

Prepare/verify dry-run: GitHub Actions workflow `.github/workflows/runpod-storage-purchase.yml` push trigger performs a no-charge CPU-only audit. A charged purchase cannot fire from a push.

**Remaining user-side security step:** Create a separate **Restricted RunPod API key** with Network Volume Read/Write, Catalog Read Only, and Network Volume list/read access. Store it as `RUNPOD_STORAGE_WRITE_KEY` in the GitHub Actions protected Environment `runpod-paid-storage` (preferred) with reviewer protections. NEVER send the key in chat or commit it. The existing `RUNPOD_API_KEY` remains Read Only. If no environment exists, create it with manual approval requirements. This requires GitHub repository administration access not available to the assistant.

The `purchase` job requires a manual `workflow_dispatch` on the default branch, exact confirmation `CREATE_EXACTLY_100GB_EU-RO-1`, the protected environment and the separate write key, plus live candidate stock MEDIUM/HIGH, and no conflicting existing volume. The feature-branch PR is draft, so **no purchase job can execute now**. Do not merge just to spend money: first review environment protection and workflow.

The Python script uses the verified REST POST /v2/network-volumes with `name`, `size`, `dataCenter`, `type` and checks HTTP 201, repeats GET to verify the created volume by ID. Ambiguous POST errors are NOT automatically retried. No GPU provisioning, model transfers, video render or social publishing are enabled.

References: https://docs.runpod.io/api-reference-v2/network-volumes/create-a-network-volume and https://docs.runpod.io/storage/network-volumes .
