#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="${1:?usage: convert.sh DIRECTORY}"

FONT_FILE="/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
LAYOUT_XML="ski-pov-1080p.xml"
PROFILE_FILE="ffmpeg-profiles.json"
FFMPEG_PROFILE="1080p"
OVERLAY_SIZE="1920x1080"
VENV_BIN="/home/joris/venv/bin"
CACHE_DIR="/tmp/gopro-cache"

if [[ ! -d "${INPUT_DIR}" ]]; then
  echo "missing directory: ${INPUT_DIR}" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/${LAYOUT_XML}" ]]; then
  echo "missing layout: ${ROOT_DIR}/${LAYOUT_XML}" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/${PROFILE_FILE}" ]]; then
  echo "missing profile file: ${ROOT_DIR}/${PROFILE_FILE}" >&2
  exit 1
fi

mkdir -p "${CACHE_DIR}"

mapfile -d '' mp4_files < <(
  find "${INPUT_DIR}" -maxdepth 1 -type f -iname '*.mp4' ! -iname '*-dashboard-*.mp4' -print0 | sort -z
)

if [[ ${#mp4_files[@]} -eq 0 ]]; then
  echo "no mp4 files found in ${INPUT_DIR}" >&2
  exit 0
fi

sequence=1
for input_file in "${mp4_files[@]}"; do
  base_name="$(basename "${input_file%.*}")"
  output_file="${INPUT_DIR}/${base_name}-dashboard-$(printf '%03d' "${sequence}").mp4"

  echo "rendering: ${input_file} -> ${output_file}"
  "${VENV_BIN}/gopro-dashboard.py" \
    --font "${FONT_FILE}" \
    --config-dir "${ROOT_DIR}" \
    --cache-dir "${CACHE_DIR}" \
    --layout xml \
    --layout-xml "${ROOT_DIR}/${LAYOUT_XML}" \
    --profile "${FFMPEG_PROFILE}" \
    --overlay-size "${OVERLAY_SIZE}" \
    "${input_file}" \
    "${output_file}"

  sequence=$((sequence + 1))
done
