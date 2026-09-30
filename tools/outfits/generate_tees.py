"""Generate tee graphic prints via ComfyUI on the Nitro5, then composite
them onto the base tee texture using the UV-mapped print areas.

This replaces the bad PIL-only generation that produced garbage stripes/dots.
"""
import json
import os
import time
import urllib.request
import uuid
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops

# The laptop's ComfyUI - from the environment, never an IP in the repo (Mario's rule).
COMFYUI_URL = os.environ["FELT_COMFYUI_URL"]
TEES_DIR = Path("E:/Felt/Assets/tees")
TOOLS_DIR = Path("E:/Felt/tools/outfits")
BASE_TEE = TOOLS_DIR / "base_tee.png"
UV_JSON = TOOLS_DIR / "tee_uv.json"
GRAPHICS_DIR = TOOLS_DIR / "graphics"

# ── ComfyUI API helpers ──────────────────────────────────────────────

def queue_prompt(workflow: dict) -> str:
    """Submit a workflow to ComfyUI API, return the prompt_id."""
    p = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=p,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 120) -> dict:
    """Poll until the prompt finishes. Return the output info."""
    start = time.time()
    while time.time() - start < timeout:
        resp = urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        history = json.loads(resp.read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"ComfyUI prompt {prompt_id} didn't finish in {timeout}s")


def download_image(filename: str, subfolder: str, out_path: Path):
    """Download a generated image from ComfyUI."""
    url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
    urllib.request.urlretrieve(url, str(out_path))


def make_workflow(prompt: str, negative: str = "", width: int = 1024, height: int = 1024, seed: int = 0) -> dict:
    """Build an SDXL txt2img workflow dict for ComfyUI API."""
    if seed == 0:
        seed = int.from_bytes(os.urandom(4), "big")
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1],
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative or "photo, realistic, blurry, text, watermark, logo, worst quality, low quality",
                "clip": ["1", 1],
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": 25,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "tee_print"},
        },
    }


# ── Graphic print prompts ────────────────────────────────────────────

PRINT_PROMPTS = [
    ("cat", "flat vector t-shirt print, cute anime cat sitting, chibi, minimal, 2 colours, solid white background, centered, no text, simple"),
    ("ghost", "flat vector t-shirt print, cute kawaii ghost, halloween, minimal, simple shape, solid white background, centered, no text"),
    ("pumpkin", "flat vector t-shirt print, cute jack-o-lantern pumpkin, halloween, minimal, solid white background, centered, no text"),
    ("snowflake", "flat vector t-shirt print, geometric snowflake, winter, minimal, solid white background, centered, no text"),
    ("star", "flat vector t-shirt print, cute shooting star with trail, minimal, solid white background, centered, no text"),
    ("heart", "flat vector t-shirt print, cute pixel heart, 8bit retro style, minimal, solid white background, centered, no text"),
    ("moon", "flat vector t-shirt print, crescent moon with small stars, night sky, minimal, solid white background, centered, no text"),
    ("sakura", "flat vector t-shirt print, cherry blossom branch, japanese style, minimal, pink, solid white background, centered, no text"),
    ("endfield_emblem", "flat vector t-shirt print, technical geometric sci-fi military emblem, hexagonal, Arknights Endfield aesthetic, minimal, solid white background, centered, no text"),
    ("endfield_circuit", "flat vector t-shirt print, abstract circuit board pattern forming a diamond shape, sci-fi, minimal, solid white background, centered, no text"),
    ("coffee", "flat vector t-shirt print, cute coffee cup with steam, kawaii face, minimal, solid white background, centered, no text"),
    ("gamepad", "flat vector t-shirt print, retro game controller, pixel art style, minimal, solid white background, centered, no text"),
]


def generate_graphics():
    """Generate graphic prints via ComfyUI."""
    GRAPHICS_DIR.mkdir(exist_ok=True)
    
    for name, prompt in PRINT_PROMPTS:
        out = GRAPHICS_DIR / f"{name}.png"
        if out.exists():
            print(f"  skip {name} (already exists)")
            continue
        
        print(f"  generating {name}...")
        workflow = make_workflow(prompt, width=1024, height=1024)
        try:
            pid = queue_prompt(workflow)
            result = wait_for_prompt(pid, timeout=180)
            
            # Find the output image
            outputs = result.get("outputs", {})
            for node_id, node_out in outputs.items():
                if "images" in node_out:
                    img_info = node_out["images"][0]
                    download_image(img_info["filename"], img_info.get("subfolder", ""), out)
                    print(f"    saved {out}")
                    break
        except Exception as e:
            print(f"    FAILED: {e}")


# ── Compositing ──────────────────────────────────────────────────────

def remove_background(img: Image.Image, threshold: int = 230) -> Image.Image:
    """Make near-white pixels transparent."""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (255, 255, 255, 0)
    return img


def composite_graphic(base: Image.Image, graphic_path: Path, front_rect: dict) -> Image.Image:
    """Paste a graphic onto the front chest area of the tee texture."""
    result = base.copy()
    w, h = result.size
    
    g = Image.open(graphic_path).convert("RGBA")
    g = remove_background(g)
    
    # UV rect → pixel rect
    u_min = front_rect["u_min"] * w
    u_max = front_rect["u_max"] * w
    v_min = (1.0 - front_rect["v_max"]) * h
    v_max = (1.0 - front_rect["v_min"]) * h
    
    cx = int((u_min + u_max) / 2)
    cy = int((v_min + v_max) / 2)
    
    # Scale graphic to 70% of the chest width
    target_w = int((u_max - u_min) * 0.7)
    ratio = target_w / g.width
    target_h = int(g.height * ratio)
    g = g.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Alpha-composite onto the tee
    result.alpha_composite(g, (cx - target_w // 2, cy - target_h // 2))
    return result


def recolor_base(base: Image.Image, color: tuple) -> Image.Image:
    """Multiply-blend the base white tee with a colour."""
    color_layer = Image.new("RGBA", base.size, color)
    return ImageChops.multiply(base, color_layer)


# ── Main generation ──────────────────────────────────────────────────

BASE_COLORS = {
    "white": (255, 255, 255, 255),
    "heather_grey": (190, 190, 190, 255),
    "black": (50, 50, 50, 255),
    "navy": (35, 45, 80, 255),
    "sage_green": (150, 180, 150, 255),
    "soft_pink": (255, 185, 200, 255),
    "pastel_blue": (185, 220, 255, 255),
    "pastel_yellow": (255, 240, 155, 255),
}

TEXT_PRINTS = [
    ("felt", "felt.", (0, 0, 0, 200)),
    ("404", "404 sleep\nnot found", (200, 50, 50, 255)),
    ("gg", "gg", (255, 255, 255, 200)),
    ("brb", "brb", (100, 100, 100, 200)),
]


def make_text_tee(base: Image.Image, text: str, text_color: tuple, front_rect: dict) -> Image.Image:
    """Render text onto the chest area."""
    result = base.copy()
    draw = ImageDraw.Draw(result)
    w, h = result.size
    
    u_min = front_rect["u_min"] * w
    u_max = front_rect["u_max"] * w
    v_min = (1.0 - front_rect["v_max"]) * h
    v_max = (1.0 - front_rect["v_min"]) * h
    cx = (u_min + u_max) / 2
    cy = (v_min + v_max) / 2
    
    # Auto-invert text on dark shirts
    bg_sample = result.getpixel((int(cx), int(cy)))
    if bg_sample[0] < 100 and bg_sample[1] < 100 and bg_sample[2] < 100:
        text_color = (255, 255, 255, 200)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 72)
    except OSError:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2, cy - th / 2), text, font=font, fill=text_color)
    return result


def main():
    # Step 1: Generate graphics via ComfyUI
    print("=== Generating graphic prints via ComfyUI on Nitro5 ===")
    generate_graphics()
    
    # Step 2: Load base texture and UV data
    base = Image.open(BASE_TEE).convert("RGBA")
    with open(UV_JSON) as f:
        uv = json.load(f)
    front_rect = uv["rect_z_pos"]
    
    # Clean old tees
    for old in TEES_DIR.glob("*.png"):
        old.unlink()
    TEES_DIR.mkdir(exist_ok=True)
    
    count = 0
    
    # Step 3: Graphic tees — every color × every graphic
    available_graphics = sorted(GRAPHICS_DIR.glob("*.png"))
    print(f"\n=== Compositing {len(available_graphics)} graphics × {len(BASE_COLORS)} colours ===")
    for cname, color in BASE_COLORS.items():
        colored = recolor_base(base, color)
        for gpath in available_graphics:
            gname = gpath.stem
            out = TEES_DIR / f"{cname}_{gname}.png"
            img = composite_graphic(colored, gpath, front_rect)
            img.save(out)
            count += 1
    
    # Step 4: Plain colour tees (just the recolour, no print)
    print(f"\n=== Plain colour tees ===")
    for cname, color in BASE_COLORS.items():
        colored = recolor_base(base, color)
        colored.save(TEES_DIR / f"{cname}_plain.png")
        count += 1
    
    # Step 5: Text tees
    print(f"\n=== Text tees ===")
    for cname, color in BASE_COLORS.items():
        colored = recolor_base(base, color)
        for tname, text, tcol in TEXT_PRINTS:
            out = TEES_DIR / f"{cname}_txt_{tname}.png"
            img = make_text_tee(colored, text, tcol, front_rect)
            img.save(out)
            count += 1
    
    print(f"\n=== Done: {count} tees in {TEES_DIR} ===")


if __name__ == "__main__":
    main()
