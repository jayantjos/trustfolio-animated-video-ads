# Safe RunPod → GitHub connection (read-only first)

This is a **credential verification only** setup, not provisioning, charging, network-volume creation, or video rendering.

## RunPod account
1. In RunPod console's optional AI-agent onboarding modal, choose **Skip for now**; it does not automatically link this GitHub repository.
2. Visit https://console.runpod.io/user/settings/api-keys (if that link redirects, use console menu → Credentials → API Keys; the official RunPod docs are https://docs.runpod.io/get-started/credentials).
3. Create an API Key named `trustfolio-github-readonly`, with **Read Only** permissions. Do not select All/Read Write for the initial test.
4. Copy key privately; never paste key in a chat, issue, commit, screenshot, or workflow YAML.

## GitHub repository secret
1. Open https://github.com/jayantjos/trustfolio-animated-video-ads/settings/secrets/actions
2. Click **New repository secret**.
3. Secret name EXACTLY `RUNPOD_API_KEY`; value is the RunPod read-only key.
4. Save. This provides a credential to GitHub Actions; it is not a way to authorize any charges.

## Test
- A safe workflow is prepared at `.github/workflows/runpod-api-readonly-check.yml` on draft PR #8's feature branch.
- While the secret is absent, the branch push workflow logs `RUNPOD_CONNECTION=NOT_CONFIGURED`.
- When a key is saved, trigger the workflow from a new push on the pilot branch, or run it manually after it exists on the default branch. GitHub `workflow_dispatch` generally requires the workflow file to be present on the default branch.
- The workflow only sends **GET** requests to `https://api.runpod.io/v2/pods` and `https://api.runpod.io/v2/network-volumes`. It prints only a status (e.g. `READ_ONLY_CONNECTED`, `PODS_HTTP_401`, `NETWORK_VOLUMES_HTTP_403`) and never creates GPU or storage.
- A read-only key passing these calls does NOT prove GPU creation permissions, available balance, region compatibility, or auto-destroy. Those need a separate controlled stage.

Official references:
- https://docs.runpod.io/get-started/credentials
- https://docs.runpod.io/api-reference-v2/pods/list-pods
- https://docs.runpod.io/api-reference-v2/network-volumes/list-network-volumes
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets

Existing TrustFolio Ads publishing crons remain untouched. No GPU/volume is provisioned, no voice synthesis API or social publishing is called.
