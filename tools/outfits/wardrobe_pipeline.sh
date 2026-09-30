#!/usr/bin/env bash
# The whole wardrobe run, unattended (WP-27, 2026-09-30): wait for Felt's
# designs + tagging, then sets -> renders -> Felt's pass -> review batch ->
# open the review window for Mario. Each step is resumable; rerun to continue.
set -euo pipefail
cd "$(dirname "$0")"
PY=~/.venvs/felt-outfits/bin/python
CAT=/mnt/e/Felt/Model/OutfitBuilderNamed/_catalog
log() { echo "$(date +%H:%M:%S) $*"; }

log "waiting for designs + tags"
while pgrep -f "python design_styles.py|python tag_pieces.py" >/dev/null; do sleep 30; done
# Anything that errored gets one more go.
$PY design_styles.py
$PY tag_pieces.py
[ -f /mnt/e/Felt/review/wardrobe-sets/sets.json ] || { log "sets"; $PY make_sets.py --n 200; }
log "renders";     $PY render_sets.py
log "felt pass";   $PY felt_pass.py
log "review batch"; $PY build_review.py
log "opening review window"
powershell.exe -NoProfile -Command 'Start-Process python -ArgumentList "E:\Felt\tools\outfits\review\server.py","E:\Felt\review\wardrobe" -WindowStyle Hidden'
log "done"
