# RunPod storage / GPU preflight — NO CHARGES
The initial RunPod GitHub read-only credential has been verified. This branch now runs API GET-only inventory to list counts of current Pods and independent Network Volumes, and discover matching STANDARD-volume + 24GB/48GB NVIDIA GPU data centers.
No GPU Pod or Network Volume is created, modified, or terminated.

First Wan2.2-TI2V-5B model files: approximately 34.2 GB at https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B/tree/main.
The proposed 100 GB STANDARD network volume is a capacity target to review, not a purchase; RunPod lists Standard network storage at $0.07/GB/month, so estimate $7/month even while GPU is off: https://docs.runpod.io/storage/network-volumes.
RunPod docs require volume and GPU to be compatible with the same data center: https://docs.runpod.io/api-reference-v2/catalog/list-data-centers.
The first test may require 24GB GPU minimum (model might OOM): https://github.com/Wan-Video/Wan2.2.
GPU prices on https://www.runpod.io/pricing are public reference prices, not confirmed price/stock for the user's volume-compatible region.

Runbook: use GitHub Action 'RunPod storage read-only preflight'; it stores a 7-day artifact 'runpod-storage-readonly-inventory' with sanitized counts and compatible data center candidates. It does not print API secrets, Pod names, Pod IDs or volume IDs. Treat snapshot as temporary. The API returns availability labels (HIGH, MEDIUM, LOW) but it is NOT a reservation or billed quote.

BEFORE STORAGE/GPU PURCHASE:
1. Confirm the chosen data center has both STANDARD network volume and suitable GPU capacity.
2. Audit actual total model + lip-sync checkpoints, scene files and intermediate rendered MP4 storage.
3. Approve paid storage, write-scoped credentials and a charged single-GPU trial separately.
4. Implement authenticated model file upload, SHA verification, durable MP4 upload, and a separate crash-safe GPU cleanup workflow. Never claim that a GitHub job timeout alone prevents GPU billing.
5. Confirm maximum runtime and dollar cap, exact GPU price in account, no other Pods, and cleanup verification before any provision call.
Social publishing remains disabled and existing TrustFolio image-ad crons untouched.
