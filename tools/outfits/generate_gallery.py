import os
import glob
import json
import socket
import time

def send_msg(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", 8765))
        s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
        s.close()
    except Exception as e:
        print("Failed to send:", e)

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

    print("Done taking screenshots. Building HTML...")

    names = [os.path.basename(t).replace(".png", "") for t in tees]
    names_json = json.dumps(names)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Felt Tee Gallery</title>
    <style>
        body {{ background: #222; color: #fff; font-family: sans-serif; margin: 0; padding: 10px; text-align: center; }}
        img {{ max-width: 100%; }}
        button {{ padding: 10px 20px; font-size: 18px; margin: 5px; cursor: pointer; }}
        #keep-checkbox {{ width: 20px; height: 20px; }}
    </style>
</head>
<body>
    <h2 id="progress"></h2>
    <div>
        <button onclick="prev()">&#9664; Prev</button>
        <label><input type="checkbox" id="keep-checkbox" onchange="toggleKeep()" checked /> Keep</label>
        <button onclick="next()">Next &#9654;</button>
        <button onclick="exportKeepers()" style="background:#4caf50;color:#fff;border:none;border-radius:4px;">Export Keepers</button>
    </div>
    <h3 id="tee-name"></h3>
    <img id="main-image" src="" />

    <script>
        const tees = {names_json};
        let currentIndex = 0;
        const keepers = new Set(tees);

        function updateUI() {{
            const name = tees[currentIndex];
            document.getElementById('main-image').src = 'gallery_' + name + '.png';
            document.getElementById('tee-name').innerText = name;
            document.getElementById('keep-checkbox').checked = keepers.has(name);
            document.getElementById('progress').innerText = (currentIndex + 1) + ' / ' + tees.length;
        }}
        function next() {{ if (currentIndex < tees.length - 1) {{ currentIndex++; updateUI(); }} }}
        function prev() {{ if (currentIndex > 0) {{ currentIndex--; updateUI(); }} }}
        function toggleKeep() {{
            const name = tees[currentIndex];
            if (document.getElementById('keep-checkbox').checked) keepers.add(name);
            else keepers.delete(name);
        }}
        function exportKeepers() {{
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([JSON.stringify(Array.from(keepers), null, 2)], {{type:'application/json'}}));
            a.download = 'tees_approved.json';
            a.click();
        }}
        document.addEventListener('keydown', e => {{
            if (e.key === 'ArrowRight') next();
            if (e.key === 'ArrowLeft') prev();
            if (e.key === ' ') {{ e.preventDefault(); document.getElementById('keep-checkbox').checked = !document.getElementById('keep-checkbox').checked; toggleKeep(); }}
        }});
        updateUI();
    </script>
</body>
</html>"""

    with open(os.path.join(scratch_dir, "gallery.html"), "w") as f:
        f.write(html)

    print(f"Gallery generated at {scratch_dir}/gallery.html")

if __name__ == "__main__":
    main()
