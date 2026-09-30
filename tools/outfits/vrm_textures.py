"""Read/extract/replace clothing textures in a .vrm/.glb (GLB 2.0, stdlib only).

CLI:  python vrm_textures.py list  X.vrm
      python vrm_textures.py extract X.vrm outdir
      python vrm_textures.py selfcheck X.vrm
"""
import json, struct, sys
from pathlib import Path

MAGIC, JSON_T, BIN_T = 0x46546C67, 0x4E4F534A, 0x004E4942


def read_glb(path):
    b = Path(path).read_bytes()
    magic, ver, _ = struct.unpack_from("<III", b, 0)
    assert magic == MAGIC and ver == 2, "not GLB 2.0"
    off, js, binc = 12, None, b""
    while off < len(b):
        n, t = struct.unpack_from("<II", b, off)
        data = b[off + 8: off + 8 + n]
        if t == JSON_T:
            js = json.loads(data.decode("utf8"))
        elif t == BIN_T and not binc:
            binc = data
        off += 8 + n
    return js, binc


def write_glb(path, js, binc):
    j = json.dumps(js, separators=(",", ":")).encode("utf8")
    j += b" " * (-len(j) % 4)
    binc += b"\0" * (-len(binc) % 4)
    total = 12 + 8 + len(j) + 8 + len(binc)
    Path(path).write_bytes(
        struct.pack("<III", MAGIC, 2, total)
        + struct.pack("<II", len(j), JSON_T) + j
        + struct.pack("<II", len(binc), BIN_T) + binc)


def image_bytes(js, binc, i):
    bv = js["bufferViews"][js["images"][i]["bufferView"]]
    o = bv.get("byteOffset", 0)
    return binc[o:o + bv["byteLength"]]


def clothing_images(js):
    """{image index: [material names]} for textures used by *_CLOTH materials
    (base colour + MToon shade multiply)."""
    tex = js.get("textures", [])
    out = {}
    for m in js.get("materials", []):
        name = m.get("name", "")
        if "_CLOTH" not in name:
            continue
        refs = []
        bc = m.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        if bc:
            refs.append(bc["index"])
        mt = m.get("extensions", {}).get("VRMC_materials_mtoon", {})
        if mt.get("shadeMultiplyTexture"):
            refs.append(mt["shadeMultiplyTexture"]["index"])
        for t in refs:
            out.setdefault(tex[t]["source"], [])
            if name not in out[tex[t]["source"]]:
                out[tex[t]["source"]].append(name)
    return out


def shared_with_non_cloth(js):
    """Image indices used by both clothing and non-clothing materials (danger)."""
    cloth = set(clothing_images(js))
    tex = js.get("textures", [])
    bad = set()
    for m in js.get("materials", []):
        if "_CLOTH" in m.get("name", ""):
            continue
        s = json.dumps(m)
        for i in cloth:
            for ti, t in enumerate(tex):
                if t["source"] == i and (f'"index":{ti}' in s.replace(" ", "")):
                    bad.add(i)
    return bad


def replace_images(src, dst, repl):
    """repl: {image index: (bytes, mime)}. Rebuilds BIN with 4-byte alignment."""
    js, binc = read_glb(src)
    used = {bv for im in js["images"] for bv in [im["bufferView"]]}
    new, cur = bytearray(), {}
    for i, bv in enumerate(js["bufferViews"]):
        if i in used and any(js["images"][k]["bufferView"] == i for k in repl):
            k = next(k for k in repl if js["images"][k]["bufferView"] == i)
            data = repl[k][0]
        else:
            o = bv.get("byteOffset", 0)
            data = binc[o:o + bv["byteLength"]]
        new += b"\0" * (-len(new) % 4)
        bv["byteOffset"], bv["byteLength"] = len(new), len(data)
        new += data
    for k, (_, mime) in repl.items():
        js["images"][k]["mimeType"] = mime
    js["buffers"][0]["byteLength"] = len(new) + (-len(new) % 4)
    write_glb(dst, js, bytes(new))


def selfcheck(path, tmp="/tmp/_rt.vrm"):
    a, ab = read_glb(path)
    replace_images(path, tmp, {})
    b, bb = read_glb(tmp)
    for d in (a, b):
        for bv in d["bufferViews"]:
            bv.pop("byteOffset", None)
        d["buffers"][0].pop("byteLength")
    assert a == b, "JSON differs beyond offsets"
    ja, _ = read_glb(path)
    for i in range(len(ja["images"])):
        assert image_bytes(*read_glb(tmp), i) == image_bytes(ja, ab, i), f"image {i}"
    print("selfcheck OK", path)


if __name__ == "__main__":
    cmd, p = sys.argv[1], sys.argv[2]
    js, binc = read_glb(p)
    if cmd == "list":
        for i, mats in clothing_images(js).items():
            print(i, js["images"][i].get("mimeType"), len(image_bytes(js, binc, i)), mats)
        print("shared with non-cloth:", shared_with_non_cloth(js))
    elif cmd == "extract":
        out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        for i in clothing_images(js):
            ext = "png" if "png" in js["images"][i]["mimeType"] else "jpg"
            (out / f"img{i}.{ext}").write_bytes(image_bytes(js, binc, i))
    elif cmd == "selfcheck":
        selfcheck(p)
