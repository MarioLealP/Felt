import os
import glob
import json
import socket
import time
from PIL import Image

def send_msg(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", 8765))
        s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
        s.close()
    except Exception as e:
        print("Failed to send:", e)

def crop_to_character(img_path):
    """Crop the ultrawide screenshot to just the center where she stands."""
    img = Image.open(img_path)
    w, h = img.size
    # She's centered horizontally, stands on the bottom half.
    # Crop a vertical strip from the center, ~30% of the width.
    crop_w = int(w * 0.20)
    left = (w - crop_w) // 2
    right = left + crop_w
    # Keep full height
    cropped = img.crop((left, 0, right, h))
    cropped.save(img_path)

def main():
    tees_dir = "E:/Felt/Assets/tees"
    scratch_dir = "E:/Felt/scratch"
    tees = sorted(glob.glob(os.path.join(tees_dir, "*.png")))

    print(f"Found {len(tees)} tees. Generating screenshots...")

    for t in tees:
        name = os.path.basename(t).replace(".png", "")
        send_msg({
            "garment": {
                "material": "N00_004_01_Tops_01_CLOTH",
                "albedo": t.replace("\\", "/")
            }
        })
        time.sleep(0.1)
        send_msg({"screenshot": "gallery_" + name})
        time.sleep(1.5)

    print("Done taking screenshots. Cropping to character...")

    # Crop all gallery screenshots to just the character
    for t in tees:
        name = os.path.basename(t).replace(".png", "")
        img_path = os.path.join(scratch_dir, f"gallery_{name}.png")
        if os.path.exists(img_path):
            crop_to_character(img_path)

    print("Cropped. Building HTML...")

    names = [os.path.basename(t).replace(".png", "") for t in tees]
    names_json = json.dumps(names)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Felt Tee Gallery</title>
    <style>
        body {{ font-family: sans-serif; background: #222; color: #fff; display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        h1 {{ margin-top: 0; }}
        .carousel {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-top: 20px;
        }}
        .image-container {{
            background: #333;
            border-radius: 8px;
            text-align: center;
        }}
        .image-container img {{
            height: 85vh;
            border-radius: 8px;
        }}
        .nav-btn {{
            background: #555;
            color: white;
            border: none;
            padding: 20px 30px;
            font-size: 24px;
            border-radius: 8px;
            cursor: pointer;
            user-select: none;
        }}
        .nav-btn:hover {{ background: #777; }}
        .controls {{
            margin-top: 20px;
            display: flex;
            gap: 20px;
            align-items: center;
            font-size: 20px;
        }}
        .checkbox-container {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        input[type="checkbox"] {{
            width: 24px;
            height: 24px;
            cursor: pointer;
        }}
        .export-btn {{
            padding: 10px 20px;
            background: #4caf50;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 18px;
        }}
        .export-btn:hover {{ background: #45a049; }}
        #progress {{ margin-bottom: 10px; font-size: 18px; color: #ccc; }}
        h2 {{ margin: 8px 0 0 0; }}
    </style>
</head>
<body>
    <h1>Tee Gallery Review</h1>
    <div id="progress"></div>

    <div class="carousel">
        <button class="nav-btn" onclick="prev()">&#10094;</button>
        <div class="image-container">
            <img id="main-image" src="" />
            <h2 id="tee-name"></h2>
        </div>
        <button class="nav-btn" onclick="next()">&#10095;</button>
    </div>

    <div class="controls">
        <label class="checkbox-container">
            <input type="checkbox" id="keep-checkbox" onchange="toggleKeep()" />
            Keep this tee
        </label>
        <button class="export-btn" onclick="exportKeepers()">Export Keepers</button>
    </div>

    <script>
        const tees = {names_json};
        let currentIndex = 0;
        const keepers = new Set(tees);

        function updateUI() {{
            const name = tees[currentIndex];
            document.getElementById('main-image').src = 'gallery_' + name + '.png?' + Date.now();
            document.getElementById('tee-name').innerText = name;
            document.getElementById('keep-checkbox').checked = keepers.has(name);
            document.getElementById('progress').innerText = (currentIndex + 1) + " / " + tees.length;
        }}

        function next() {{
            if (currentIndex < tees.length - 1) {{ currentIndex++; updateUI(); }}
        }}

        function prev() {{
            if (currentIndex > 0) {{ currentIndex--; updateUI(); }}
        }}

        function toggleKeep() {{
            const name = tees[currentIndex];
            if (document.getElementById('keep-checkbox').checked) {{
                keepers.add(name);
            }} else {{
                keepers.delete(name);
            }}
        }}

        function exportKeepers() {{
            const blob = new Blob([JSON.stringify(Array.from(keepers), null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'tees_approved.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight') next();
            if (e.key === 'ArrowLeft') prev();
            if (e.key === ' ') {{ e.preventDefault(); document.getElementById('keep-checkbox').checked = !document.getElementById('keep-checkbox').checked; toggleKeep(); }}
        }});

        updateUI();
    </script>
</body>
</html>
"""
    with open(os.path.join(scratch_dir, "gallery.html"), "w") as f:
        f.write(html)

    print(f"Gallery generated at {scratch_dir}/gallery.html")

if __name__ == "__main__":
    main()
