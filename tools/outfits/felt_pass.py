"""Felt's first pass over the rendered sets (WP-27, 2026-09-30).

Rating outfits one at a time didn't work: she said she'd wear all of the
first 98 and gave 95 of them 8/10 (her persona is easy company and on
Mario's side). So she *compares* instead: groups of four outfits side by
side (front views, labelled A-D), ranked best to worst with a one-line
comment each. Every set appears in ROUNDS different groups; its score is
the average Borda points (3/2/1/0). Then, from the top of that ranking with
her comments, she decides how many outfits she wants and which. Her picks
become Mario's review batch ("parent style").

Output: E:/Felt/review/wardrobe-sets/felt_rank.json
    {"groups": [{"ids": [...], "ranking": [...], "comments": {...}}], "scores": {id: avg},
     "comments": {id: [...]}, "wardrobe": {"count", "picks", "why"}}
Resumable.  Run (WSL): ~/.venvs/felt-outfits/bin/python felt_pass.py
"""

import json
import random
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import felt_llm  # noqa: E402

SETS = Path("/mnt/e/Felt/review/wardrobe-sets")
OUT = SETS / "felt_rank.json"
ROUNDS = 2
GROUP = 4
LABELS = "ABCD"

RANK_SCHEMA = {
    "type": "object",
    "properties": {
        "ranking": {"type": "array", "minItems": GROUP, "maxItems": GROUP, "items": {"type": "string", "enum": list(LABELS)}},
        "comments": {
            "type": "object",
            "properties": {label: {"type": "string"} for label in LABELS},
            "required": list(LABELS),
        },
    },
    "required": ["ranking", "comments"],
}
RANK_PROMPT = """Mario made outfits for your wardrobe. Here are four of them on you, side by side: A, B, C, D (front view; the arms-out pose is just for the fitting).

Rank them from the one you like most to the one you like least - you have to pick, no ties. Judge the whole look: do the pieces go together, do the colours work, is it you.
- ranking: the four letters, favourite first
- comments: for each letter, one short honest sentence in your own voice
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
PICK_PROMPT = """You've compared all the outfits Mario made for you. These are the best ones, highest ranked first, with what you said about them:
{lines}

How many outfits do you actually want in your wardrobe? Enough variety for everyday, not so many you'd never wear half. Pick them from this list by id. Answer with count, picks (the ids) and why (one or two sentences in your voice).
This time answer only with the JSON; it is not spoken."""


def groups_for(ids: list[str], seed: int = 3) -> list[list[str]]:
    """ROUNDS shuffles, each cut into groups of GROUP (the last group topped
    up with random others so every group is full)."""
    rng = random.Random(seed)
    out = []
    for _ in range(ROUNDS):
        order = ids[:]
        rng.shuffle(order)
        for i in range(0, len(order), GROUP):
            g = order[i : i + GROUP]
            while len(g) < GROUP:
                extra = rng.choice([x for x in ids if x not in g])
                g.append(extra)
            out.append(g)
    return out


def sheet(ids: list[str]) -> Image.Image:
    """The four front views side by side, labelled."""
    tiles = []
    for sid in ids:
        full = Image.open(SETS / "renders" / f"{sid}.png").convert("RGB")
        tiles.append(full.crop((0, 28, 380, 748)))  # front half
    w, h = tiles[0].size
    out = Image.new("RGB", (w * GROUP, h + 40), (236, 236, 240))
    d = ImageDraw.Draw(out)
    for i, t in enumerate(tiles):
        out.paste(t, (i * w, 40))
        d.text((i * w + w // 2 - 6, 10), LABELS[i], fill=(20, 20, 20), font_size=26)
    return out.resize((out.width * 3 // 4, out.height * 3 // 4))


def main():
    sets = json.loads((SETS / "sets.json").read_text())
    ids = [s["id"] for s in sets if (SETS / "renders" / f"{s['id']}.png").exists()]
    res = json.loads(OUT.read_text()) if OUT.exists() else {"groups": []}
    plan = groups_for(ids)
    done = {tuple(g["ids"]) for g in res["groups"]}
    for g in plan:
        if tuple(g) in done:
            continue
        t = time.time()
        try:
            ans = felt_llm.ask(RANK_PROMPT, images=[sheet(g)], schema=RANK_SCHEMA, temperature=0.5, max_tokens=400)
        except Exception as e:  # noqa: BLE001 - retried on the next run
            print(f"  ! {g}: {e!r}", flush=True)
            continue
        ranking = list(dict.fromkeys(ans["ranking"]))
        if sorted(ranking) != list(LABELS):
            print(f"  ! {g}: bad ranking {ans['ranking']}", flush=True)
            continue
        res["groups"].append({"ids": g, "ranking": [g[LABELS.index(x)] for x in ranking],
                              "comments": {g[LABELS.index(k)]: v for k, v in ans["comments"].items()}})
        OUT.write_text(json.dumps(res, indent=1))
        print(f"[{time.time() - t:.0f}s] {' > '.join(res['groups'][-1]['ranking'])}", flush=True)
    if len(res["groups"]) < len(plan):
        print(f"{len(plan) - len(res['groups'])} groups left - rerun")
        return
    pts, n, comments = {}, {}, {}
    for g in res["groups"]:
        for rank, sid in enumerate(g["ranking"]):
            pts[sid] = pts.get(sid, 0) + (GROUP - 1 - rank)
            n[sid] = n.get(sid, 0) + 1
        for sid, c in g["comments"].items():
            comments.setdefault(sid, []).append(c)
    res["scores"] = {k: round(pts[k] / n[k], 2) for k in sorted(pts, key=lambda k: -pts[k] / n[k])}
    res["comments"] = comments
    top = list(res["scores"])[:45]
    lines = "\n".join(f"{k} (score {res['scores'][k]}): {comments[k][0][:100]}" for k in top)
    ans = felt_llm.ask(PICK_PROMPT.format(lines=lines), schema=PICK_SCHEMA, temperature=0.5, max_tokens=900)
    ans["picks"] = [p for p in dict.fromkeys(ans["picks"]) if p in res["scores"]]
    res["wardrobe"] = ans
    OUT.write_text(json.dumps(res, indent=1))
    print(f"She wants {ans['count']} outfits, picked {len(ans['picks'])}: {ans['why']}")


if __name__ == "__main__":
    main()
