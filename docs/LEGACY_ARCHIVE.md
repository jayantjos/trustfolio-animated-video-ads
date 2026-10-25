# Old engine and recovery references

Audit date: 2026-10-26. Do **not** delete historical branches, tags, pull requests, workflow-run evidence, or existing RunPod network volumes during cleanup.

- Default branch before cleanup: `main`, commit `382beb9beb25117c162c968a1a42b4f6cbb5746a` (primarily independent GPU safety/reaper workflows and scripts).
- Explicit backup branch: `archive/pre-google-flow-cleanup-20261026`.
- Historical code: `feat/animated-engine-foundation` (26 files), `feat/washing-machine-character-video-pilot` (218 tracked files, dozens of GPU/test workflows); these and other feature branches remain untouched.
- Prior open PR #8 integrates the experimental washing-machine GPU pipeline against the foundation branch; **this cleanup does not merge or delete that PR**.
- This cleaned branch deliberately contains no runnable WAN2.2/RunPod GPU Actions; do not merge it over the default branch until ensuring no current reaper/safety automation is needed. Before adopting as default, evaluate and preserve any required emergency cleanup controls out of band.

Removal in the proposed clean tree is *branch-only*. The original contents remain accessible on `main`, the archive branch, historical feature branches, and commit history. No paid GPU task and no social posting should be triggered.
