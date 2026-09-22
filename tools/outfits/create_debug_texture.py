from PIL import Image, ImageDraw
import json

def main():
    with open("tee_uv.json", "r") as f:
        data = json.load(f)
        
    width = 2048
    height = 2048
    
    # original white texture
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # VRoid UVs: V axis is usually bottom-to-top, but PIL is top-to-bottom.
    # Let's paint both and see.
    for name, rect in data.items():
        if rect:
            u_min = rect["u_min"] * width
            u_max = rect["u_max"] * width
            
            # Try OpenGL standard (V from bottom)
            v_min_gl = (1.0 - rect["v_max"]) * height
            v_max_gl = (1.0 - rect["v_min"]) * height
            
            # Or DirectX standard (V from top)
            v_min_dx = rect["v_min"] * height
            v_max_dx = rect["v_max"] * height
            
            # Let's paint the GL one Red, DX one Blue
            color = (255, 0, 0, 255) if name == "rect_z_neg" else (0, 255, 0, 255) 
            # I will paint both with different colors to test which is front/back
            # z_neg = red, z_pos = green
            draw.rectangle([u_min, v_min_gl, u_max, v_max_gl], fill=color)
            
            # To be safe, draw a small marker for the "top" of the rect in black
            draw.rectangle([u_min, v_min_gl, u_max, v_min_gl + 20], fill=(0,0,0,255))
            
    img.save("debug_tee.png")
    print("Saved debug_tee.png")

if __name__ == "__main__":
    main()
