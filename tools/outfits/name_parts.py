"""Auto-name VRoid part exports for the outfit builder (combine.py).

Mario exports each piece as "undies base + that one piece" from VRoid
Studio with whatever file name; this finds the piece (what the base lacks),
renders a front/back close-up of it, asks felt-llm (Gemma 4 on the P104,
vision via its mmproj - fully local) what it is, and renames the file to
<type>_<name>.vrm (type: top, bottom, dress, shoes, socks, acc).

Next to the parts it keeps _catalog/<new name>.json (description, colours,
original file name) + .png (the close-up it judged), and _catalog/renames.log
(old -> new, to undo by hand).

Run (WSL, the felt-outfits venv):
    ~/.venvs/felt-outfits/bin/python name_parts.py [DIR] [--base FILE] [--dry-run]
DIR defaults to E:/Felt/Model/OutfitBuilder. Files already named <type>_*
and the base (default: the file with "undies" or "base" in its name) are
skipped, so it's safe to re-run after every export session.

Rendering needs pyrender in WSL: pyopengl>=3.1.9, networkx>=3, and GLU +
libOpenGL, which aren't installed system-wide - their .debs are unpacked
under ~/.venvs/felt-outfits/glu (apt-get download libglu1-mesa libopengl0;
dpkg -x). This script re-execs itself with LD_LIBRARY_PATH pointing there.
"""

import argparse
import base64
import datetime
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_GLU = Path.home() / ".venvs/felt-outfits/glu/x/usr/lib/x86_64-linux-gnu"
if _GLU.is_dir() and str(_GLU) not in os.environ.get("LD_LIBRARY_PATH", ""):
    env = dict(os.environ, LD_LIBRARY_PATH=f"{_GLU}:{os.environ.get('LD_LIBRARY_PATH', '')}", PYOPENGL_PLATFORM="egl")
    os.execve(sys.executable, [sys.executable, *sys.argv], env)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from combine import Combiner, Glb  # noqa: E402
from render_preview import render_views  # noqa: E402

TYPES = ["top", "bottom", "dress", "shoes", "socks", "acc"]
_TYPED = re.compile(rf"^({'|'.join(TYPES)})_", re.I)
DEFAULT_DIR = Path("/mnt/e/Felt/Model/OutfitBuilder/Tops")

_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": TYPES},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "colors": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["type", "name", "description", "colors"],
}

_PROMPT = """These are front (left) and back (right) views of ONE clothing item from a 3D anime character, shown on its own (the character's body is hidden, so the item may look hollow).

Facts from the 3D file:
{facts}

Pick its type:
- top: upper body only (shirt, blouse, tank top, jacket, hoodie, sweater)
- bottom: from the waist down (skirt, shorts, trousers, jeans)
- dress: one piece covering torso and legs (dress, jumpsuit, overalls, full suit)
- shoes: footwear
- socks: socks, stockings, tights, leggings
- acc: anything else small (tie, gloves, wristbands, belt, hat, choker, ribbon, glasses)

Reply in JSON: type; name = 1-3 lowercase words in snake_case, specific enough to tell it apart from similar items (e.g. pleated_skirt, denim_shorts, sailor_top, thigh_high_socks, frilly_wristbands); description = one short sentence with shape, material look and colours; colors = its main colours."""


def analyze(base: Glb, base_skin, path: Path):
    """What the part adds over the base: garment bounds + facts for the prompt."""
    part = Glb(path)
    base_mats = {m["name"] for m in base.js["materials"]}
    base_nodes = {n.get("name") for n in base.js["nodes"]}
    pos, slots = [], []
    for m in part.js["meshes"]:
        for p in m["primitives"]:
            name = part.js["materials"][p["material"]]["name"]
            if name in base_mats:
                continue
            slots.append(re.sub(r"^N00_\d+_\d+_|_\d+_CLOTH.*$| \(Instance\)$", "", name))
            used = np.unique(part.acc(p["indices"]))
            pos.append(part.acc(p["attributes"]["POSITION"])[used])
    new_nodes = [n.get("name") for n in part.js["nodes"] if n.get("name") not in base_nodes]
    tex = Combiner._skin_texture(part)
    painted = np.abs(tex.astype(int) - base_skin.astype(int)).max(-1) > 2
    facts = []
    if pos:
        pts = np.concatenate(pos)
        facts.append(f"- VRoid slot(s): {', '.join(sorted(set(slots)))} (not always accurate: shorts can be a 'Onepiece', a dress a 'Tops')")
    else:
        # Only skin paint (legwear): bounds = skin vertices whose UV lands on a painted pixel.
        _, sp = part.skin_prim()
        spos, suv = part.acc(sp["attributes"]["POSITION"]), part.acc(sp["attributes"]["TEXCOORD_0"])
        h, w = painted.shape
        px = np.clip((suv * [w, h]).astype(int), 0, [w - 1, h - 1])
        hit = painted[px[:, 1], px[:, 0]]
        if not hit.any():
            return None
        pts = spos[hit]
        facts.append("- it has no 3D mesh of its own: it is painted onto the skin (typical of socks, stockings, tights)")
    lo, hi = pts.min(0), pts.max(0)
    pair = bool((pts[:, 0] > 0.12).any() and (pts[:, 0] < -0.12).any() and not (np.abs(pts[:, 0]) < 0.06).any())
    if pair:
        facts.append("- it is a left/right pair, one on each side of the body (only one side is shown)")
    facts.append(f"- it spans heights {lo[1]:.2f} m to {hi[1]:.2f} m on a 1.55 m tall body (feet 0, knees ~0.45, hips ~0.9, chest ~1.2, neck ~1.35)")
    chains = sum(1 for n in new_nodes if not n.endswith("_end"))
    if chains:
        facts.append(f"- it adds {chains} physics bones (swinging parts: skirt, sleeves, ribbons, frills)")
    return {"lo": lo, "hi": hi, "facts": "\n".join(facts), "mesh": bool(pos), "slots": sorted(set(slots)),
            "pair": pair, "painted": None if pos else painted}


def isolate(path: Path, base: Glb, painted, out: Path):
    """A copy of the part with only the item left: base materials' primitives
    dropped (body, face, hair); for skin-painted legwear, only the skin
    triangles that carry the paint."""
    part = Glb(path)
    base_mats = {m["name"] for m in base.js["materials"]}
    _, skin = part.skin_prim()
    keep_skin = None
    if painted is not None:
        uv = part.acc(skin["attributes"]["TEXCOORD_0"])
        h, w = painted.shape
        px = np.clip((uv * [w, h]).astype(int), 0, [w - 1, h - 1])
        hit = painted[px[:, 1], px[:, 0]]
        tris = part.acc(skin["indices"]).reshape(-1, 3)
        keep_skin = tris[hit[tris].any(1)].ravel().astype(np.uint32)
    for mi, m in enumerate(part.js["meshes"]):
        prims = []
        for p in m["primitives"]:
            if p is skin and keep_skin is not None:
                p["indices"] = part.add_acc(keep_skin, "SCALAR", 34963)
                prims.append(p)
            elif part.js["materials"][p["material"]]["name"] not in base_mats:
                prims.append(p)
        m["primitives"] = prims
    for n in part.js["nodes"]:
        if "mesh" in n and not part.js["meshes"][n["mesh"]]["primitives"]:
            del n["mesh"]
            n.pop("skin", None)
    part.js["buffers"] = [{"byteLength": len(part.bin)}]
    from vrm_textures import write_glb
    write_glb(out, part.js, bytes(part.bin))


def closeup(path: Path, lo, hi, pair: bool) -> Image.Image:
    """Front|back close-up of the isolated item, framed on it (at least
    20 cm, so a tiny accessory isn't blown up past recognition). A left/right
    pair is framed on one side only."""
    if pair:
        lo = np.array([max(lo[0], 0.0), lo[1], lo[2]])
    c = (lo + hi) / 2
    half = np.maximum((hi - lo) / 2 + 0.03, 0.10)
    views = render_views(path, frame=(c - half, c + half), size=(384, 512))
    out = Image.new("RGB", (768, 512))
    for i, v in enumerate(views):
        out.paste(Image.fromarray(v[..., :3]), (i * 384, 0))
    return out


def ask_llm(img: Image.Image, facts: str) -> dict:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    payload = {
        "model": "felt",
        "temperature": 0.2,
        "max_tokens": 200,
        "response_format": {"type": "json_schema", "json_schema": {"schema": _SCHEMA}},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}},
                {"type": "text", "text": _PROMPT.format(facts=facts)},
            ],
        }],
    }
    # felt-llm only listens on the server's docker network; reach it via SSH.
    cmd = ("IP=$(docker inspect -f '{{.NetworkSettings.Networks.edge.IPAddress}}' felt-llm) && "
           "curl -sS --max-time 180 -H 'Content-Type: application/json' -d @- http://$IP:8080/v1/chat/completions")
    res = subprocess.run(["ssh", "clockmost-claude", cmd], input=json.dumps(payload).encode(), capture_output=True, check=True, timeout=240)
    reply = json.loads(res.stdout)
    return json.loads(reply["choices"][0]["message"]["content"])


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return "_".join(s.split("_")[:4]) or "item"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--base", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    d = args.dir
    base_path = args.base or next((p for p in sorted(d.glob("*.vrm")) if re.search(r"undies|base", p.stem, re.I)), None)
    if base_path is None:
        sys.exit("no base: pass --base, or name the underwear export with 'undies' or 'base'")
    base = Glb(base_path)
    base_skin = Combiner._skin_texture(base)
    catalog = d / "_catalog"
    catalog.mkdir(exist_ok=True)
    todo = [p for p in sorted(d.glob("*.vrm")) if p != base_path and not _TYPED.match(p.stem)]
    print(f"base: {base_path.name}; {len(todo)} to name")
    for path in todo:
        info = analyze(base, base_skin, path)
        if info is None:
            print(f"  ? {path.name}: identical to the base - skipped")
            continue
        tmp = catalog / "_isolated.vrm"
        isolate(path, base, info["painted"], tmp)
        img = closeup(tmp, info["lo"], info["hi"], info["pair"])
        tmp.unlink()
        ans = ask_llm(img, info["facts"])
        kind = ans["type"] if ans["type"] in TYPES else "acc"
        if not info["mesh"]:
            kind = "socks"  # skin paint is always legwear, whatever the model says
        target = d / f"{kind}_{slug(ans['name'])}.vrm"
        n = 2
        while target.exists():
            target = d / f"{kind}_{slug(ans['name'])}_{n}.vrm"
            n += 1
        print(f"  {path.name} -> {target.name}  ({ans['description']})")
        if args.dry_run:
            img.save(catalog / f"_dry_{path.stem}.png")
            continue
        path.rename(target)
        img.save(catalog / f"{target.stem}.png")
        (catalog / f"{target.stem}.json").write_text(json.dumps({
            "file": target.name, "was": path.name, "type": kind, "name": slug(ans["name"]),
            "description": ans["description"], "colors": ans["colors"], "slots": info["slots"],
        }, indent=2) + "\n")
        with open(catalog / "renames.log", "a") as log:
            log.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M}\t{path.name}\t{target.name}\n")


if __name__ == "__main__":
    main()
