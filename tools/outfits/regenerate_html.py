import os
import glob

def main():
    tees_dir = "E:/Felt/Assets/tees"
    tees = glob.glob(os.path.join(tees_dir, "*.png"))
    
    # We will pass the list of names to JS
    names = [os.path.basename(t).replace(".png", "") for t in tees]
    
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
        .image-container-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .image-container {{
            background: #333;
            width: 800px;
            height: 800px;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .image-container img {{
            /* The source image is 1920x1080 with her in the center. 
               We don't want to squish it into 800x800. 
               We scale it up so she's big! */
            width: 1920px;
            height: 1080px;
            min-width: 1920px;
            min-height: 1080px;
            object-fit: none; /* Keep original pixel size */
            transform: scale(2.0) translateY(10%); /* Zoom 2x, shift down slightly if she is at the bottom center */
            transform-origin: center center;
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
    </style>
</head>
<body>
    <h1>Tee Gallery Review</h1>
    
    <div id="progress"></div>
    
    <div class="carousel">
        <button class="nav-btn" onclick="prev()">&#10094;</button>
        <div class="image-container-wrapper">
            <div class="image-container">
                <img id="main-image" src="" />
            </div>
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
        const tees = {names};
        let currentIndex = 0;
        
        // Initialize all to "keep" by default
        const keepers = new Set(tees);

        function updateUI() {{
            const name = tees[currentIndex];
            document.getElementById('main-image').src = 'file:///E:/Felt/scratch/gallery_' + name + '.png';
            document.getElementById('tee-name').innerText = name;
            document.getElementById('keep-checkbox').checked = keepers.has(name);
            document.getElementById('progress').innerText = (currentIndex + 1) + " / " + tees.length;
        }}

        function next() {{
            if (currentIndex < tees.length - 1) {{
                currentIndex++;
                updateUI();
            }}
        }}

        function prev() {{
            if (currentIndex > 0) {{
                currentIndex--;
                updateUI();
            }}
        }}

        function toggleKeep() {{
            const name = tees[currentIndex];
            const checked = document.getElementById('keep-checkbox').checked;
            if (checked) {{
                keepers.add(name);
            }} else {{
                keepers.delete(name);
            }}
        }}

        function exportKeepers() {{
            const keepersArray = Array.from(keepers);
            const blob = new Blob([JSON.stringify(keepersArray, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'tees_approved.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight') next();
            if (e.key === 'ArrowLeft') prev();
            if (e.key === ' ') {{
                // Toggle keep on spacebar
                e.preventDefault();
                document.getElementById('keep-checkbox').checked = !document.getElementById('keep-checkbox').checked;
                toggleKeep();
            }}
        }});

        // Init
        updateUI();
    </script>
</body>
</html>
"""
    with open("E:/Felt/scratch/gallery.html", "w") as f:
        f.write(html)
        
    print("Gallery generated at E:/Felt/scratch/gallery.html")

if __name__ == "__main__":
    main()
