"""Tag every wardrobe piece for outfit matching (WP-27, 2026-09-30).

Text-only felt-llm call per piece (its catalog description), no persona -
this is classification, not taste. Plus measurements from the 3D file:
where the piece starts and ends on her body, and its dominant colour.

Output: OutfitBuilderNamed/_catalog/tags.json
    {"Tops/top_x.vrm": {"styles": [...], "formality": 1-5, "warmth": "light|medium|warm",
                         "built_in": [...], "y_lo": .., "y_hi": .., "color": "#rrggbb", "chromatic": bool}}
Resumable.  Run (WSL): ~/.venvs/felt-outfits/bin/python tag_pieces.py
"""

import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import felt_llm  # noqa: E402
from combine import Combiner, Glb  # noqa: E402
from patterns import classify  # noqa: E402

NAMED = Path("/mnt/e/Felt/Model/OutfitBuilderNamed")
CATALOG = NAMED / "_catalog"
OUT = CATALOG / "tags.json"

STYLES = ["casual", "school", "gothic", "lolita", "techwear", "formal", "sporty", "cute", "streetwear", "cozy", "elegant", "punk"]
SCHEMA = {
    "type": "object",
    "properties": {
        "styles": {"type": "array", "minItems": 1, "maxItems": 3, "items": {"type": "string", "enum": STYLES}},
        "formality": {"type": "integer", "minimum": 1, "maximum": 5},
        "warmth": {"type": "string", "enum": ["light", "medium", "warm"]},
        "built_in": {"type": "array", "items": {"type": "string", "enum": ["tie", "bow", "ribbon", "choker", "necklace", "belt", "none"]}},
    },
    "required": ["styles", "formality", "warmth", "built_in"],
}
PROMPT = """Classify this clothing item of an anime-style 3D character for outfit matching.
Item: {name} ({kind}). Description: {desc}
- styles: 1 to 3 of {styles}
- formality: 1 (lounge) to 5 (gala)
- warmth: light, medium or warm
- built_in: neck/waist accessories that are part of this item itself (tie, bow, ribbon, choker, necklace, belt), or ["none"]
Answer only with JSON."""


def measure(base: Glb, base_skin, path: Path) -> dict:
    """Height range on her body + dominant colour of the piece's fabric."""
    g = Glb(path)
    base_mats = {m["name"] for m in base.js["materials"]}
    pts, cols = [], []
    for m in g.js["meshes"]:
        for p in m["primitives"]:
            mat = g.js["materials"][p["material"]]
            if mat["name"] in base_mats:
                continue
            pts.append(g.acc(p["attributes"]["POSITION"])[np.unique(g.acc(p["indices"]))])
            bc = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
            if bc:
                img = np.asarray(Image.open(io.BytesIO(g.image_bytes(g.js["textures"][bc["index"]]["source"]))).convert("RGBA"))
                cols.append(img)
    if not pts:  # skin-painted: the painted pixels
        tex = Combiner._skin_texture(g)
        mask = np.abs(tex.astype(int) - base_skin.astype(int)).max(-1) > 2
        cols = [np.where(mask[..., None], tex, 0).astype(np.uint8)]
        y_lo = y_hi = None
    else:
        allp = np.concatenate(pts)
        y_lo, y_hi = float(np.percentile(allp[:, 1], 1)), float(np.percentile(allp[:, 1], 99))
    rgb, chroma = _dominant(cols)
    return {"y_lo": y_lo, "y_hi": y_hi, "color": rgb, "chromatic": chroma}


def _dominant(imgs):
    px = []
    for img in imgs:
        c = classify(img)
        sel = c["colour"] if c["colour"].sum() > c["achro"].sum() * 0.5 else c["achro"]
        px.append(img[..., :3][sel])
    px = np.concatenate(px) if px else np.zeros((1, 3))
    if not len(px):
        return "#ffffff", False
    med = np.median(px.reshape(-1, 3), 0)
    mx, mn = med.max(), med.min()
    return "#%02x%02x%02x" % tuple(int(v) for v in med), bool(mx > 0 and (mx - mn) / mx > 0.22)


def main():
    tags = json.loads(OUT.read_text()) if OUT.exists() else {}
    base = Glb(next((NAMED / "_base").glob("*.vrm")))
    base_skin = Combiner._skin_texture(base)
    for p in sorted(NAMED.rglob("*.vrm")):
        rel = str(p.relative_to(NAMED))
        if rel.startswith("_") or rel in tags:
            continue
        meta = json.loads((CATALOG / f"{p.stem}.json").read_text())
        ans = felt_llm.ask(PROMPT.format(name=meta["name"], kind=meta["type"], desc=meta["description"], styles=", ".join(STYLES)),
                           schema=SCHEMA, persona_on=False, temperature=0.2, max_tokens=150)
        ans["built_in"] = [b for b in ans["built_in"] if b != "none"]
        tags[rel] = {**ans, **measure(base, base_skin, p), "type": meta["type"]}
        OUT.write_text(json.dumps(tags, indent=1))
        print(f"  {rel}: {tags[rel]}", flush=True)


if __name__ == "__main__":
    main()
