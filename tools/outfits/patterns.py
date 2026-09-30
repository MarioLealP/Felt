"""Procedural fabric patterns for white VRoid garments.

Felt designs a style as a spec (pattern, colours, scale); this renders it
in the garment's texture space and applies it per the garment's own fabric
(classify): white/grey/black cloth takes the pattern multiplied by its own
brightness, coloured cloth is hue-shifted relative to its dominant colour,
line art stays, sheer garments (lace, fishnet) get a solid colour only, and
alpha is never touched.

    spec = {"pattern": "plaid", "colors": ["#2b3a55", "#c8a24a"], "scale": "medium"}
    rgba = apply_style(rgba, spec)
"""

import numpy as np

PATTERNS = ["solid", "stripes", "plaid", "gingham", "polka_dots", "checker", "gradient", "denim", "camo"]
SCALES = {"small": 20, "medium": 40, "large": 80}  # pattern period in px at a 2048 texture


def hex_rgb(text: str) -> np.ndarray:
    t = text.strip().lstrip("#")
    if len(t) == 3:
        t = "".join(c * 2 for c in t)
    return np.array([int(t[i : i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def fabric_mask(img: np.ndarray) -> np.ndarray:
    """1 on near-white/grey fabric, 0 on saturated or dark pixels (soft edges)."""
    f = img[..., :3].astype(np.float32) / 255
    mx, mn = f.max(-1), f.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    return np.clip((0.25 - sat) / 0.1, 0, 1) * np.clip((mx - 0.25) / 0.15, 0, 1)


def _smooth_noise(h, w, cell, rng):
    """Value noise: a coarse random grid, bilinearly upsampled."""
    gh, gw = h // cell + 2, w // cell + 2
    g = rng.random((gh, gw)).astype(np.float32)
    y = np.arange(h, dtype=np.float32) / cell
    x = np.arange(w, dtype=np.float32) / cell
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def render_pattern(h: int, w: int, spec: dict, seed: int = 0) -> np.ndarray:
    """(h, w, 3) float RGB 0-1 for a style spec."""
    cols = [hex_rgb(c) for c in spec.get("colors") or ["#ffffff"]]
    c0 = cols[0]
    c1 = cols[1] if len(cols) > 1 else np.clip(c0 * 0.55, 0, 1)
    c2 = cols[2] if len(cols) > 2 else np.clip((c0 + c1) / 2 * 0.8, 0, 1)
    p = max(4, int(SCALES.get(spec.get("scale", "medium"), 40) * max(h, w) / 2048))
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    kind = spec.get("pattern", "solid")
    rng = np.random.default_rng(seed)

    def mix(a, b, t):
        return a * (1 - t[..., None]) + b * t[..., None]

    if kind == "stripes":
        return mix(c0[None, None], c1[None, None], ((y // (p / 2)) % 2).astype(np.float32))
    if kind == "checker":
        return mix(c0[None, None], c1[None, None], (((x // p) + (y // p)) % 2).astype(np.float32))
    if kind == "gingham":
        bx = ((x // (p / 2)) % 2).astype(np.float32)
        by = ((y // (p / 2)) % 2).astype(np.float32)
        t = (bx + by) / 2  # 0 base, 0.5 one band, 1 crossing
        return mix(c0[None, None], c1[None, None], t)
    if kind == "plaid":
        P = p * 2
        wide_x = ((x % P) < P * 0.35).astype(np.float32)
        wide_y = ((y % P) < P * 0.35).astype(np.float32)
        thin_x = (np.abs((x % P) - P * 0.68) < max(1.0, P * 0.03)).astype(np.float32)
        thin_y = (np.abs((y % P) - P * 0.68) < max(1.0, P * 0.03)).astype(np.float32)
        out = mix(c0[None, None], c1[None, None], 0.55 * wide_x + 0.55 * wide_y - 0.25 * wide_x * wide_y)
        return mix(out, c2[None, None], np.clip(thin_x + thin_y, 0, 1) * 0.9)
    if kind == "polka_dots":
        row = y // p
        xo = x + (row % 2) * p / 2
        dx, dy = (xo % p) - p / 2, (y % p) - p / 2
        return mix(c0[None, None], c1[None, None], (dx * dx + dy * dy < (p * 0.2) ** 2).astype(np.float32))
    if kind == "gradient":
        return mix(c0[None, None], c1[None, None], y / max(h - 1, 1))
    if kind == "denim":
        twill = (((x + y) // max(2, p // 10)) % 2).astype(np.float32)
        n = _smooth_noise(h, w, max(4, p // 2), rng)
        base = mix(c0[None, None], np.clip(c0 * 1.25 + 0.05, 0, 1)[None, None], n * 0.6)
        return base * (1 - 0.12 * twill[..., None])
    if kind == "camo":
        n1 = _smooth_noise(h, w, p * 2, rng)
        n2 = _smooth_noise(h, w, p * 2, np.random.default_rng(seed + 1))
        out = np.broadcast_to(c0, (h, w, 3)).copy()
        out[n1 > 0.55] = c1
        out[(n2 > 0.62) & (n1 <= 0.55)] = c2
        return out
    return np.broadcast_to(c0, (h, w, 3)).copy()  # solid


def rgb_to_hsv(f: np.ndarray) -> np.ndarray:
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mx, mn = f.max(-1), f.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    rm = nz & (mx == r)
    gm = nz & (mx == g) & ~rm
    bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6
    h[gm] = (b - r)[gm] / d[gm] + 2
    h[bm] = (r - g)[bm] / d[bm] + 4
    return np.stack([h / 6, np.where(mx > 0, d / np.maximum(mx, 1e-6), 0), mx], -1)


def hsv_to_rgb(hsv: np.ndarray) -> np.ndarray:
    h, s, v = hsv[..., 0] % 1 * 6, np.clip(hsv[..., 1], 0, 1), np.clip(hsv[..., 2], 0, 1)
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    choices = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    out = np.zeros(hsv.shape, np.float32)
    for k, (a, b, c) in enumerate(choices):
        m = i == k
        out[m] = np.stack([a[m], b[m], c[m]], -1)
    return out


def classify(img: np.ndarray) -> dict:
    """How a garment texture should take a style (Mario's per-garment rules,
    2026-09-30): opaque-ish pixels split into achromatic fabric (multiply /
    tint relative to its own brightness - white, grey AND black cloth),
    coloured fabric (relative hue shift) and line art (untouched); a garment
    with lots of partial alpha is sheer (lace, fishnet) -> solid colour only."""
    f = img[..., :3].astype(np.float32) / 255
    a = img[..., 3]
    hsv = rgb_to_hsv(f)
    vis = a > 8
    sheer = bool(vis.any() and ((a > 8) & (a < 245)).sum() / vis.sum() > 0.15)
    achro = vis & (hsv[..., 1] < 0.22)
    colour = vis & ~achro & (hsv[..., 2] > 0.12)
    lum = hsv[..., 2]
    # Line art: dark, and a small share of the achromatic pixels.
    ach_ref = float(np.percentile(lum[achro], 60)) if achro.sum() > 50 else 1.0
    lines = achro & (lum < min(0.18, ach_ref * 0.45))
    return {"hsv": hsv, "achro": achro & ~lines, "colour": colour, "sheer": sheer, "ach_ref": max(ach_ref, 0.05)}


def apply_style(img: np.ndarray, spec: dict, region: np.ndarray | None = None, seed: int = 0) -> np.ndarray:
    """Style an RGBA uint8 texture per the garment's own fabric (see
    classify). `region` (bool h,w) limits it further (skin-painted legwear:
    only the painted pixels). Alpha is never changed."""
    h, w = img.shape[:2]
    c = classify(img if region is None else np.where(region[..., None], img, 0))
    if c["sheer"]:
        spec = {"pattern": "solid", "colors": (spec.get("colors") or ["#ffffff"])[:1]}
    pat = render_pattern(h, w, spec, seed)
    f = img[..., :3].astype(np.float32) / 255
    out = f.copy()
    reg = np.ones((h, w), bool) if region is None else region
    hsv = c["hsv"]
    # Achromatic cloth: pattern x brightness relative to the cloth's own level.
    a = c["achro"] & reg
    if a.any():
        shade = np.clip(hsv[..., 2] / c["ach_ref"], 0, 1.1)
        out[a] = (pat * shade[..., None])[a]
    # Coloured cloth: move the dominant colour onto the pattern's, keep each
    # pixel's offset from it (hue shift, saturation/value ratios).
    k = c["colour"] & reg
    if k.any():
        dom_h = np.angle(np.exp(2j * np.pi * hsv[..., 0][k]).mean()) / (2 * np.pi)
        dom_s = max(float(np.median(hsv[..., 1][k])), 0.05)
        dom_v = max(float(np.median(hsv[..., 2][k])), 0.05)
        ph = rgb_to_hsv(pat)
        new = np.stack([
            ph[..., 0] + (hsv[..., 0] - dom_h),
            ph[..., 1] * hsv[..., 1] / dom_s,
            ph[..., 2] * hsv[..., 2] / dom_v,
        ], -1)
        out[k] = hsv_to_rgb(new)[k]
    res = img.copy()
    res[..., :3] = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
    return res


def mean_color(spec: dict) -> np.ndarray:
    """Average colour of a style - for MToon's shade colour factor."""
    return render_pattern(128, 128, spec).reshape(-1, 3).mean(0)
