"""Batch driver.  stage 'restyle': ComfyUI textures (cached).  stage 'assemble': variant VRMs.
Usage: python build_batch.py restyle|assemble [outfit ...]
Env: COMFY_HOST (default 127.0.0.1:18188), FELT_CHAR_DIR, FELT_WORK.
"""
import io, os, sys, time
from pathlib import Path
from PIL import Image
import vrm_textures as vt, recolor

CHARS = Path(os.environ.get("FELT_CHAR_DIR", "/mnt/e/Felt/felt-character-assets/felt-godot-overlay/characters"))
WORK = Path(os.environ.get("FELT_WORK", "/mnt/e/Felt/scratch/outfit-review/work"))
OUTFITS = ["General_1", "LaceDress", "Sport", "NightOuting"]
RESTYLES = {"plaid": "plaid", "floral": "floral"}
PALS = list(recolor.PALETTES)


def tex(outfit):
    """{image idx: PIL RGBA} for clothing textures (skipping fully transparent ones)."""
    js, b = vt.read_glb(CHARS / f"Felt_{outfit}.vrm")
    out = {}
    for i in vt.clothing_images(js):
        im = Image.open(io.BytesIO(vt.image_bytes(js, b, i))).convert("RGBA")
        if im.getchannel("A").getextrema()[1] > 0:
            out[i] = im
    return out


def png(im):
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=False); return buf.getvalue()


def restyle_stage(outfits):
    import comfy_restyle
    host = os.environ.get("COMFY_HOST", "127.0.0.1:18188")
    for o in outfits:
        for i, im in tex(o).items():
            for st in RESTYLES:
                f = WORK / o / f"restyle_{st}" / f"img{i}.png"
                if f.exists():
                    continue
                f.parent.mkdir(parents=True, exist_ok=True)
                t = time.time()
                (WORK / o / "src").mkdir(exist_ok=True); im.save(WORK / o / "src" / f"img{i}.png")
                r = comfy_restyle.restyle(WORK / o / "src" / f"img{i}.png", st, host)
                r.save(f)
                print(f"{o} img{i} {st} {time.time()-t:.0f}s", flush=True)


def assemble_stage(outfits):
    out = CHARS / "variants"; out.mkdir(exist_ok=True)
    for o in outfits:
        src = CHARS / f"Felt_{o}.vrm"
        t = tex(o)
        dom = recolor.dominant_angle(t.values())
        for pal in PALS:
            repl = {i: (png(recolor.recolor(im, pal, dom)), "image/png") for i, im in t.items()}
            vt.replace_images(src, out / f"Felt_{o}__{pal}.vrm", repl)
        for st in RESTYLES:
            fs = {i: WORK / o / f"restyle_{st}" / f"img{i}.png" for i in t}
            if not all(f.exists() for f in fs.values()):
                print("skip (restyle incomplete):", o, st); continue
            repl = {i: (png(Image.open(f)), "image/png") for i, f in fs.items()}
            vt.replace_images(src, out / f"Felt_{o}__{st}.vrm", repl)
        print("assembled", o, flush=True)


if __name__ == "__main__":
    outs = sys.argv[2:] or OUTFITS
    {"restyle": restyle_stage, "assemble": assemble_stage}[sys.argv[1]](outs)
