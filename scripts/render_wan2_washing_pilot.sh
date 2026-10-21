#!/usr/bin/env bash
# Image-to-video ONLY for 5-second washing-machine intro, NOT a complete Reel.
set -Eeuo pipefail
[[ "${TRUSTFOLIO_APPROVED_EXISTING_GPU:-}" == "yes" ]] || { echo "BLOCKED: GPU approval missing; will not create/rent GPU" >&2; exit 2; }
[[ "${TRUSTFOLIO_GPU_COST_PER_HOUR_USD:-unverified}" == "0" ]] || { echo "BLOCKED: verified $0/hour GPU required by pilot policy" >&2; exit 2; }
command -v nvidia-smi >/dev/null || { echo "BLOCKED: no NVIDIA GPU" >&2; exit 2; }
vram="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d '[:space:]')"
[[ "$vram" =~ ^[0-9]+$ && "$vram" -ge 23000 ]] || { echo "BLOCKED: Wan2.2 TI2V-5B needs ~24GB VRAM" >&2; exit 2; }
: "${WAN2_REPO:?Set local checked-out official Wan2.2 repository}"
: "${WAN2_CKPT:?Set local downloaded official Wan2.2-TI2V-5B weights}"
: "${TRUSTFOLIO_HERO_IMAGE:?Set approved hero image path}"
: "${WAN2_OUTPUT:?Set full path for silent scene01 mp4}"
[[ -f "$WAN2_REPO/generate.py" && -d "$WAN2_CKPT" && -f "$TRUSTFOLIO_HERO_IMAGE" ]] || { echo "BLOCKED: missing code, checkpoint or image" >&2; exit 2; }
# Immutable full-resolution canonical image; never use a random substitute.
python -m trustfolio_video.verify_asset --image "$TRUSTFOLIO_HERO_IMAGE" --pilot config/pilots/washing-machines.json
mkdir -p "$(dirname "$WAN2_OUTPUT")"
(
 cd "$WAN2_REPO"
 python generate.py --task ti2v-5B --size '704*1280' --ckpt_dir "$WAN2_CKPT" \
   --offload_model True --convert_model_dtype --t5_cpu \
   --frame_num 121 --image "$TRUSTFOLIO_HERO_IMAGE" --prompt \
   'Animate this exact premium 3D cartoon Indian woman in pink kurta, she is surprised by the huge laundry pile, naturally blinking and making a small head turn, preserve exact face, clothes, courtyard and basket, no text, no redesign.' \
   --save_file "$WAN2_OUTPUT"
)
ffprobe -v error -show_entries stream=codec_name -of default=noprint_wrappers=1 "$WAN2_OUTPUT"
echo 'SCENE01_ONLY_NO_LIPSYNC_AND_NO_PUBLISH'
