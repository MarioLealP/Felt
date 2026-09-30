"""Render every set in sets.json: build it (combine.py, Felt's styles
applied) and save a front|back T-pose picture. Resumable.

Output: E:/Felt/review/wardrobe-sets/renders/<id>.png
Run (WSL): ~/.venvs/felt-outfits/bin/python render_sets.py
"""

import json
import os
import sys
import time
from pathlib import Path

_GLU = Path.home() / ".venvs/felt-outfits/glu/x/usr/lib/x86_64-linux-gnu"
if _GLU.is_dir() and str(_GLU) not in os.environ.get("LD_LIBRARY_PATH", ""):
    env = dict(os.environ, LD_LIBRARY_PATH=f"{_GLU}:{os.environ.get('LD_LIBRARY_PATH', '')}", PYOPENGL_PLATFORM="egl")
    os.execve(sys.executable, [sys.executable, *sys.argv], env)

import contextlib  # noqa: E402
import io  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from combine import Combiner  # noqa: E402
from render_preview import render_views  # noqa: E402

NAMED = Path("/mnt/e/Felt/Model/OutfitBuilderNamed")
SETS = Path("/mnt/e/Felt/review/wardrobe-sets")
TMP = Path.home() / ".cache/felt-outfits/tmp"
# Her body, forearms cropped: outfits read better big than with full T-pose arms.
FRAME = (np.array([-0.42, -0.02, -0.3]), np.array([0.42, 1.62, 0.3]))


def build(s: dict, out: Path) -> None:
    base = next((NAMED / "_base").glob("*.vrm"))
    c = Combiner(str(base))
    with contextlib.redirect_stdout(io.StringIO()):
        for p in s["pieces"]:
            c.add_part(str(NAMED / p["rel"]), Path(p["rel"]).stem, p["spec"])
        c.write(str(out), s["id"])


def main():
    sets = json.loads((SETS / "sets.json").read_text())
    (SETS / "renders").mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    for s in sets:
        png = SETS / "renders" / f"{s['id']}.png"
        if png.exists():
            continue
        t = time.time()
        vrm = TMP / f"{s['id']}.vrm"
        build(s, vrm)
        front, back = render_views(str(vrm), frame=FRAME, size=(380, 720))
        vrm.unlink()
        img = Image.new("RGB", (760, 748), (236, 236, 240))
        img.paste(Image.fromarray(front[..., :3]), (0, 28))
        img.paste(Image.fromarray(back[..., :3]), (380, 28))
        ImageDraw.Draw(img).text((8, 8), f"{s['id']}  front | back", fill=(40, 40, 40))
        img.save(png)
        print(f"{s['id']} {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
