# Isolation, deployment and rollback

No deployment has occurred. This foundation requires no VPS change: only public
read-only category and product endpoints are used. No repository secret is
required for static or storyboard CI. Keep video publishing hard-disabled.

Do not enable a cron, production deploy workflow, or social write endpoint as a
side effect of merging this foundation. Keep PR draft until scope and blockers
are reviewed. Existing image repo paths, deployment allowlists, schedules,
tokens, publishing ledgers and services are out of scope.

To discard this draft, close its PR and delete only its feature branch. To undo
a later foundation merge, revert that merge in this new repository. Never
force-push the old image repository or restart its services.

For a future separately approved deployment: install under a dedicated versioned
video-engine release directory, record commit and artifact hashes, preserve the
previous release, validate read-only health and disk/memory limits, then switch
only the new engine's release pointer. Roll back that pointer on failure. These
are future instructions, not a tested deployment/rollback claim.

Large models and videos must not enter ordinary Git history. Future models need
license, provenance, checksums and resource review before download. Use Actions
artifacts for generated previews and appropriate model/media storage for large
assets. No third-party model, audio or copyrighted character has been added.
