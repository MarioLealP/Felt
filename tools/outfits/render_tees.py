"""WP-33: render Felt wearing every generated tee, as a review batch.

The overlay applies a tee by swapping the albedo of her shirt material
(N00_004_01_Tops_01_CLOTH, wardrobe.apply_tee). This does the same swap
offline on felt.vrm (base colour + MToon shade texture), renders the torso
front-on, and writes the review batch E:/Felt/review/wp33-tees/: keep = it
goes into her daily rotation (tees_approved.json, written from approved/).

Run (WSL): ~/.venvs/felt-outfits/bin/python render_tees.py
"""

import json
import os
import sys
from pathlib import Path

_GLU = Path.home() / ".venvs/felt-outfits/glu/x/usr/lib/x86_64-linux-gnu"
if _GLU.is_dir() and str(_GLU) not in os.environ.get("LD_LIBRARY_PATH", ""):
    env = dict(os.environ, LD_LIBRARY_PATH=f"{_GLU}:{os.environ.get('LD_LIBRARY_PATH', '')}", PYOPENGL_PLATFORM="egl")
    os.execve(sys.executable, [sys.executable, *sys.argv], env)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from combine import Glb  # noqa: E402
from render_preview import render_views  # noqa: E402
from vrm_textures import write_glb  # noqa: E402

BASE = Path("/mnt/e/Felt/felt-character-assets/felt-godot-overlay/characters/felt.vrm")
TEES = Path("/mnt/e/Felt/Assets/tees")
BATCH = Path("/mnt/e/Felt/review/wp33-tees")
TMP = Path.home() / ".cache/felt-outfits/tmp"
MATERIAL = "N00_004_01_Tops_01_CLOTH"
# Her torso, head to hips (world metres, bind pose).
FRAME = (np.array([-0.32, 0.78, -0.3]), np.array([0.32, 1.52, 0.3]))


def with_tee(base: Glb, png: Path, out: Path) -> None:
    g = Glb(BASE)  # fresh copy per tee
    mat = next(m for m in g.js["materials"] if MATERIAL in m["name"])
    g.js["images"].append({"name": png.stem, "mimeType": "image/png", "bufferView": g.add_view(png.read_bytes())})
    src = g.js["textures"][mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]]
    g.js["textures"].append({**src, "source": len(g.js["images"]) - 1})
    tex = len(g.js["textures"]) - 1
    mat["pbrMetallicRoughness"]["baseColorTexture"]["index"] = tex
    shade = mat.get("extensions", {}).get("VRMC_materials_mtoon", {}).get("shadeMultiplyTexture")
    if shade:
        shade["index"] = tex
    g.js["buffers"] = [{"byteLength": len(g.bin)}]
    write_glb(out, g.js, bytes(g.bin))


def main():
    pngs = sorted(TEES.glob("*.png"))
    (BATCH / "pending").mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    (BATCH / "batch.json").write_text(json.dumps({
        "title": f"WP-33 daily tees ({len(pngs)})",
        "dest": None,
        "hint": "Keep = it goes into her daily tee rotation. Claude writes tees_approved.json from your keeps - just close the window.",
    }, indent=1))
    base = Glb(BASE)
    for png in pngs:
        out = BATCH / "pending" / f"{png.stem}.png"
        if out.exists() or (BATCH / "approved" / out.name).exists() or (BATCH / "rejected" / out.name).exists():
            continue
        vrm = TMP / "tee.vrm"
        with_tee(base, png, vrm)
        front, back = render_views(str(vrm), frame=FRAME, size=(480, 560))
        img = Image.new("RGB", (960, 560), (236, 236, 240))
        img.paste(Image.fromarray(front[..., :3]), (0, 0))
        img.paste(Image.fromarray(back[..., :3]), (480, 0))
        img.save(out)
        name = png.stem.replace("_txt_", " - text: ").replace("_", " ")
        (BATCH / "pending" / f"{png.stem}.json").write_text(json.dumps({"title": name, "tee": png.stem}, indent=1))
        print("rendered", png.stem, flush=True)
    vrm.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
