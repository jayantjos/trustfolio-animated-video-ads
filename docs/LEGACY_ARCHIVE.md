# Legacy GPU engine and recovery

Audit 2026-10-26. Do not delete historical branches, tags, PRs, workflow evidence or RunPod volumes.

- Original `main`: `382beb9beb25117c162c968a1a42b4f6cbb5746a`.
- Backup: `archive/pre-google-flow-cleanup-20261026`.
- Historical branches preserved: `feat/animated-engine-foundation` (26 files), `feat/washing-machine-character-video-pilot` (218 files), others.
- PR #8 remains open and untouched.
- **Preserved on clean branch:** manual emergency GPU Pod stop, independent WAN5/WAN9 Pod reapers, associated Python scripts and tests. These safety workflows are not video generators.
- **Removed from clean branch:** obsolete WAN5 video collector workflow; recoverable from main or archive.
- No paid GPU launch workflow added. No existing Pod, 100GB network volume, or social publishing changed.

Reviewable cleanup, not production deployment.
