"""WP-33 batch 2: pattern tees from the outfits pattern engine (patterns.py).

The base tee is white cloth, so apply_style multiplies each pattern by the
fabric's own shading, the same way generated outfits are styled. No text,
ever (Mario 2026-10-01). Writes E:/Felt/Assets/tees/<name>.png and skips
files that already exist; it never deletes anything (unlike
generate_tees.py's clean step). Then render them for review with
render_tees.py.

Run (WSL): ~/.venvs/felt-outfits/bin/python make_pattern_tees.py
"""

from pathlib import Path

import numpy as np
from PIL import Image

from patterns import apply_style

BASE = Path(__file__).parent / "base_tee.png"
TEES = Path("/mnt/e/Felt/Assets/tees")

# name -> style spec. Colourways lean on her palette (sage hair, pastels,
# navy/black basics) plus a few seasonal ones (October / December).
STYLES = {
    "breton_navy": {"pattern": "stripes", "colors": ["#f4f1ea", "#24305a"], "scale": "small"},
    "breton_black": {"pattern": "stripes", "colors": ["#f4f1ea", "#2a2a2e"], "scale": "small"},
    "breton_red": {"pattern": "stripes", "colors": ["#f4f1ea", "#b8323a"], "scale": "small"},
    "stripes_sage": {"pattern": "stripes", "colors": ["#f2f4ee", "#94b496"], "scale": "medium"},
    "stripes_pink": {"pattern": "stripes", "colors": ["#fbf3f5", "#f2a9bb"], "scale": "medium"},
    "stripes_grey_wide": {"pattern": "stripes", "colors": ["#d9d9dc", "#5a5c63"], "scale": "large"},
    "gingham_pink": {"pattern": "gingham", "colors": ["#fbf4f6", "#e98ea6"], "scale": "small"},
    "gingham_blue": {"pattern": "gingham", "colors": ["#f3f7fb", "#7fa6d6"], "scale": "small"},
    "gingham_sage": {"pattern": "gingham", "colors": ["#f2f5f0", "#88a98a"], "scale": "small"},
    "gingham_black": {"pattern": "gingham", "colors": ["#f4f4f4", "#3a3a3e"], "scale": "small"},
    "dots_navy": {"pattern": "polka_dots", "colors": ["#24305a", "#f4f1ea"], "scale": "small"},
    "dots_black": {"pattern": "polka_dots", "colors": ["#2a2a2e", "#f4f1ea"], "scale": "small"},
    "dots_pink": {"pattern": "polka_dots", "colors": ["#f6c3cf", "#ffffff"], "scale": "small"},
    "dots_yellow": {"pattern": "polka_dots", "colors": ["#fbeea0", "#ffffff"], "scale": "medium"},
    "plaid_red": {"pattern": "plaid", "colors": ["#a82a33", "#2a2a2e", "#e8d6a0"], "scale": "medium"},
    "plaid_navy_green": {"pattern": "plaid", "colors": ["#2c4a3a", "#24305a", "#d8c068"], "scale": "medium"},
    "plaid_grey": {"pattern": "plaid", "colors": ["#c8c8cc", "#6a6c73", "#f2f2f2"], "scale": "medium"},
    "checker_bw": {"pattern": "checker", "colors": ["#f2f2f2", "#2a2a2e"], "scale": "small"},
    "checker_lavender": {"pattern": "checker", "colors": ["#f4f0fa", "#c3b2e3"], "scale": "small"},
    "camo_sage": {"pattern": "camo", "colors": ["#a4b89c", "#6e8466", "#d3dccb"], "scale": "medium"},
    "camo_urban": {"pattern": "camo", "colors": ["#b8b9bd", "#6a6c73", "#e6e6e8"], "scale": "medium"},
    "fade_pink_lavender": {"pattern": "gradient", "colors": ["#f6bccb", "#c3b2e3"]},
    "fade_sky": {"pattern": "gradient", "colors": ["#e8f2fc", "#7fa6d6"]},
    "fade_sunset": {"pattern": "gradient", "colors": ["#fbe39a", "#ef8a7a"]},
    "chambray": {"pattern": "denim", "colors": ["#7d97bd"], "scale": "small"},
    # seasonal
    "halloween_stripes": {"pattern": "stripes", "colors": ["#2a2a2e", "#e8792b"], "scale": "medium"},
    "halloween_dots": {"pattern": "polka_dots", "colors": ["#2a2a2e", "#e8792b"], "scale": "medium"},
    "xmas_plaid": {"pattern": "plaid", "colors": ["#a82a33", "#1f4a32", "#f2f2f2"], "scale": "medium"},
    "xmas_stripes": {"pattern": "stripes", "colors": ["#f4f1ea", "#b8323a"], "scale": "medium"},
    "xmas_gingham": {"pattern": "gingham", "colors": ["#f4f4f4", "#1f4a32"], "scale": "small"},
}


def main():
    base = np.asarray(Image.open(BASE).convert("RGBA"))
    TEES.mkdir(parents=True, exist_ok=True)
    for i, (name, spec) in enumerate(STYLES.items()):
        out = TEES / f"{name}.png"
        if out.exists():
            continue
        Image.fromarray(apply_style(base, spec, seed=i)).save(out)
        print("made", name, flush=True)


if __name__ == "__main__":
    main()
