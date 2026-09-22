from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageChops
import json
import os
import random
import colorsys

def create_tee(base_img, color, pattern=None, text=None, text_color=(0,0,0,255), front_rect=None):
    width, height = base_img.size
    
    # Recolor: multiply base with color
    # create a solid color image
    color_img = Image.new("RGBA", (width, height), color)
    # multiply
    result = ImageChops.multiply(base_img, color_img)
    
    draw = ImageDraw.Draw(result)
    
    # Patterns
    if pattern == "stripes":
        # Draw horizontal stripes over the whole shirt
        stripe_color = (255, 255, 255, 100) if random.random() > 0.5 else (0, 0, 0, 100)
        for y in range(0, height, 40):
            if (y // 40) % 2 == 0:
                draw.rectangle([0, y, width, y+20], fill=stripe_color)
    elif pattern == "polka":
        dot_color = (255, 255, 255, 150)
        for y in range(0, height, 60):
            for x in range(0, width, 60):
                offset = 30 if (y // 60) % 2 == 1 else 0
                draw.ellipse([x+offset, y, x+offset+15, y+15], fill=dot_color)
                
    # Text graphics on front_rect
    if text and front_rect:
        u_min = front_rect["u_min"] * width
        u_max = front_rect["u_max"] * width
        v_min_gl = (1.0 - front_rect["v_max"]) * height
        v_max_gl = (1.0 - front_rect["v_min"]) * height
        
        # Center of front chest
        cx = (u_min + u_max) / 2
        cy = (v_min_gl + v_max_gl) / 2
        
        try:
            # Try to load a nice font, fallback to default
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
            
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        draw.text((cx - tw/2, cy - th/2), text, font=font, fill=text_color)
        
    return result

def hsv_to_rgb(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r*255), int(g*255), int(b*255), 255)

def main():
    base_path = "E:/Felt/tools/outfits/base_tee.png"
    if not os.path.exists(base_path):
        print("base_tee.png not found")
        return
        
    base_img = Image.open(base_path).convert("RGBA")
    
    with open("E:/Felt/tools/outfits/tee_uv.json", "r") as f:
        uv_data = json.load(f)
        
    front_rect = uv_data.get("rect_z_pos")
    
    out_dir = "E:/Felt/Assets/tees"
    os.makedirs(out_dir, exist_ok=True)
    
    # 60 variations
    # 1. Colors
    base_colors = {
        "white": (255, 255, 255, 255),
        "black": (60, 60, 60, 255),
        "heather_grey": (180, 180, 180, 255),
        "navy": (30, 40, 80, 255),
        "sage_green": (150, 180, 150, 255),
        "soft_pink": (255, 180, 200, 255),
        "pastel_blue": (180, 220, 255, 255),
        "pastel_yellow": (255, 240, 150, 255)
    }
    
    patterns = [None, "stripes", "polka"]
    
    texts = [
        (None, None),
        ("felt.", (0,0,0,255)),
        ("404 sleep not found", (255,50,50,255)),
        ("gg", (255,255,255,255)),
        ("brb", (100,100,100,255)),
        ("ENDFIELD", (200,200,200,255)),
        ("LOCAL", (0,0,0,255)),
        ("ROUTING", (50,50,150,255))
    ]
    
    count = 0
    # Generate combinations
    for cname, color in base_colors.items():
        for pat in patterns:
            for txt, txt_col in texts:
                # To avoid too many, just pick a subset or randomize
                if count >= 80:
                    break
                    
                # We need some variety
                if pat and txt: 
                    continue # skip text on patterned shirts for cleaner look
                
                name = f"{cname}"
                if pat:
                    name += f"_{pat}"
                if txt:
                    name += f"_txt_{txt.replace(' ', '_')}"
                    
                img = create_tee(base_img, color, pattern=pat, text=txt, text_color=txt_col, front_rect=front_rect)
                img.save(f"{out_dir}/{name}.png")
                count += 1
                
    # Also add seasonal
    img = create_tee(base_img, (255,150,50,255), text="SPOOKY", text_color=(0,0,0,255), front_rect=front_rect)
    img.save(f"{out_dir}/halloween_spooky.png")
    
    img = create_tee(base_img, (200,50,50,255), text="MERRY", text_color=(255,255,255,255), front_rect=front_rect)
    img.save(f"{out_dir}/christmas_merry.png")
    
    print(f"Generated {count+2} tees in {out_dir}")

if __name__ == "__main__":
    main()
