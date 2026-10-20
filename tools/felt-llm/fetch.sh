#!/bin/bash
# felt-llm model files into /home/ai-models/gguf on the server (mounted
# read-only into the felt-llm container). Idempotent: skips files already
# present with the right SHA-256.
# - Ternary Bonsai 2 27B PQ2_0 + its vision projector (Felt's brain since
#   2026-10-20, model spike; needs Prism ML's llama.cpp fork - infra
#   projects/felt-llm/Dockerfile)
# - Gemma 4 12B QAT q4_0 + projector (WP-36 rev 2): kept as the rollback
set -euo pipefail
DIR=${1:-/home/ai-models/gguf}
HF=https://huggingface.co
mkdir -p "$DIR"
while read -r sha dst src; do  # src = <repo>/<file> on Hugging Face
  [ -z "$sha" ] && continue
  if [ -s "$DIR/$dst" ] && echo "$sha  $DIR/$dst" | sha256sum -c --quiet 2>/dev/null; then
    echo "ok   $dst"; continue
  fi
  echo "get  $dst"
  repo=${src%/*}; file=${src##*/}
  curl -sfL -o "$DIR/$dst.part" "$HF/$repo/resolve/main/$file"
  echo "$sha  $DIR/$dst.part" | sha256sum -c --quiet
  mv "$DIR/$dst.part" "$DIR/$dst"
done <<'LIST'
3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1 Ternary-Bonsai-2-27B-PQ2_0.gguf prism-ml/Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PQ2_0.gguf
6807ede61d570bb86ba34b756a0fa109edc33668604de867c6ea6d8f1d631903 Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf prism-ml/Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf
93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b gemma-4-12b-it-qat-q4_0.gguf google/gemma-4-12B-it-qat-q4_0-gguf/gemma-4-12b-it-qat-q4_0.gguf
cb018338a7538a9814d994bfe54644c71eb7ed54e31eae2f721e45fd3c260da7 gemma-4-12b-mmproj.gguf google/gemma-4-12B-it-qat-q4_0-gguf/mmproj-gemma-4-12b-it-qat-q4_0.gguf
LIST
