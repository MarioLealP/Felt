"""WP-19 Part 4, second half: reads the decisions.json downloaded from
curate.html and copies every "keep" file from
E:\\Felt\\Sounds\\candidates\\<kind>\\ to E:\\Felt\\Sounds\\<kind>\\ - the
real, final location sounds.py's pick_sound_path/pick_filler_path read
from. Rejected/undecided candidates are left where they are (not
deleted - Mario can always revisit a rejected take later without
needing to regenerate it).

Usage: uv run python apply_keepers.py <path-to-decisions.json>
(the file Firefox's downloads folder gets when you click "Download
decisions.json" on curate.html)
"""

import json
import shutil
import sys
from pathlib import Path

CANDIDATES_DIR = Path(r"E:\Felt\Sounds\candidates")
SOUNDS_DIR = Path(r"E:\Felt\Sounds")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: uv run python apply_keepers.py <path-to-decisions.json>")
        sys.exit(1)

    decisions_path = Path(sys.argv[1])
    decisions: dict[str, str] = json.loads(decisions_path.read_text(encoding="utf-8"))

    kept = [key for key, choice in decisions.items() if choice == "keep"]
    if not kept:
        print("No 'keep' decisions in that file - nothing to move.")
        return

    moved = 0
    for key in kept:
        kind, _, fname = key.partition("/")
        src = CANDIDATES_DIR / kind / fname
        if not src.is_file():
            print(f"  SKIP (not found): {src}")
            continue
        dest_dir = SOUNDS_DIR / kind
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / fname
        shutil.copy2(src, dest)
        print(f"  {src} -> {dest}")
        moved += 1

    print(f"Copied {moved}/{len(kept)} keeper(s) into {SOUNDS_DIR}.")


if __name__ == "__main__":
    main()
