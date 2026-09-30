"""SD1.5 (meinamix) img2img + lineart-anime ControlNet (SDXL variant tripped the RAM guard; see report) restyle of one clothing texture via ComfyUI HTTP API.

restyle(png_path, style, host) -> RGBA PIL image at the ORIGINAL size.
Only originally-opaque pixels (alpha > 0) change; alpha and transparent-pixel RGB stay original.
Fully opaque textures are replaced whole (nothing to mask).
"""
import io, json, time, uuid, urllib.request
import numpy as np
from PIL import Image

STYLES = {
    "plaid": "plaid tartan fabric pattern, flat texture",
    "floral": "floral print fabric pattern, flat texture",
}
NEG = "person, face, text, watermark, blurry"


def _http(host, path, data=None, headers=None):
    req = urllib.request.Request(f"http://{host}{path}", data=data, headers=headers or {})
    return urllib.request.urlopen(req, timeout=600).read()


def _upload(host, img, name):
    b = uuid.uuid4().hex
    buf = io.BytesIO(); img.save(buf, "PNG")
    body = (f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
            f'Content-Type: image/png\r\n\r\n').encode() + buf.getvalue() + \
           (f'\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n').encode()
    _http(host, "/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={b}"})


def _workflow(name, prompt, seed, denoise=0.45):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "meinamix_v11.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
        "4": {"class_type": "LoadImage", "inputs": {"image": name}},
        "5": {"class_type": "AnimeLineArtPreprocessor", "inputs": {"image": ["4", 0], "resolution": 768}},
        "6": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "control_v11p_sd15s2_lineart_anime_fp16.safetensors"}},
        "7": {"class_type": "ControlNetApplyAdvanced", "inputs": {
            "positive": ["2", 0], "negative": ["3", 0], "control_net": ["6", 0], "image": ["5", 0],
            "strength": 0.8, "start_percent": 0.0, "end_percent": 1.0, "vae": ["1", 2]}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}},
        "9": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["7", 0], "negative": ["7", 1], "latent_image": ["8", 0],
            "seed": seed, "steps": 25, "cfg": 7.0, "sampler_name": "euler_ancestral",
            "scheduler": "normal", "denoise": denoise}},
        "10": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["1", 2]}},
        "11": {"class_type": "SaveImage", "inputs": {"images": ["10", 0], "filename_prefix": "outfit_restyle"}},
    }


def free(host):
    _http(host, "/free", json.dumps({"unload_models": True, "free_memory": True}).encode(),
          {"Content-Type": "application/json"})
    time.sleep(5)


class GuardAbort(Exception):
    pass


STATS = {"min_mem_gb": 1e9, "max_vram_mb": 0}


def sample():
    """(MemAvailable GB, GPU used MiB) on the laptop; updates STATS."""
    import subprocess
    o = subprocess.run(["ssh", "clockmost-nitro5", "bash", "-c",
                        "'awk \"/MemAvailable/{print \\$2}\" /proc/meminfo; "
                        "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits'"],
                       capture_output=True, text=True, timeout=60).stdout.split()
    m, g = int(o[0]) / 1048576, int(o[1])
    STATS["min_mem_gb"] = min(STATS["min_mem_gb"], m); STATS["max_vram_mb"] = max(STATS["max_vram_mb"], g)
    return m, g


def guard():
    t = time.time()
    while True:
        m, g = sample()
        if m >= 4 and g <= 5120:
            return
        if time.time() - t > 120:
            raise GuardAbort(f"MemAvailable={m:.1f}GB gpu={g}MiB")
        time.sleep(10)


def restyle(path, style, host="127.0.0.1:18188", seed=1234):
    orig = Image.open(path).convert("RGBA")
    arr = np.array(orig)
    op = arr[..., 3] > 0
    if not op.any():
        return None  # fully transparent texture: nothing to restyle
    # generation input: transparent pixels filled with the mean opaque colour
    gen = arr[..., :3].copy()
    gen[~op] = arr[..., :3][op].mean(0).astype(np.uint8)
    w, h = orig.size
    s = 768 / max(w, h)
    gw, gh = max(64, round(w * s / 8) * 8), max(64, round(h * s / 8) * 8)
    name = f"ov_{uuid.uuid4().hex[:8]}.png"
    _upload(host, Image.fromarray(gen).resize((gw, gh), Image.LANCZOS), name)
    guard()
    pid = json.loads(_http(host, "/prompt", json.dumps(
        {"prompt": _workflow(name, STYLES[style], seed)}).encode(),
        {"Content-Type": "application/json"}))["prompt_id"]
    while True:
        hist = json.loads(_http(host, f"/history/{pid}"))
        if pid in hist:
            break
        time.sleep(5)
        if sample()[0] < 3:
            raise GuardAbort("MemAvailable < 3GB during job")
    if "11" not in hist[pid]["outputs"]:
        raise RuntimeError(json.dumps(hist[pid].get("status"))[:800])
    outs = hist[pid]["outputs"]["11"]["images"][0]
    free(host)
    res = Image.open(io.BytesIO(_http(host, f"/view?filename={outs['filename']}&subfolder={outs['subfolder']}&type={outs['type']}"))).convert("RGB")
    res = np.array(res.resize((w, h), Image.LANCZOS))
    out = arr.copy()
    out[op, :3] = res[op]          # only originally-opaque pixels change
    return Image.fromarray(out, "RGBA")
