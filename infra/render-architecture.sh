#!/usr/bin/env bash
set -euo pipefail

SOURCE="docs/architecture/proofbid-google-cloud.mmd"
CONFIG="docs/architecture/mermaid-config.json"
SVG="docs/architecture/proofbid-google-cloud.svg"
PNG="docs/architecture/proofbid-google-cloud-1920x1080.png"

if [[ -z "${PUPPETEER_EXECUTABLE_PATH:-}" ]] && \
  [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
  export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
fi

npx --yes @mermaid-js/mermaid-cli@11.16.0 \
  --input "${SOURCE}" \
  --output "${SVG}" \
  --configFile "${CONFIG}" \
  --backgroundColor transparent \
  --width 1920

npx --yes @mermaid-js/mermaid-cli@11.16.0 \
  --input "${SOURCE}" \
  --output "${PNG}" \
  --configFile "${CONFIG}" \
  --backgroundColor '#F7F9FC' \
  --width 1920 \
  --height 1080

if command -v magick >/dev/null 2>&1; then
  magick "${PNG}" \
    -background '#F7F9FC' \
    -gravity center \
    -extent 1920x1080 \
    "${PNG}"
elif command -v sips >/dev/null 2>&1; then
  sips --padToHeightWidth 1080 1920 --padColor F7F9FC "${PNG}" >/dev/null
else
  echo "ImageMagick or macOS sips is required to enforce the 1920x1080 canvas" >&2
  exit 3
fi
