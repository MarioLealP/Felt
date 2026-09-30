"""Geometric fit check between wardrobe pieces (WP-27, 2026-09-30).

Every part export shares the base's bind pose, so two garments can be
compared directly in T-pose. For each pair that can be worn together and
whose bounds touch:
  - near: vertices of one garment within 1.5 cm of the other's surface;
  - outside fraction, both ways: of A's near vertices, how many sit outside
    B's surface (sign by B's outward normal - "outward" = away from her
    body). A clean layering is ~1 one way and ~0 the other;
  - poke = the smaller of the two: how much the inner piece punches through
    the outer one;
  - coplanar = share of near vertices within 1 mm of the other surface
    (z-fighting flicker in the renderer).
Skin-painted pieces (socks, arm warmers) have no geometry and always fit.

Output: OutfitBuilderNamed/_catalog/fit.json
    {"A.vrm|B.vrm": {"outer": "A.vrm", "poke": 0.02, "coplanar": 0.01, "nearA": 812, "nearB": 640}}
Run (WSL): ~/.venvs/felt-outfits/bin/python fit.py
"""

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from combine import Glb  # noqa: E402

NAMED = Path("/mnt/e/Felt/Model/OutfitBuilderNamed")
CATALOG = NAMED / "_catalog"
NEAR = 0.015
COPLANAR = 0.001
MIN_NEAR = 30  # fewer facing contacts than this: too little overlap to judge
# Which categories can be worn together (and so need a check).
PAIRS = [("top", "bottom"), ("bottom", "shoes"), ("dress", "shoes"), ("top", "acc"), ("dress", "acc"),
         ("bottom", "acc"), ("top", "shoes")]


def closest_points(points, tris, k=16):
    """Nearest point on the triangle set (m,3,3) for each point + that
    triangle's index; checks each point's k nearest triangles by centroid."""
    cent = tris.mean(1)
    q_out = np.empty_like(points)
    t_out = np.empty(len(points), int)
    for s in range(0, len(points), 256):
        pts = points[s : s + 256]
        d = np.linalg.norm(pts[:, None, :] - cent[None, :, :], axis=2)
        kk = min(k, d.shape[1])
        nn = np.argpartition(d, kk - 1, axis=1)[:, :kk]
        t = tris[nn]
        pp = np.repeat(pts, kk, axis=0)
        q = _closest_on_tri(pp, t[:, :, 0].reshape(-1, 3), t[:, :, 1].reshape(-1, 3), t[:, :, 2].reshape(-1, 3)).reshape(len(pts), kk, 3)
        dist = np.linalg.norm(q - pts[:, None, :], axis=2)
        best = dist.argmin(1)
        q_out[s : s + 256] = q[np.arange(len(pts)), best]
        t_out[s : s + 256] = nn[np.arange(len(pts)), best]
    return q_out, t_out


def _closest_on_tri(p, a, b, c):
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - b
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - c
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
    v, w = vb / denom, vc / denom
    q = a + ab * v[:, None] + ac * w[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        e = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        q = np.where(e[:, None], a + ab * np.nan_to_num(d1 / (d1 - d3))[:, None], q)
        e = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        q = np.where(e[:, None], a + ac * np.nan_to_num(d2 / (d2 - d6))[:, None], q)
        e = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        q = np.where(e[:, None], b + (c - b) * np.nan_to_num((d4 - d3) / ((d4 - d3) + (d5 - d6)))[:, None], q)
    q = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, q)
    q = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, q)
    q = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, q)
    return q


class Piece:
    def __init__(self, path: Path, base: Glb, skin_pts):
        g = Glb(path)
        base_mats = {m["name"] for m in base.js["materials"]}
        verts, tris = [], []
        for m in g.js["meshes"]:
            for p in m["primitives"]:
                if g.js["materials"][p["material"]]["name"] in base_mats:
                    continue
                pos = g.acc(p["attributes"]["POSITION"])
                idx = g.acc(p["indices"]).reshape(-1, 3)
                used, remap = np.unique(idx, return_inverse=True)
                off = sum(len(v) for v in verts)
                verts.append(pos[used])
                tris.append(remap.reshape(-1, 3) + off)
        self.rel = str(path.relative_to(NAMED))
        self.geom = bool(verts)
        if not self.geom:
            return
        self.v = np.concatenate(verts).astype(np.float64)
        self.t = np.concatenate(tris)
        self.tri = self.v[self.t]
        n = np.cross(self.tri[:, 1] - self.tri[:, 0], self.tri[:, 2] - self.tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        # Outward = away from her body: flip normals facing the nearest skin point.
        cent = self.tri.mean(1)
        near_skin = skin_pts[_nearest(cent, skin_pts)]
        flip = ((cent - near_skin) * n).sum(1) < 0
        n[flip] *= -1
        self.n = n
        self.lo, self.hi = self.v.min(0), self.v.max(0)


def _nearest(points, cloud):
    out = np.empty(len(points), int)
    for s in range(0, len(points), 512):
        d = np.linalg.norm(points[s : s + 512, None, :] - cloud[None, :, :], axis=2)
        out[s : s + 512] = d.argmin(1)
    return out


def side(a: Piece, b: Piece):
    """(near count, outside fraction, coplanar fraction) of a's vertices vs b."""
    m = np.all((a.v > b.lo - NEAR) & (a.v < b.hi + NEAR), axis=1)
    pts = a.v[m]
    if not len(pts):
        return 0, 0.0, 0.0
    q, ti = closest_points(pts, b.tri)
    d = pts - q
    dist = np.linalg.norm(d, axis=1)
    near = dist < NEAR
    if not near.any():
        return 0, 0.0, 0.0
    signed = (d[near] * b.n[ti[near]]).sum(1)
    # Only points really in front of / behind b's surface: a vertex merely
    # beside b's edge (a shirt next to a tie) is offset sideways, not along
    # the normal, and says nothing about layering.
    facing = (np.abs(signed) >= 0.8 * dist[near]) | (dist[near] <= COPLANAR)
    signed = signed[facing]
    if len(signed) < MIN_NEAR:
        return 0, 0.0, 0.0
    return int(len(signed)), float((signed > COPLANAR).mean()), float((np.abs(signed) <= COPLANAR).mean())


def main():
    base = Glb(next((NAMED / "_base").glob("*.vrm")))
    _, sp = base.skin_prim()
    skin_pts = base.acc(sp["attributes"]["POSITION"])[np.unique(base.acc(sp["indices"]))].astype(np.float64)
    meta = {json.loads(f.read_text())["file"]: json.loads(f.read_text()) for f in CATALOG.glob("*.json")
            if f.name not in ("styles.json", "fit.json", "tags.json") and "file" in json.loads(f.read_text())}
    pieces = {}
    t0 = time.time()
    for p in sorted(NAMED.rglob("*.vrm")):
        rel = str(p.relative_to(NAMED))
        if rel.startswith("_") or rel not in meta:
            continue
        pieces[rel] = (meta[rel]["type"], Piece(p, base, skin_pts))
    print(f"loaded {len(pieces)} pieces in {time.time() - t0:.0f}s", flush=True)
    out = {}
    for ta, tb in PAIRS:
        la = [r for r, (t, _) in pieces.items() if t == ta]
        lb = [r for r, (t, _) in pieces.items() if t == tb]
        combos = [(x, y) for x, y in itertools.product(la, lb) if x != y] if ta != tb else list(itertools.combinations(la, 2))
        t1 = time.time()
        for ra, rb in combos:
            a, b = pieces[ra][1], pieces[rb][1]
            if not (a.geom and b.geom) or np.any(a.lo > b.hi + NEAR) or np.any(b.lo > a.hi + NEAR):
                out[f"{ra}|{rb}"] = {"outer": None, "poke": 0.0, "coplanar": 0.0, "nearA": 0, "nearB": 0}
                continue
            na, oa, ca = side(a, b)
            nb, ob, cb = side(b, a)
            if na == 0 or nb == 0:  # touching on one side only: no real overlap
                out[f"{ra}|{rb}"] = {"outer": None, "poke": 0.0, "coplanar": 0.0, "nearA": na, "nearB": nb}
                continue
            outer = ra if oa >= ob else rb
            out[f"{ra}|{rb}"] = {"outer": outer, "poke": round(min(oa, ob), 3),
                                 "coplanar": round((ca * na + cb * nb) / max(na + nb, 1), 3), "nearA": na, "nearB": nb}
        print(f"{ta} x {tb}: {len(combos)} pairs in {time.time() - t1:.0f}s", flush=True)
        (CATALOG / "fit.json").write_text(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
