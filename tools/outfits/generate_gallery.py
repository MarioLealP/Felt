import os
import glob
import json
import socket
import time
import subprocess

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
    tees = glob.glob(os.path.join(tees_dir, "*.png"))
    
    print(f"Found {len(tees)} tees. Generating screenshots...")
    
    for t in tees:
        name = os.path.basename(t).replace(".png", "")
        # send garment
        send_msg({
            "garment": {
                "material": "N00_004_01_Tops_01_CLOTH",
                "albedo": t.replace("\\", "/")
            }
        })
        time.sleep(0.1) # wait for apply
        
        # take screenshot
        send_msg({"screenshot": "gallery_" + name})
        time.sleep(1.5) # wait for Godot timer
        
    print("Done taking screenshots.")
    
    # Build HTML gallery
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Felt Tee Gallery</title>
        <style>
            body { font-family: sans-serif; background: #222; color: #fff; padding: 20px; }
            .grid { display: flex; flex-wrap: wrap; gap: 20px; }
            .card { background: #333; padding: 10px; border-radius: 8px; text-align: center; }
            .card img { max-width: 300px; border-radius: 4px; }
            .controls { margin-bottom: 20px; }
            button { padding: 10px 20px; background: #4caf50; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #45a049; }
        </style>
    </head>
    <body>
        <h1>Tee Gallery Review</h1>
        <div class="controls">
            <button onclick="exportKeepers()">Export Keepers</button>
        </div>
        <div class="grid">
    """
    
    for t in tees:
        name = os.path.basename(t).replace(".png", "")
        img_path = f"file:///E:/Felt/scratch/gallery_{name}.png"
        html += f"""
        <div class="card">
            <img src="{img_path}" />
            <br/>
            <label>
                <input type="checkbox" class="keeper" value="{name}" checked /> Keep <b>{name}</b>
            </label>
        </div>
        """
        
    html += """
        </div>
        <script>
            function exportKeepers() {
                const checkboxes = document.querySelectorAll('.keeper:checked');
                const keepers = Array.from(checkboxes).map(cb => cb.value);
                
                // Create a blob and download
                const blob = new Blob([JSON.stringify(keepers, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'tees_approved.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        </script>
    </body>
    </html>
    """
    
    with open("E:/Felt/scratch/gallery.html", "w") as f:
        f.write(html)
        
    print("Gallery generated at E:/Felt/scratch/gallery.html")

if __name__ == "__main__":
    main()
