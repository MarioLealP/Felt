"""Felt designs looks for her wardrobe pieces (WP-27, 2026-09-30).

For every named piece in OutfitBuilderNamed she gets its render (worn /
alone, from the namer's catalog) and designs a few different looks -
pattern, colours, scale, and why, in her own words - plus her take on the
piece as exported. Specs only: patterns.apply_style renders them when an
outfit is built (combine.py), per the garment's own fabric.

Output: OutfitBuilderNamed/_catalog/styles.json
    {"Tops/top_x.vrm": {"original": "...", "designs": [{name, pattern, colors, scale, why}, ...]}}
Resumable: pieces already in styles.json are skipped.

Run (WSL):  ~/.venvs/felt-outfits/bin/python design_styles.py [--only SUBSTR]
"""

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import felt_llm  # noqa: E402
from patterns import PATTERNS, SCALES  # noqa: E402

NAMED = Path("/mnt/e/Felt/Model/OutfitBuilderNamed")
CATALOG = NAMED / "_catalog"
OUT = CATALOG / "styles.json"
N_DESIGNS = 3

SCHEMA = {
    "type": "object",
    "properties": {
        "original": {"type": "string"},
        "designs": {
            "type": "array", "minItems": N_DESIGNS, "maxItems": N_DESIGNS,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "pattern": {"type": "string", "enum": PATTERNS},
                    "colors": {"type": "array", "minItems": 1, "maxItems": 3,
                               "items": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}},
                    "scale": {"type": "string", "enum": list(SCALES)},
                    "why": {"type": "string"},
                },
                "required": ["name", "pattern", "colors", "scale", "why"],
            },
        },
    },
    "required": ["original", "designs"],
}

PROMPT = """Mario is building you a wardrobe: outfits you'll actually wear on his desktop. This piece is one of them: {desc} (a {kind}). The picture shows it on you (top row, front and back) and on its own (bottom row).

Design {n} different looks for it that YOU would want to wear - it's your wardrobe, go with your own taste. Make the {n} clearly different from each other (different colours and/or patterns). For each look:
- name: 2 to 4 words
- pattern: one of {patterns}. Plain white parts take the pattern; already-coloured parts just shift to your colours; see-through parts only take the first colour.
- colors: 1 to 3 hex colours, main colour first (for patterns: the second colour is the pattern's, the third an accent)
- scale: small, medium or large (pattern size)
- why: one short sentence in your own voice about why you'd wear it

Also "original": one short sentence, in your voice, on what you think of the piece as it is now.

{avoid}This time answer only with the JSON; it is not spoken."""


def _avoid(styles: dict) -> str:
    """Her recent looks, so she doesn't keep reaching for the same three
    themes (early runs: every piece got a "Midnight ...", a teal "Cyber Punk"
    checker and a "Forest ...")."""
    recent = [d for v in list(styles.values())[-12:] for d in v["designs"]]
    if not recent:
        return ""
    names = ", ".join(sorted({d["name"] for d in recent}))
    pats = {}
    for d in recent:
        pats[d["pattern"]] = pats.get(d["pattern"], 0) + 1
    used = ", ".join(f"{k} x{v}" for k, v in sorted(pats.items(), key=lambda kv: -kv[1]))
    return (f"Looks you already made for other pieces: {names}. Patterns used so far: {used}. "
            "Don't repeat those names, themes or colour schemes - surprise yourself, and lean on "
            "patterns you've used less.\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="only pieces whose path contains this")
    args = ap.parse_args()
    styles = json.loads(OUT.read_text()) if OUT.exists() else {}
    pieces = sorted(p for p in NAMED.rglob("*.vrm") if not p.relative_to(NAMED).parts[0].startswith("_"))
    todo = [p for p in pieces if str(p.relative_to(NAMED)) not in styles and (not args.only or args.only in str(p))]
    print(f"{len(todo)} of {len(pieces)} pieces to design", flush=True)
    for p in todo:
        rel = str(p.relative_to(NAMED))
        meta = json.loads((CATALOG / f"{p.stem}.json").read_text())
        img = Image.open(CATALOG / f"{p.stem}.png").convert("RGB")
        t = time.time()
        try:
            ans = felt_llm.ask(PROMPT.format(desc=meta["description"], kind=meta["type"], n=N_DESIGNS,
                                             patterns=", ".join(PATTERNS), avoid=_avoid(styles)), images=[img], schema=SCHEMA)
        except Exception as e:  # noqa: BLE001 - skip this one, the next run retries it
            print(f"  ! {rel}: {e!r}", flush=True)
            continue
        styles[rel] = ans
        OUT.write_text(json.dumps(styles, indent=1))
        looks = "; ".join(f"{d['name']} ({d['pattern']} {' '.join(d['colors'])})" for d in ans["designs"])
        print(f"  {rel} [{time.time() - t:.0f}s]: {looks} | {ans['original']}", flush=True)


if __name__ == "__main__":
    main()
