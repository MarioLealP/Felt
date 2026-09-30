r"""Auto-name VRoid part exports as Mario exports them (watcher).

Mario exports each piece from VRoid Studio as "undies base + that one piece"
into a category folder under OutfitBuilder (Tops, Bottoms, ...), with
whatever file name. This loop picks up every new .vrm once VRoid has
finished writing it, and for each:
  1. finds the piece (whatever the base lacks) and renders it - worn, and
     on its own - framed on the piece;
  2. asks felt-llm (Gemma 4 on the P104, vision via its mmproj - fully
     local) for a name; the category folder decides the type when it's a
     known one (Tops -> top, ...), otherwise the model picks;
  3. copies it to OutfitBuilderNamed/<same sub-folders>/<type>_<name>.vrm
     (+ _catalog/<that name>.png/.json: the render and what the model said);
  4. moves the original to OutfitBuilderUnnamed/<same sub-folders>/.
A file with "undies" or "base" in its name becomes the new base
(OutfitBuilderNamed/_base/; the previous base goes to OutfitBuilderUnnamed).

All three folders sit inside the Godot overlay's characters/ (E:\Felt\Model
is a junction there), so every folder gets a .gdignore - Godot must never
import these.

Run (WSL):  ~/.venvs/felt-outfits/bin/python name_parts.py [--once]
Log: OutfitBuilderNamed/_catalog/watch.log. Stop: kill the pid in
OutfitBuilderNamed/_catalog/watch.pid.

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
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

_GLU = Path.home() / ".venvs/felt-outfits/glu/x/usr/lib/x86_64-linux-gnu"
if _GLU.is_dir() and str(_GLU) not in os.environ.get("LD_LIBRARY_PATH", ""):
    env = dict(os.environ, LD_LIBRARY_PATH=f"{_GLU}:{os.environ.get('LD_LIBRARY_PATH', '')}", PYOPENGL_PLATFORM="egl")
    os.execve(sys.executable, [sys.executable, *sys.argv], env)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from combine import Combiner, Glb  # noqa: E402
from render_preview import render_views  # noqa: E402
from vrm_textures import write_glb  # noqa: E402

SRC = Path("/mnt/e/Felt/Model/OutfitBuilder")
NAMED = Path("/mnt/e/Felt/Model/OutfitBuilderNamed")
UNNAMED = Path("/mnt/e/Felt/Model/OutfitBuilderUnnamed")
BASE_DIR = NAMED / "_base"
CATALOG = NAMED / "_catalog"

TYPES = ["top", "bottom", "dress", "shoes", "socks", "acc"]
# Category folder name -> type (lower-cased, plural or not).
FOLDER_TYPES = {
    "top": "top", "tops": "top", "shirt": "top", "shirts": "top", "jacket": "top", "jackets": "top",
    "bottom": "bottom", "bottoms": "bottom", "pants": "bottom", "skirt": "bottom", "skirts": "bottom", "shorts": "bottom",
    "dress": "dress", "dresses": "dress", "onepiece": "dress", "onepieces": "dress",
    "shoe": "shoes", "shoes": "shoes", "footwear": "shoes",
    "sock": "socks", "socks": "socks", "legwear": "socks", "tights": "socks",
    "acc": "acc", "accessory": "acc", "accessories": "acc",
}
_POLL_S = 3
_STABLE_S = 6       # unchanged this long = VRoid finished writing
_RETRY_S = 60

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

_TYPE_HELP = """- top: upper body only (shirt, blouse, tank top, jacket, hoodie, sweater)
- bottom: from the waist down (skirt, shorts, trousers, jeans)
- dress: one piece covering torso and legs (dress, jumpsuit, overalls, full suit)
- shoes: footwear
- socks: socks, stockings, tights, leggings
- acc: anything else small (tie, gloves, wristbands, belt, hat, choker, ribbon, glasses)"""

_PROMPT = """The image shows ONE clothing item of a 3D anime character standing in a T-pose (arms stretched straight out sideways). Top row: the item as worn (front, back). Bottom row: the same item alone, body hidden (front, back) - it can look hollow there.

Facts from the 3D file:
{facts}

{type_line}

Reply in JSON: type; name = 1-3 lowercase words in snake_case, specific enough to tell it apart from similar items (e.g. pleated_skirt, denim_shorts, cropped_hoodie, sailor_top, thigh_high_socks, frilly_wristbands); description = one short sentence with shape, material look and colours; colors = its main colours."""


def log(msg: str) -> None:
    line = f"{datetime.datetime.now():%H:%M:%S} {msg}"
    print(line, flush=True)
    with open(CATALOG / "watch.log", "a") as f:
        f.write(line + "\n")


# -- understanding a part -----------------------------------------------
def analyze(base: Glb, base_skin, path: Path):
    """What the part adds over the base: garment points + facts for the prompt."""
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
    tex = Combiner._skin_texture(part)
    painted = np.abs(tex.astype(int) - base_skin.astype(int)).max(-1) > 2
    facts = []
    if pos:
        pts = np.concatenate(pos)
        facts.append(f"- VRoid slot(s): {', '.join(sorted(set(slots)))} (not always accurate: shorts can be a 'Onepiece', a dress a 'Tops')")
    else:
        tris = _painted_tris(part, painted)
        if tris is None:
            return None
        _, sp = part.skin_prim()
        pts = part.acc(sp["attributes"]["POSITION"])[np.unique(tris)]
        facts.append("- it has no 3D mesh of its own: it is painted onto the skin (typical of socks, stockings, tights)")
    # Robust bounds: a few stray vertices mustn't blow up the framing.
    lo, hi = np.percentile(pts, 1, axis=0), np.percentile(pts, 99, axis=0)
    pair = bool((pts[:, 0] > 0.12).mean() > 0.3 and (pts[:, 0] < -0.12).mean() > 0.3 and (np.abs(pts[:, 0]) < 0.06).mean() < 0.02)
    if pair:
        facts.append("- it is a left/right pair, one on each side of the body")
    where = _body_region(pts)
    if where:
        facts.append(f"- it sits {where}")
    facts.append(f"- it spans heights {lo[1]:.2f} m to {hi[1]:.2f} m on a 1.55 m tall body (feet 0, knees ~0.45, hips ~0.9, chest ~1.2, neck ~1.35)")
    chains = sum(1 for n in part.js["nodes"] if n.get("name") not in base_nodes and not n.get("name", "").endswith("_end"))
    if chains:
        facts.append(f"- it adds {chains} physics bones (swinging parts: skirt, sleeves, ribbons, frills)")
    if pair:  # frame one of the two
        side = pts[pts[:, 0] > 0]
        lo, hi = np.percentile(side, 1, axis=0), np.percentile(side, 99, axis=0)
    return {"lo": lo, "hi": hi, "facts": "\n".join(facts), "mesh": bool(pos), "slots": sorted(set(slots)),
            "painted": None if pos else painted}


def _body_region(pts) -> str | None:
    """Where on the (T-posed) body the item sits, for the prompt - arms
    stick straight out sideways, so |x| tells shoulder / forearm / wrist."""
    ax = np.abs(pts[:, 0])
    arm = (ax > 0.25) & (pts[:, 1] > 1.05) & (pts[:, 1] < 1.5)
    if arm.mean() > 0.8:
        x = np.median(ax[arm])
        return ("around the wrists" if x > 0.45 else "on the forearms" if x > 0.33 else "on the upper arms") + \
            " (the arms are stretched out sideways)"
    y0, y1 = np.percentile(pts[:, 1], [2, 98])
    if y1 < 0.2:
        return "on the feet"
    if y0 > 1.3:
        return "on the head or neck"
    return None


def _painted_tris(part: Glb, painted):
    """Skin triangles whose three vertices all sit on changed skin pixels."""
    _, sp = part.skin_prim()
    uv = part.acc(sp["attributes"]["TEXCOORD_0"])
    h, w = painted.shape
    px = np.clip((uv * [w, h]).astype(int), 0, [w - 1, h - 1])
    hit = painted[px[:, 1], px[:, 0]]
    tris = part.acc(sp["indices"]).reshape(-1, 3)
    tris = tris[hit[tris].all(1)]
    return tris if len(tris) else None


def isolate(path: Path, base: Glb, painted, out: Path):
    """A copy of the part with only the item left: base materials'
    primitives dropped (body, face, hair); for skin-painted legwear, only
    the painted skin triangles."""
    part = Glb(path)
    base_mats = {m["name"] for m in base.js["materials"]}
    _, skin = part.skin_prim()
    keep_skin = None
    if painted is not None:
        keep_skin = _painted_tris(part, painted).ravel().astype(np.uint32)
    for m in part.js["meshes"]:
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
    write_glb(out, part.js, bytes(part.bin))


def closeup(path: Path, iso: Path, lo, hi) -> Image.Image:
    """2x2: worn front|back over alone front|back, framed on the item (at
    least 24 cm so a small accessory keeps some context)."""
    c = (lo + hi) / 2
    half = np.maximum((hi - lo) / 2 * 1.15 + 0.02, 0.12)
    frame = (c - half, c + half)
    out = Image.new("RGB", (768, 1024))
    for row, f in enumerate((path, iso)):
        for col, v in enumerate(render_views(f, frame=frame, size=(384, 512))):
            out.paste(Image.fromarray(v[..., :3]), (col * 384, row * 512))
    d = ImageDraw.Draw(out)
    d.line([(0, 512), (768, 512)], fill=(120, 120, 120), width=2)
    d.line([(384, 0), (384, 1024)], fill=(120, 120, 120), width=2)
    return out


def ask_llm(img: Image.Image, facts: str, known_type: str | None) -> dict:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    if known_type:
        type_line = f"Its type is already known: {known_type}. Answer type = {known_type}."
    else:
        type_line = "Pick its type:\n" + _TYPE_HELP
    payload = {
        "model": "felt",
        "temperature": 0.2,
        "max_tokens": 200,
        "response_format": {"type": "json_schema", "json_schema": {"schema": _SCHEMA}},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}},
                {"type": "text", "text": _PROMPT.format(facts=facts, type_line=type_line)},
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


def free_path(p: Path) -> Path:
    n, out = 2, p
    while out.exists():
        out = p.with_name(f"{p.stem}_{n}{p.suffix}")
        n += 1
    return out


# -- the loop -----------------------------------------------------------
def ensure_dirs():
    for d in (NAMED, UNNAMED, BASE_DIR, CATALOG):
        d.mkdir(parents=True, exist_ok=True)
    for d in (NAMED, UNNAMED):
        (d / ".gdignore").touch()
    # OutfitBuilder itself stays folders-only (Mario's call): each category
    # folder carries its own .gdignore instead.
    for d in [SRC, *SRC.rglob("*")]:
        if d.is_dir() and d != SRC and not (d / ".gdignore").exists():
            (d / ".gdignore").touch()


def current_base():
    bases = sorted(BASE_DIR.glob("*.vrm"), key=lambda p: p.stat().st_mtime)
    return bases[-1] if bases else None


def process(path: Path, base_path: Path) -> None:
    rel = path.parent.relative_to(SRC)
    base = Glb(base_path)
    info = analyze(base, Combiner._skin_texture(base), path)
    if info is None:
        log(f"  {path.relative_to(SRC)}: identical to the base - moved to Unnamed, not named")
        (UNNAMED / rel).mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(free_path(UNNAMED / rel / path.name)))
        return
    iso = CATALOG / "_isolated.vrm"
    isolate(path, base, info["painted"], iso)
    img = closeup(path, iso, info["lo"], info["hi"])
    iso.unlink()
    known = next((FOLDER_TYPES[p.lower()] for p in reversed(rel.parts) if p.lower() in FOLDER_TYPES), None)
    if not info["mesh"]:
        known = "socks"  # skin paint is always legwear
    ans = ask_llm(img, info["facts"], known)
    kind = known or (ans["type"] if ans["type"] in TYPES else "acc")
    (NAMED / rel).mkdir(parents=True, exist_ok=True)
    target = free_path(NAMED / rel / f"{kind}_{slug(ans['name'])}.vrm")
    shutil.copy2(path, target)
    img.save(CATALOG / f"{target.stem}.png")
    (CATALOG / f"{target.stem}.json").write_text(json.dumps({
        "file": str(target.relative_to(NAMED)), "was": str(path.relative_to(SRC)), "type": kind,
        "name": slug(ans["name"]), "description": ans["description"], "colors": ans["colors"],
        "slots": info["slots"], "base": base_path.name,
    }, indent=2) + "\n")
    (UNNAMED / rel).mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(free_path(UNNAMED / rel / path.name)))
    log(f"  {path.relative_to(SRC)} -> {target.relative_to(NAMED)}  ({ans['description']})")


def take_base(path: Path) -> None:
    for old in BASE_DIR.glob("*.vrm"):
        shutil.move(str(old), str(free_path(UNNAMED / old.name)))
    shutil.copy2(path, BASE_DIR / path.name)
    rel = path.parent.relative_to(SRC)
    (UNNAMED / rel).mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(free_path(UNNAMED / rel / path.name)))
    log(f"  new base: {path.relative_to(SRC)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="process what's there now, then exit")
    args = ap.parse_args()
    ensure_dirs()
    (CATALOG / "watch.pid").write_text(str(os.getpid()))
    log(f"watching {SRC} (pid {os.getpid()})")
    seen: dict[Path, tuple] = {}      # path -> (size, mtime, first seen unchanged at)
    failed: dict[Path, float] = {}    # path -> retry after
    while True:
        ensure_dirs()
        now = time.monotonic()
        ready = []
        for p in sorted(SRC.rglob("*.vrm")):
            st = p.stat()
            sig = (st.st_size, st.st_mtime)
            prev = seen.get(p)
            if prev is None or prev[:2] != sig:
                seen[p] = (*sig, now)
            elif now - prev[2] >= _STABLE_S and failed.get(p, 0) <= now:
                ready.append(p)
        for p in ready:
            try:
                if re.search(r"undies|base", p.stem, re.I):
                    take_base(p)
                else:
                    base = current_base()
                    if base is None:
                        log(f"  waiting: no base yet - export the underwear-only model (file name with 'undies' or 'base') - {p.name} on hold")
                        failed[p] = now + _RETRY_S
                        continue
                    process(p, base)
                seen.pop(p, None)
                failed.pop(p, None)
            except Exception as e:  # noqa: BLE001 - keep watching; retry this one later
                log(f"  ! {p.relative_to(SRC)}: {e!r} - retry in {_RETRY_S}s")
                traceback.print_exc()
                failed[p] = time.monotonic() + _RETRY_S
        if args.once and all(p in failed for p in SRC.rglob("*.vrm")):
            break
        time.sleep(_POLL_S)


if __name__ == "__main__":
    main()
