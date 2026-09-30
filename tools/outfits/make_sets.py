"""Generate outfit sets from the tagged, styled, fit-checked pieces (WP-27).

A set = (top + bottom | dress) + shoes, optionally socks, a neck accessory
and the arm piece; each piece in its original look or one of Felt's
designs (styles.json). Rules:
  - fit (fit.json): top+bottom poke <= 0.25, bottom+shoes poke <= 0.40
    (calibrated by eye 2026-09-30: 0.30 trench coat + pleated skirt clips
    visibly, 0.15 is clean). Neck pieces aren't geometry-filtered (thin
    ribbons fool the measure) - skipped instead when the top/dress already
    has one built in.
  - socks only when the legs show (bottom ends above the shin, or a dress);
  - style: the main pieces must share a style family, formality within 2;
  - colour: at most 3 distinct hues across the set (neutrals free), at most
    2 patterned pieces;
  - variety: each piece in at most MAX_USES sets, no two sets with the same
    pieces.
Output: E:/Felt/review/wardrobe-sets/sets.json
Run (WSL): ~/.venvs/felt-outfits/bin/python make_sets.py [--n 200] [--seed 1]
"""

import argparse
import colorsys
import json
import random
from pathlib import Path

NAMED = Path("/mnt/e/Felt/Model/OutfitBuilderNamed")
CATALOG = NAMED / "_catalog"
OUT_DIR = Path("/mnt/e/Felt/review/wardrobe-sets")
MAX_USES = 12
# Style families: pieces match when their styles fall in a shared family
# (exact shared tags only found 96 sets in 80k tries).
FAMILIES = [
    {"casual", "streetwear", "cozy", "sporty"},
    {"school", "cute", "lolita", "casual"},
    {"gothic", "punk", "lolita", "streetwear"},
    {"formal", "elegant", "school"},
    {"techwear", "streetwear", "sporty", "punk"},
    {"cute", "cozy", "elegant", "casual"},
]
POKE_TOP_BOTTOM = 0.25
POKE_BOTTOM_SHOES = 0.40
SHIN_Y = 0.35  # a bottom ending above this shows the legs (socks visible)
NECK_BUILT_IN = {"tie", "bow", "ribbon", "choker", "necklace"}


def load():
    tags = json.loads((CATALOG / "tags.json").read_text())
    styles = json.loads((CATALOG / "styles.json").read_text())
    fit = json.loads((CATALOG / "fit.json").read_text())
    pieces = {}
    for rel, t in tags.items():
        folder = rel.split("/")[0].lower()
        kind = t["type"]
        if kind == "acc":
            kind = "arm" if "arm" in folder else "neck"
        looks = [{"name": "original", "spec": None, "color": t["color"], "chromatic": t["chromatic"], "pattern": "original"}]
        for d in styles.get(rel, {}).get("designs", []):
            looks.append({"name": d["name"], "spec": {k: d[k] for k in ("pattern", "colors", "scale")}, "why": d["why"],
                          "color": d["colors"][0], "chromatic": _chromatic(d["colors"][0]), "pattern": d["pattern"],
                          "all_colors": d["colors"]})
        pieces[rel] = {"rel": rel, "kind": kind, "tags": t, "looks": looks, "felt_original": styles.get(rel, {}).get("original")}
    return pieces, fit


def _hsv(hex_):
    h = hex_.lstrip("#")
    return colorsys.rgb_to_hsv(*(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)))


def _chromatic(hex_):
    _, s, v = _hsv(hex_)
    return s > 0.22 and v > 0.15


def fit_ok(fit, a, b, limit):
    v = fit.get(f"{a}|{b}") or fit.get(f"{b}|{a}")
    return v is None or v["outer"] is None or v["poke"] <= limit


def colour_ok(chosen):
    hues = []
    for p, look in chosen:
        cols = look.get("all_colors", [look["color"]]) if look["spec"] else [look["color"]]
        for c in cols[:2]:
            if _chromatic(c):
                hues.append(_hsv(c)[0])
    clusters = []
    for h in sorted(hues):
        if not any(min(abs(h - c), 1 - abs(h - c)) < 0.1 for c in clusters):
            clusters.append(h)
    patterned = sum(1 for _, look in chosen if look["pattern"] not in ("original", "solid", "gradient"))
    return len(clusters) <= 3 and patterned <= 2, len(clusters), patterned


def _families(styles) -> set:
    return {i for i, fam in enumerate(FAMILIES) if fam & set(styles)}


def style_score(main):
    sets = [set(p["tags"]["styles"]) for p in main]
    fams = [_families(s) for s in sets]
    common = set.intersection(*sets) if sets else set()
    if not common and fams and set.intersection(*fams):
        # No shared tag, but a shared family: name it by the family's tags present.
        fam = FAMILIES[min(set.intersection(*fams))]
        common = set.union(*sets) & fam
    union = set.union(*sets) if sets else set()
    forms = [p["tags"]["formality"] for p in main]
    return len(common) / max(len(union), 1), max(forms) - min(forms), sorted(common)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--append", action="store_true", help="keep sets.json's sets, add until --n")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    pieces, fit = load()
    by = {}
    for p in pieces.values():
        by.setdefault(p["kind"], []).append(p)
    uses = {r: 0 for r in pieces}
    sets, seen, tries = [], set(), 0
    if args.append and (OUT_DIR / "sets.json").exists():
        sets = json.loads((OUT_DIR / "sets.json").read_text())
        for s in sets:
            seen.add(tuple(sorted(p["rel"] for p in s["pieces"])))
            for p in s["pieces"]:
                uses[p["rel"]] = uses.get(p["rel"], 0) + 1
        rng.seed(args.seed + len(sets))

    def pick(kind):
        pool = [p for p in by.get(kind, []) if uses[p["rel"]] < MAX_USES]
        if not pool:
            return None
        w = [1.0 / (1 + uses[p["rel"]]) for p in pool]
        return rng.choices(pool, w)[0]

    while len(sets) < args.n and tries < args.n * 400:
        tries += 1
        if rng.random() < 0.15 and by.get("dress"):
            main_pieces = [pick("dress")]
        else:
            main_pieces = [pick("top"), pick("bottom")]
        shoes = pick("shoes")
        if None in main_pieces or shoes is None:
            continue
        if len(main_pieces) == 2 and not fit_ok(fit, main_pieces[0]["rel"], main_pieces[1]["rel"], POKE_TOP_BOTTOM):
            continue
        lower = main_pieces[-1]
        if lower["kind"] == "bottom" and not fit_ok(fit, lower["rel"], shoes["rel"], POKE_BOTTOM_SHOES):
            continue
        overlap, form_gap, common = style_score(main_pieces + [shoes])
        core_overlap, core_gap, core_common = style_score(main_pieces)
        if not core_common or core_gap > 2 or form_gap > 3:
            continue
        extra = []
        legs_show = lower["kind"] == "dress" or (lower["tags"]["y_lo"] or 0) > SHIN_Y
        if legs_show and rng.random() < 0.6 and (s := pick("socks")):
            extra.append(s)
        built_in = set().union(*(set(p["tags"]["built_in"]) for p in main_pieces))
        if not (built_in & NECK_BUILT_IN) and rng.random() < 0.3 and (n := pick("neck")):
            extra.append(n)
        if rng.random() < 0.1 and (a := pick("arm")):
            extra.append(a)
        chosen_pieces = main_pieces + [shoes] + extra
        key = tuple(sorted(p["rel"] for p in chosen_pieces))
        if key in seen:
            continue
        # Looks: a few random assignments, keep the first that passes colour rules.
        for _ in range(25):
            chosen = [(p, p["looks"][0] if rng.random() < 0.3 or len(p["looks"]) == 1 else rng.choice(p["looks"][1:]))
                      for p in chosen_pieces]
            ok, n_hues, n_pat = colour_ok(chosen)
            if ok:
                break
        else:
            continue
        seen.add(key)
        for p in chosen_pieces:
            uses[p["rel"]] += 1
        sid = f"set_{len(sets) + 1:03d}"
        sets.append({
            "id": sid,
            "pieces": [{"rel": p["rel"], "kind": p["kind"], "look": look["name"], "spec": look["spec"],
                        "why": look.get("why"), "felt_original": p["felt_original"] if look["spec"] is None else None}
                       for p, look in chosen],
            "styles": core_common, "formality_gap": core_gap, "hues": n_hues, "patterned": n_pat,
        })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "sets.json").write_text(json.dumps(sets, indent=1))
    used = sum(1 for v in uses.values() if v)
    print(f"{len(sets)} sets in {tries} tries; {used}/{len(pieces)} pieces used; "
          f"dresses {sum(1 for s in sets if s['pieces'][0]['kind'] == 'dress')}")


if __name__ == "__main__":
    main()
