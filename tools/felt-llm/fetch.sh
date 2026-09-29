#!/bin/bash
# felt-llm model files (WP-36 rev 2): Gemma 4 12B QAT q4_0 + its vision
# projector, from Google's official GGUF repo, into /home/ai-models/gguf on
# the server (mounted read-only into the felt-llm container). Idempotent:
# skips files already present with the right SHA-256.
set -euo pipefail
DIR=${1:-/home/ai-models/gguf}
REPO=https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/main
mkdir -p "$DIR"
while read -r sha dst src; do
  [ -z "$sha" ] && continue
  if [ -s "$DIR/$dst" ] && echo "$sha  $DIR/$dst" | sha256sum -c --quiet 2>/dev/null; then
    echo "ok   $dst"; continue
  fi
  echo "get  $dst"
  curl -sfL -o "$DIR/$dst.part" "$REPO/$src"
  echo "$sha  $DIR/$dst.part" | sha256sum -c --quiet
  mv "$DIR/$dst.part" "$DIR/$dst"
done <<'LIST'
93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b gemma-4-12b-it-qat-q4_0.gguf gemma-4-12b-it-qat-q4_0.gguf
cb018338a7538a9814d994bfe54644c71eb7ed54e31eae2f721e45fd3c260da7 gemma-4-12b-mmproj.gguf mmproj-gemma-4-12b-it-qat-q4_0.gguf
LIST
