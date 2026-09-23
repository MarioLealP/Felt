from PIL import Image, ImageDraw, ImageFont, ImageChops
import json
import os
import glob

def remove_white(img):
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for item in data:
        # If it's mostly white, make it transparent
        if item[0] > 220 and item[1] > 220 and item[2] > 220:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    return img

def create_tee(base_img, color, pattern=None, text=None, text_color=(0,0,0,255), front_rect=None, graphic_path=None):
    width, height = base_img.size
    
    color_img = Image.new("RGBA", (width, height), color)
    result = ImageChops.multiply(base_img, color_img)
    
    draw = ImageDraw.Draw(result)
    
    if pattern == "stripes":
        stripe_color = (255, 255, 255, 100) if color[0] < 100 else (0, 0, 0, 80)
        for y in range(0, height, 40):
            if (y // 40) % 2 == 0:
                draw.rectangle([0, y, width, y+20], fill=stripe_color)
    elif pattern == "polka":
        dot_color = (255, 255, 255, 120) if color[0] < 100 else (0, 0, 0, 80)
        for y in range(0, height, 60):
            for x in range(0, width, 60):
                offset = 30 if (y // 60) % 2 == 1 else 0
                draw.ellipse([x+offset, y, x+offset+15, y+15], fill=dot_color)
                
    if graphic_path and front_rect:
        u_min = front_rect["u_min"] * width
        u_max = front_rect["u_max"] * width
        v_min_gl = (1.0 - front_rect["v_max"]) * height
        v_max_gl = (1.0 - front_rect["v_min"]) * height
        
        cx = int((u_min + u_max) / 2)
        cy = int((v_min_gl + v_max_gl) / 2)
        
        # Load graphic
        g = Image.open(graphic_path).convert("RGBA")
        g = remove_white(g)
        
        # Scale graphic to fit the chest width (with padding)
        target_w = int((u_max - u_min) * 0.7)
        ratio = target_w / g.width
        target_h = int(g.height * ratio)
        g = g.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # If the tee is very dark, the multiply blending won't show black lines.
        # We can just paste it directly using alpha composite, so colors remain.
        # Actually, if we want it to look like fabric, multiply is good, but for dark shirts we need lighter graphics.
        # To keep it simple, we just alpha_composite it on top. 
        # But to keep the fabric shading, we could multiply the shading layer... 
        # Let's just paste it for now, it's a huge step up.
        result.alpha_composite(g, (cx - target_w//2, cy - target_h//2))

    if text and front_rect and not graphic_path:
        u_min = front_rect["u_min"] * width
        u_max = front_rect["u_max"] * width
        v_min_gl = (1.0 - front_rect["v_max"]) * height
        v_max_gl = (1.0 - front_rect["v_min"]) * height
        cx = (u_min + u_max) / 2
        cy = (v_min_gl + v_max_gl) / 2
        try:
            font = ImageFont.truetype("arialbd.ttf", 80)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw/2, cy - th/2), text, font=font, fill=text_color)
        
    return result

def main():
    base_path = "E:/Felt/tools/outfits/base_tee.png"
    if not os.path.exists(base_path):
        return
        
    base_img = Image.open(base_path).convert("RGBA")
    
    with open("E:/Felt/tools/outfits/tee_uv.json", "r") as f:
        uv_data = json.load(f)
        
    front_rect = uv_data.get("rect_z_pos")
    
    out_dir = "E:/Felt/Assets/tees"
    
    # Delete old terrible tees
    for f in glob.glob(f"{out_dir}/*.png"):
        os.remove(f)
    
    base_colors = {
        "white": (255, 255, 255, 255),
        "heather_grey": (180, 180, 180, 255),
        "sage_green": (150, 180, 150, 255),
        "soft_pink": (255, 180, 200, 255),
        "pastel_blue": (180, 220, 255, 255),
        "pastel_yellow": (255, 240, 150, 255),
        "navy": (40, 50, 80, 255),
    }
    
    graphics = {
        "cat": "E:/Felt/tools/outfits/graphics/cat.jpg",
        "endfield": "E:/Felt/tools/outfits/graphics/endfield.jpg",
        "ghost": "E:/Felt/tools/outfits/graphics/ghost.jpg"
    }
    
    patterns = [None, "stripes", "polka"]
    
    count = 0
    # Generate Graphic Tees
    for cname, color in base_colors.items():
        for gname, gpath in graphics.items():
            name = f"{cname}_graphic_{gname}"
            img = create_tee(base_img, color, graphic_path=gpath, front_rect=front_rect)
            img.save(f"{out_dir}/{name}.png")
            count += 1
            
    # Generate Patterned Tees
    for cname, color in base_colors.items():
        for pat in ["stripes", "polka"]:
            name = f"{cname}_{pat}"
            img = create_tee(base_img, color, pattern=pat)
            img.save(f"{out_dir}/{name}.png")
            count += 1
            
    # Generate Cool Text Tees
    texts = [
        ("404", (200,50,50,255)),
        ("ENDFIELD", (40,40,40,255)),
        ("LOCAL", (50,100,150,255))
    ]
    for cname, color in base_colors.items():
        for txt, txt_col in texts:
            # white text on dark shirts
            if color[0] < 100:
                txt_col = (255, 255, 255, 255)
            name = f"{cname}_txt_{txt}"
            img = create_tee(base_img, color, text=txt, text_color=txt_col, front_rect=front_rect)
            img.save(f"{out_dir}/{name}.png")
            count += 1
            
    print(f"Generated {count} amazing tees in {out_dir}")

if __name__ == "__main__":
    main()
