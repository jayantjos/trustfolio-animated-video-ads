# Upload EXACT approved TrustFolio woman once
Source artwork is `trustfolio_washing_master_v1.png` (941x1672 PNG, 2,484,010 bytes, sha256 7f9ca4e47803ff9df57ff389ede1bba15eb6cb761c2fe4521edfe4036bc20ac6).
Do not use the old rejected alternate image; do not regenerate/recolor/recompress this file. It must be byte-identical.

Repo path: `assets/characters/shared/pink_kurta_lady_v1.png` in feature branch `feat/washing-machine-character-video-pilot`.
One upload via the GitHub repository web UI triggers `.github/workflows/stage-approved-character.yml`. GitHub Action checks exact bytes, then uploads the already-owned master to S3 at identical key. It refuses wrong images and does not use any GPU or publisher.

**Current status before user uploads that one original image:** SOURCE_FILE_PRESENT_IN_CHAT_RUNTIME_ONLY; S3 CHARACTER NOT VERIFIED.
Keep all 20 category character references pointing to this one canonical PNG.
