"""Headless front render of .vrm/.glb files (bind pose, unlit base colour). Runs on the laptop.
Usage: PYOPENGL_PLATFORM=egl python render_preview.py outdir file.vrm [file.vrm ...]
"""
import os, sys
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
from pathlib import Path
import numpy as np, pyrender, trimesh  # WSL: needs pyopengl>=3.1.9, networkx>=3; GLU/libOpenGL via LD_LIBRARY_PATH (see name_parts.py)

W, H = 512, 1024

# glTF alphaMode MASK (all VRoid skin/clothing) as a real cut-out: pyrender
# has no MASK support - it blends such materials in draw order, and their
# see-through texels still write depth, hiding whatever is drawn after them
# (a combined outfit's shorts "cut" her thighs). So: a copy of pyrender's flat
# shader that discards alpha < 0.5, and MASK materials drawn in the opaque pass.
_SHADERS = Path(__file__).parent / ".preview_shaders"


def _mask_shaders():
    src = Path(pyrender.__file__).parent / "shaders"
    _SHADERS.mkdir(exist_ok=True)
    for f in src.iterdir():
        text = f.read_text()
        if f.name == "flat.frag":
            text = text.replace("frag_color = clamp(base_color, 0.0, 1.0);",
                                "if (base_color.a < 0.5) discard;\n    frag_color = clamp(vec4(base_color.rgb, 1.0), 0.0, 1.0);")
        (_SHADERS / f.name).write_text(text)
    return str(_SHADERS)


def render_views(path, frame=None, size=(W, H), backs=(False, True), pad=1.05):
    """Front/back renders (RGB arrays) of one model, loaded once. `frame`
    (lo, hi) world bounds to fit instead of the whole model."""
    w, h = size
    scene = trimesh.load(path, file_type="glb", force="scene")
    slo, shi = scene.bounds
    lo, hi = (np.asarray(frame[0]), np.asarray(frame[1])) if frame is not None else (slo, shi)
    c, ext = (lo + hi) / 2, hi - lo
    ps = pyrender.Scene.from_trimesh_scene(scene, bg_color=[0.93, 0.93, 0.95, 1], ambient_light=[1, 1, 1])
    for m in ps.meshes:
        for p in m.primitives:
            p.material.alphaMode = "OPAQUE"
            p._is_transparent = None
    ymag = max(ext[1] / 2, ext[0] / 2 * h / w) * pad   # fit height and width
    cam = pyrender.OrthographicCamera(xmag=ymag * w / h, ymag=ymag)
    cam_node = ps.add(cam, pose=np.eye(4))
    r = pyrender.OffscreenRenderer(w, h)
    from pyrender.shader_program import ShaderProgramCache
    r._renderer._program_cache = ShaderProgramCache(shader_dir=_mask_shaders())
    out = []
    for back in backs:
        pose = np.eye(4); pose[:3, 3] = [c[0], c[1], shi[2] + 5]      # in front (+Z), looking -Z
        if back:  # behind (-Z), looking +Z
            pose[:3, :3] = np.diag([-1.0, 1.0, -1.0]); pose[2, 3] = slo[2] - 5
        ps.set_pose(cam_node, pose)
        img, _ = r.render(ps, flags=pyrender.RenderFlags.FLAT)
        out.append(img)
    r.delete()
    return out


def render(path, out, back=False):
    from PIL import Image
    Image.fromarray(render_views(path, backs=(back,))[0]).save(out)


if __name__ == "__main__":
    od = Path(sys.argv[1]); od.mkdir(parents=True, exist_ok=True)
    for f in sys.argv[2:]:
        render(f, od / (Path(f).stem + ".png"))
        if os.environ.get("PREVIEW_BACK"):
            render(f, od / (Path(f).stem + "_back.png"), back=True)
        print("ok", f, flush=True)
