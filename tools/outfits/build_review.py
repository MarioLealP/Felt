"""Turn Felt's wardrobe picks into a review batch for Mario (WP-27).

Builds each picked set as a VRM (combine.py, her styles applied) into
E:/Felt/review/wardrobe/pending/<id>.vrm with a sidecar carrying her
rating, comment and occasion and the pieces/looks. Finalize moves the
approved ones to the overlay's characters/variants/wardrobe/ (gitignored:
derived from paid assets).

Run (WSL): ~/.venvs/felt-outfits/bin/python build_review.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_sets import build  # noqa: E402

SETS = Path("/mnt/e/Felt/review/wardrobe-sets")
BATCH = Path("/mnt/e/Felt/review/wardrobe")


def main():
    sets = {s["id"]: s for s in json.loads((SETS / "sets.json").read_text())}
    felt = json.loads((SETS / "felt_pass.json").read_text())
    picks = felt["wardrobe"]["picks"]
    (BATCH / "pending").mkdir(parents=True, exist_ok=True)
    (BATCH / "batch.json").write_text(json.dumps({
        "title": f"Felt's wardrobe picks ({len(picks)} of {len(sets)})",
        "dest": r"E:\Felt\felt-character-assets\felt-godot-overlay\characters\variants\wardrobe",
        "hint": f"Felt: {felt['wardrobe']['why']}",
    }, indent=1))
    for sid in picks:
        s, r = sets[sid], felt["sets"][sid]
        vrm = BATCH / "pending" / f"{sid}.vrm"
        if not vrm.exists():
            build(s, vrm)
        pieces = [Path(p["rel"]).stem + ("" if p["look"] == "original" else f" [{p['look']}]") for p in s["pieces"]]
        (BATCH / "pending" / f"{sid}.json").write_text(json.dumps({
            "title": f"{sid} - Felt {r['rating']}/10",
            "felt": r["comment"],
            "occasion": r["occasion"],
            "pieces": pieces,
            "styles": s["styles"],
        }, indent=1))
        print(f"built {sid}", flush=True)


if __name__ == "__main__":
    main()
