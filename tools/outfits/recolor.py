"""Luminance-preserving recolour. Hue rotation happens in YIQ (rotating I/Q keeps Y = luma),
then chroma scale, a light tint toward the target hue (so white/grey garments pick up colour
too) and a luma gamma/lift for the pastel/winter looks. Alpha untouched; only alpha>0 pixels change.
"""
import numpy as np
from PIL import Image

# ref: target colour (defines the target hue), sat: chroma multiplier, tint: extra chroma toward
# target, gamma: <1 lifts luma, lift: added to luma (0..1)
PALETTES = {
    "autumn": dict(ref=(200, 110, 40), sat=1.0, tint=0.10, gamma=1.0, lift=0.0),
    "winter": dict(ref=(90, 140, 215), sat=0.6, tint=0.07, gamma=0.9, lift=0.04),
    "pastel": dict(ref=(240, 165, 205), sat=0.55, tint=0.06, gamma=0.7, lift=0.10),
}
M = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]])
Mi = np.linalg.inv(M)


def _yiq(rgb):
    return rgb @ M.T


def dominant_angle(images):
    """chroma-weighted circular mean hue (YIQ angle) over opaque pixels of all images."""
    v = np.zeros(2)
    for im in images:
        a = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255
        px = a[a[..., 3] > 0.5][:, :3]
        if len(px) > 300_000:
            px = px[np.random.default_rng(0).choice(len(px), 300_000, replace=False)]
        q = _yiq(px)
        v += q[:, 1:].sum(0)
    return np.arctan2(v[1], v[0]) if np.hypot(*v) > 1e-6 else None


def recolor(im, pal, dom):
    p = PALETTES[pal]
    ref = _yiq(np.array(p["ref"], dtype=np.float32) / 255)
    tgt = np.arctan2(ref[2], ref[1])
    rot = 0.0 if dom is None else tgt - dom
    a = np.asarray(im.convert("RGBA")).copy()
    m = a[..., 3] > 0
    yiq = _yiq(a[..., :3][m].astype(np.float32) / 255)
    y, i, q = yiq[:, 0], yiq[:, 1], yiq[:, 2]
    c, s = np.cos(rot), np.sin(rot)
    i2, q2 = (i * c - q * s) * p["sat"], (i * s + q * c) * p["sat"]
    tv = np.array([np.cos(tgt), np.sin(tgt)]) * p["tint"]
    w = 1 - np.clip(np.hypot(i, q) / 0.3, 0, 1)      # tint mostly where garment is achromatic
    i2, q2 = i2 + tv[0] * w, q2 + tv[1] * w
    y2 = np.clip(y, 0, 1) ** p["gamma"] * (1 - p["lift"]) + p["lift"]
    rgb = np.stack([y2, i2, q2], 1) @ Mi.T
    a[..., :3][m] = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    return Image.fromarray(a, "RGBA")
