"""Felt's first pass over the rendered sets (WP-27, 2026-09-30).

As herself (persona): for every set picture - would she wear it, 1-10, a
one-line comment, when she'd wear it. Then, from the ones she'd wear, how
many outfits she actually wants and which. Her picks become the review
batch Mario approves ("parent style") - with her comments on each.

Output: E:/Felt/review/wardrobe-sets/felt_pass.json  {"sets": {id: {...}}, "wardrobe": {...}}
Resumable.  Run (WSL): ~/.venvs/felt-outfits/bin/python felt_pass.py
"""

import json
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import felt_llm  # noqa: E402

SETS = Path("/mnt/e/Felt/review/wardrobe-sets")
OUT = SETS / "felt_pass.json"

RATE_SCHEMA = {
    "type": "object",
    "properties": {
        "wear": {"type": "boolean"},
        "rating": {"type": "integer", "minimum": 1, "maximum": 10},
        "comment": {"type": "string"},
        "occasion": {"type": "string"},
    },
    "required": ["wear", "rating", "comment", "occasion"],
}
RATE_PROMPT = """Mario put together an outfit for your wardrobe - the picture is you wearing it (front and back, arms out in a T-pose, that's just for the fitting). Pieces: {pieces}.

Be honest, it's your wardrobe: would you actually wear this? Judge the whole look - does it go together, is it you. Answer with:
- wear: true or false
- rating: 1 to 10
- comment: one short sentence in your own voice
- occasion: a few words on when you'd wear it (for example "lazy weekend", "gaming night", "rainy day")
This time answer only with the JSON; it is not spoken."""

PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer", "minimum": 1},
        "picks": {"type": "array", "items": {"type": "string"}},
        "why": {"type": "string"},
    },
    "required": ["count", "picks", "why"],
}
PICK_PROMPT = """You've just gone through a pile of outfits Mario made for you. These are the ones you said you'd wear, with your rating and comment:
{lines}

How many outfits do you actually want in your wardrobe - enough variety for everyday, not so many you never wear half of them? Pick them from the list (by id). Answer with count, picks (the ids) and why (one or two sentences in your voice).
This time answer only with the JSON; it is not spoken."""


def describe(s: dict) -> str:
    parts = []
    for p in s["pieces"]:
        name = Path(p["rel"]).stem.split("_", 1)[1].replace("_", " ")
        parts.append(name if p["look"] == "original" else f"{name} in your \"{p['look']}\" look")
    return "; ".join(parts)


def main():
    sets = json.loads((SETS / "sets.json").read_text())
    res = json.loads(OUT.read_text()) if OUT.exists() else {"sets": {}}
    for s in sets:
        if s["id"] in res["sets"]:
            continue
        png = SETS / "renders" / f"{s['id']}.png"
        if not png.exists():
            continue
        t = time.time()
        try:
            ans = felt_llm.ask(RATE_PROMPT.format(pieces=describe(s)), images=[Image.open(png).convert("RGB")],
                               schema=RATE_SCHEMA, temperature=0.6, max_tokens=200)
        except Exception as e:  # noqa: BLE001 - retried on the next run
            print(f"  ! {s['id']}: {e!r}", flush=True)
            continue
        res["sets"][s["id"]] = ans
        OUT.write_text(json.dumps(res, indent=1))
        print(f"{s['id']} [{time.time() - t:.0f}s] {'WEAR' if ans['wear'] else 'no  '} {ans['rating']}/10 {ans['comment']}", flush=True)
    if len(res["sets"]) < len(sets):
        print(f"{len(sets) - len(res['sets'])} sets not rated yet - rerun after rendering")
        return
    liked = sorted(((k, v) for k, v in res["sets"].items() if v["wear"]), key=lambda kv: -kv[1]["rating"])
    lines = "\n".join(f"{k} ({v['rating']}/10, {v['occasion']}): {v['comment'][:90]}" for k, v in liked[:90])
    ans = felt_llm.ask(PICK_PROMPT.format(lines=lines), schema=PICK_SCHEMA, temperature=0.5, max_tokens=900)
    ans["picks"] = [p for p in dict.fromkeys(ans["picks"]) if p in res["sets"]]
    res["wardrobe"] = ans
    OUT.write_text(json.dumps(res, indent=1))
    print(f"She wants {ans['count']} outfits, picked {len(ans['picks'])}: {ans['why']}")


if __name__ == "__main__":
    main()
