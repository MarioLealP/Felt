"""Mix-and-match outfit builder: splice garments from VRoid "part" exports
onto an underwear base.

Every part export is the same Felt as the base plus exactly one garment, so
the garment is whatever the part has that the base doesn't: its materials,
its extra spring-bone nodes and chains. Everything else (face, hair, body,
humanoid, expressions) comes from the base untouched.

Skin: VRoid deletes body skin hidden under each garment. A combo keeps the
base's full skin minus, per garment, the triangles that garment's export
dropped *near that garment's own fabric* - an export can also drop or
simplify skin elsewhere (the shorts export came with lower-detail feet),
and those must not become holes.

CLI:  python combine.py OUT.vrm BASE.vrm PART.vrm[:#rrggbb] [PART.vrm[:#rrggbb] ...]
      (":#rrggbb" recolours that part - patterns.apply_style, solid)
"""

import copy
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from patterns import apply_style, mean_color  # noqa: E402
from vrm_textures import read_glb, write_glb  # noqa: E402

_CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_SKIN_MAT = "Body_00_SKIN"
# How close (m) a dropped skin triangle must be to a garment's vertices for
# that garment to be the reason it was dropped.
_COVER_RADIUS = 0.05
# A base skin triangle whose centre is further (m) than this from any of the
# part's skin was deleted by VRoid in that export (else merely re-meshed).
_SKIN_GONE = 0.005


class Glb:
    def __init__(self, path):
        self.js, binc = read_glb(path)
        self.bin = bytearray(binc)
        self.path = Path(path)

    def acc(self, i):
        a = self.js["accessors"][i]
        bv = self.js["bufferViews"][a["bufferView"]]
        n = _NC[a["type"]]
        dt = np.dtype(_CT[a["componentType"]])
        stride = bv.get("byteStride", 0)
        assert not stride or stride == dt.itemsize * n, "strided accessor"
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        r = np.frombuffer(bytes(self.bin), dt, a["count"] * n, off)
        return r.reshape(a["count"], n) if n > 1 else r

    def add_view(self, data: bytes, target=None):
        self.bin += b"\0" * (-len(self.bin) % 16)
        bv = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            bv["target"] = target
        self.bin += data
        self.js["bufferViews"].append(bv)
        return len(self.js["bufferViews"]) - 1

    def add_acc(self, arr, gl_type, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        ct = {np.dtype(v): k for k, v in _CT.items()}[arr.dtype]
        a = {
            "bufferView": self.add_view(arr.tobytes(), target),
            "componentType": ct,
            "count": arr.shape[0],
            "type": gl_type,
        }
        if minmax:
            a["min"] = arr.min(0).tolist()
            a["max"] = arr.max(0).tolist()
        self.js["accessors"].append(a)
        return len(self.js["accessors"]) - 1

    def image_bytes(self, i):
        bv = self.js["bufferViews"][self.js["images"][i]["bufferView"]]
        o = bv.get("byteOffset", 0)
        return bytes(self.bin[o : o + bv["byteLength"]])

    def node_index(self):
        names = [n.get("name") for n in self.js["nodes"]]
        assert len(set(names)) == len(names), f"{self.path.name}: duplicate node names"
        return {n: i for i, n in enumerate(names)}

    def parents(self):
        p = {}
        for i, n in enumerate(self.js["nodes"]):
            for c in n.get("children", []):
                p[c] = i
        return p

    def skin_prim(self):
        for mi, m in enumerate(self.js["meshes"]):
            for p in m["primitives"]:
                if _SKIN_MAT in self.js["materials"][p["material"]]["name"]:
                    return mi, p
        raise ValueError("no body skin primitive")

    def mesh_node(self, mi):
        return next(n for n in self.js["nodes"] if n.get("mesh") == mi)


def _tri_keys(pos, idx):
    r = np.round(pos, 4)
    return [tuple(sorted(map(tuple, r[t]))) for t in idx.reshape(-1, 3)]


def _point_tri_distance(p, a, b, c):
    """Distance from points p (n,3) to triangles a,b,c (n,3) - Ericson's
    closest-point-on-triangle, vectorised."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = p - b
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = p - c
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
    v, w = vb / denom, vc / denom
    q = a + ab * v[:, None] + ac * w[:, None]  # interior
    with np.errstate(divide="ignore", invalid="ignore"):
        # edges
        e_ab = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        q = np.where(e_ab[:, None], a + ab * np.nan_to_num(d1 / (d1 - d3))[:, None], q)
        e_ac = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        q = np.where(e_ac[:, None], a + ac * np.nan_to_num(d2 / (d2 - d6))[:, None], q)
        e_bc = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        tbc = np.nan_to_num((d4 - d3) / ((d4 - d3) + (d5 - d6)))
        q = np.where(e_bc[:, None], b + (c - b) * tbc[:, None], q)
    # vertices
    q = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, q)
    q = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, q)
    q = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, q)
    return np.linalg.norm(p - q, axis=1)


def _surface_distance(points, tris, k=24):
    """Distance from each point to the nearest of the triangles (m,3,3),
    checking each point's k nearest triangles by centroid."""
    cent = tris.mean(1)
    out = np.empty(len(points))
    for s in range(0, len(points), 128):
        pts = points[s : s + 128]
        d = np.linalg.norm(pts[:, None, :] - cent[None, :, :], axis=2)
        nn = np.argpartition(d, min(k, d.shape[1] - 1), axis=1)[:, :k]
        t = tris[nn]  # (n,k,3,3)
        pp = np.repeat(pts, nn.shape[1], axis=0)
        dist = _point_tri_distance(pp, t[:, :, 0].reshape(-1, 3), t[:, :, 1].reshape(-1, 3), t[:, :, 2].reshape(-1, 3))
        out[s : s + 128] = dist.reshape(len(pts), -1).min(1)
    return out


def tint_rgba(img, rgb):
    """Multiply-tint the near-white/grey fabric of an RGBA array by rgb (0-1
    floats). Saturated or dark pixels (trims, prints, buttons, line art) are
    left alone; alpha is never touched (lace/fishnet keep their holes)."""
    f = img[..., :3].astype(np.float32) / 255
    mx, mn = f.max(-1), f.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    m = np.clip((0.25 - sat) / 0.1, 0, 1) * np.clip((mx - 0.25) / 0.15, 0, 1)
    out = f * (1 - m[..., None]) + f * np.asarray(rgb, np.float32) * m[..., None]
    res = img.copy()
    res[..., :3] = np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)
    return res


def parse_color(text):
    text = text.lstrip("#")
    return [int(text[i : i + 2], 16) / 255 for i in (0, 2, 4)]


_STYLE_CACHE = Path.home() / ".cache/felt-outfits/styled"


def _styled_texture(data: bytes, style: dict, seed: int) -> bytes:
    """apply_style on an encoded texture, cached on disk by (texture, style)
    - building hundreds of outfits restyles the same pieces over and over."""
    key = hashlib.sha1(data + json.dumps(style, sort_keys=True).encode() + str(seed).encode()).hexdigest()
    f = _STYLE_CACHE / f"{key}.png"
    if f.exists():
        return f.read_bytes()
    img = np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))
    buf = io.BytesIO()
    Image.fromarray(apply_style(img, style, seed=seed)).save(buf, "PNG")
    _STYLE_CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(buf.getvalue())
    return buf.getvalue()


def _texture_refs(obj, key=""):
    """Every textureInfo dict (has 'index') under a *Texture key."""
    if isinstance(obj, dict):
        if "index" in obj and key.lower().endswith("texture"):
            yield obj
        for k, v in obj.items():
            yield from _texture_refs(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _texture_refs(v, key)


class Combiner:
    def __init__(self, base_path):
        self.out = Glb(base_path)
        self.base_mats = {m["name"] for m in self.out.js["materials"]}
        self.base_nodes = set(self.out.node_index())
        self.img_hash = {
            hashlib.sha1(self.out.image_bytes(i)).hexdigest(): i
            for i in range(len(self.out.js["images"]))
        }
        mi, p = self.out.skin_prim()
        self.skin_pos = self.out.acc(p["attributes"]["POSITION"])
        self.skin_idx = self.out.acc(p["indices"]).reshape(-1, 3).copy()
        self.skin_keys = _tri_keys(self.skin_pos, self.skin_idx)
        self.cull = np.zeros(len(self.skin_idx), bool)
        self.added = []
        self.skins = {}  # skin index -> (joints, inverse bind matrices), extended by garments
        self.skin_tex = self._skin_texture(self.out)
        self.skin_tex_dirty = False

    def _skin(self, si):
        if si not in self.skins:
            s = self.out.js["skins"][si]
            self.skins[si] = (list(s["joints"]), list(self.out.acc(s["inverseBindMatrices"])))
        return self.skins[si]

    # -- nodes -----------------------------------------------------------
    def _add_nodes(self, part):
        """Copy the part's nodes the base lacks, under their parents by name."""
        pnames = [n.get("name") for n in part.js["nodes"]]
        pparent = part.parents()
        out_idx = self.out.node_index()
        pending = [i for i, nm in enumerate(pnames) if nm not in out_idx]
        while pending:
            progressed = False
            for i in list(pending):
                par = pparent.get(i)
                if par is not None and pnames[par] not in out_idx:
                    continue
                src = part.js["nodes"][i]
                node = {k: copy.deepcopy(v) for k, v in src.items() if k in ("name", "translation", "rotation", "scale", "matrix")}
                self.out.js["nodes"].append(node)
                ni = len(self.out.js["nodes"]) - 1
                out_idx[pnames[i]] = ni
                if par is None:
                    self.out.js["scenes"][0]["nodes"].append(ni)
                else:
                    self.out.js["nodes"][out_idx[pnames[par]]].setdefault("children", []).append(ni)
                pending.remove(i)
                progressed = True
            assert progressed, "node parent cycle"
        return out_idx

    # -- materials -------------------------------------------------------
    def _copy_material(self, part, mi, style=None):
        mat = copy.deepcopy(part.js["materials"][mi])
        colour_refs = set()
        if style:
            bc = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
            sm = mat.get("extensions", {}).get("VRMC_materials_mtoon", {}).get("shadeMultiplyTexture")
            colour_refs = {id(r) for r in (bc, sm) if r}
            mt = mat.get("extensions", {}).get("VRMC_materials_mtoon", {})
            if "shadeColorFactor" in mt:
                # Shadow tone follows the new colour at the old shadow's depth.
                old = mt["shadeColorFactor"]
                depth = 0.299 * old[0] + 0.587 * old[1] + 0.114 * old[2]
                mt["shadeColorFactor"] = [float(v) for v in np.clip(mean_color(style) * depth * 1.1, 0, 1)]
        tex_map = {}
        for ref in _texture_refs(mat):
            key = (ref["index"], id(ref) in colour_refs)
            if key not in tex_map:
                tex_map[key] = self._copy_texture(part, ref["index"], style if key[1] else None)
            ref["index"] = tex_map[key]
        self.out.js["materials"].append(mat)
        return len(self.out.js["materials"]) - 1

    def _copy_texture(self, part, t, style=None):
        src = part.js["textures"][t]
        data = part.image_bytes(src["source"])
        if style:
            data = _styled_texture(data, style, t)
        h = hashlib.sha1(data).hexdigest()
        if h not in self.img_hash:
            img = {k: v for k, v in part.js["images"][src["source"]].items() if k != "bufferView"}
            if style:
                img["mimeType"] = "image/png"
            img["bufferView"] = self.out.add_view(data)
            self.out.js["images"].append(img)
            self.img_hash[h] = len(self.out.js["images"]) - 1
        tex = {k: v for k, v in src.items() if k not in ("source", "sampler")}
        tex["source"] = self.img_hash[h]
        if "sampler" in src:
            self.out.js["samplers"].append(copy.deepcopy(part.js["samplers"][src["sampler"]]))
            tex["sampler"] = len(self.out.js["samplers"]) - 1
        self.out.js["textures"].append(tex)
        return len(self.out.js["textures"]) - 1

    # -- springs ---------------------------------------------------------
    def _copy_springs(self, part, out_idx):
        psb = part.js["extensions"]["VRMC_springBone"]
        osb = self.out.js["extensions"]["VRMC_springBone"]
        pnames = [n.get("name") for n in part.js["nodes"]]
        ogroups = {g["name"]: gi for gi, g in enumerate(osb["colliderGroups"])}
        new = 0
        for s in psb["springs"]:
            if all(pnames[j["node"]] in self.base_nodes for j in s["joints"]):
                continue
            s = copy.deepcopy(s)
            for j in s["joints"]:
                j["node"] = out_idx[pnames[j["node"]]]
            s["colliderGroups"] = [
                ogroups[psb["colliderGroups"][g]["name"]] for g in s.get("colliderGroups", [])
                if psb["colliderGroups"][g]["name"] in ogroups
            ]
            if "center" in s:
                s["center"] = out_idx[pnames[s["center"]]]
            osb["springs"].append(s)
            new += 1
        return new

    # -- garments --------------------------------------------------------
    def add_part(self, path, label, style=None):
        """`style`: a patterns.py spec ({"pattern", "colors", "scale"}) for
        this part's garment, or None to keep it as exported."""
        part = Glb(path)
        out_idx = self._add_nodes(part)
        pnames = [n.get("name") for n in part.js["nodes"]]
        garment_pos = []
        for mi, m in enumerate(part.js["meshes"]):
            gprims = [p for p in m["primitives"] if part.js["materials"][p["material"]]["name"] not in self.base_mats]
            if not gprims:
                continue
            pnode = part.mesh_node(mi)
            pskin = part.js["skins"][pnode["skin"]]
            # Same layout as a VRoid export: the garment joins the base mesh
            # its part mesh corresponds to (Body/Face/Hair, by node name),
            # on that mesh's skin - extended with any joints it lacks.
            onode = next(n for n in self.out.js["nodes"] if n.get("name") == pnode.get("name") and "mesh" in n)
            joints, ibm = self._skin(onode["skin"])
            pibm = part.acc(pskin["inverseBindMatrices"])
            jmap = np.zeros(len(pskin["joints"]), np.uint16)
            for k, pj in enumerate(pskin["joints"]):
                oj = out_idx[pnames[pj]]
                if oj not in joints:
                    joints.append(oj)
                    ibm.append(pibm[k])
                jmap[k] = joints.index(oj)
            for p in gprims:
                idx = part.acc(p["indices"])
                used, remap = np.unique(idx, return_inverse=True)
                attrs = {}
                for name, gl in (("POSITION", "VEC3"), ("NORMAL", "VEC3"), ("TEXCOORD_0", "VEC2"), ("JOINTS_0", "VEC4"), ("WEIGHTS_0", "VEC4")):
                    if name in p["attributes"]:
                        data = part.acc(p["attributes"][name])[used]
                        if name == "JOINTS_0":
                            data = jmap[data]
                        attrs[name] = self.out.add_acc(data, gl, 34962, minmax=(name == "POSITION"))
                        if name == "POSITION":
                            garment_pos.append(data)
                ind = self.out.add_acc(remap.astype(np.uint32), "SCALAR", 34963)
                prim = {"mode": 4, "indices": ind, "attributes": attrs, "material": self._copy_material(part, p["material"], style)}
                omesh = self.out.js["meshes"][onode["mesh"]]
                assert not omesh["primitives"][0].get("targets"), "morph-target mesh: garment can't join it"
                if "extras" in omesh["primitives"][0]:
                    prim["extras"] = copy.deepcopy(omesh["primitives"][0]["extras"])
                omesh["primitives"].append(prim)
        painted = self._paint_skin(part, style)
        assert garment_pos or painted, f"{path}: nothing the base lacks (no garment, no skin paint)"
        springs = self._copy_springs(part, out_idx)
        culled = self._cull_skin(part, np.concatenate(garment_pos)) if garment_pos else 0
        self.added.append(label)
        print(f"  + {label}: {sum(len(g) for g in garment_pos)} verts, {springs} spring chains, {culled} skin tris hidden, {painted} skin px painted")

    @staticmethod
    def _skin_texture(g):
        _, p = g.skin_prim()
        t = g.js["materials"][p["material"]]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
        return np.asarray(Image.open(io.BytesIO(g.image_bytes(g.js["textures"][t]["source"]))).convert("RGBA")).copy()

    def _paint_skin(self, part, style=None):
        """Legwear (socks, tights) is painted on the skin texture, not a mesh:
        carry over whatever the part's skin texture changed vs the base."""
        tex = self._skin_texture(part)
        ref = self._base_skin_tex()
        assert tex.shape == ref.shape, "skin texture size differs"
        mask = np.abs(tex.astype(int) - ref.astype(int)).max(-1) > 2
        if mask.any():
            if style:
                tex = apply_style(tex, style, region=mask)
            self.skin_tex[mask] = tex[mask]
            self.skin_tex_dirty = True
        return int(mask.sum())

    def _base_skin_tex(self):
        if not hasattr(self, "_base_skin"):
            self._base_skin = self._skin_texture(self.out)
        return self._base_skin

    def _cull_skin(self, part, gpos):
        """Hide base skin the part's export no longer has, near the garment.
        "No longer has" is geometric, not an exact triangle match: some
        exports (shoes, shorts) come with a re-meshed foot/ankle, whose skin
        is still there, just triangulated differently."""
        _, p = part.skin_prim()
        ppos = part.acc(p["attributes"]["POSITION"])
        pidx = part.acc(p["indices"]).reshape(-1, 3)
        pkeys = set(_tri_keys(ppos, pidx))
        unmatched = np.array([k not in pkeys for k in self.skin_keys])
        cand = np.nonzero(unmatched & ~self.cull)[0]
        if not len(cand):
            return 0
        cent = self.skin_pos[self.skin_idx[cand]].mean(1)
        gone = _surface_distance(cent, ppos[pidx]) > _SKIN_GONE
        near = np.zeros(len(cand), bool)
        for s in range(0, len(cand), 256):
            d = np.linalg.norm(cent[s : s + 256, None, :] - gpos[None, :, :], axis=2).min(1)
            near[s : s + 256] = d < _COVER_RADIUS
        hide = gone & near
        self.cull[cand[hide]] = True
        return int(hide.sum())

    def write(self, path, title):
        mi, p = self.out.skin_prim()
        keep = self.skin_idx[~self.cull].ravel().astype(np.uint32)
        p["indices"] = self.out.add_acc(keep, "SCALAR", 34963)
        for si, (joints, ibm) in self.skins.items():
            s = self.out.js["skins"][si]
            s["joints"] = joints
            s["inverseBindMatrices"] = self.out.add_acc(np.array(ibm, np.float32), "MAT4")
        if self.skin_tex_dirty:
            buf = io.BytesIO()
            Image.fromarray(self.skin_tex).save(buf, "PNG")
            mat = self.out.js["materials"][p["material"]]
            bc = mat["pbrMetallicRoughness"]["baseColorTexture"]
            tex = copy.deepcopy(self.out.js["textures"][bc["index"]])
            self.out.js["images"].append({"name": "SkinPainted", "mimeType": "image/png", "bufferView": self.out.add_view(buf.getvalue())})
            tex["source"] = len(self.out.js["images"]) - 1
            self.out.js["textures"].append(tex)
            ti = len(self.out.js["textures"]) - 1
            old = bc["index"]
            for ref in _texture_refs(mat):
                if ref["index"] == old:
                    ref["index"] = ti
        meta = self.out.js["extensions"]["VRMC_vrm"]["meta"]
        meta["name"] = title
        self.out.js["buffers"] = [{"byteLength": len(self.out.bin)}]
        write_glb(path, self.out.js, bytes(self.out.bin))
        print(f"wrote {path} ({len(self.out.bin) // 1024} KB, skin {len(keep) // 3}/{len(self.skin_idx)} tris)")


def main(argv):
    out, base, *parts = argv
    c = Combiner(base)
    for p in parts:
        path, _, colour = p.partition(":#")
        style = {"pattern": "solid", "colors": ["#" + colour]} if colour else None
        c.add_part(path, Path(path).stem.removeprefix("Felt_"), style)
    c.write(out, Path(out).stem)


if __name__ == "__main__":
    main(sys.argv[1:])
