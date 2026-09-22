from pygltflib import GLTF2
from PIL import Image
import io

def main():
    path = r"E:\Felt\felt-character-assets\felt-godot-overlay\characters\felt.vrm"
    # copy to temp .glb
    import shutil
    import os
    glb_path = "temp_felt.glb"
    shutil.copy(path, glb_path)
    gltf = GLTF2().load(glb_path)
    os.remove(glb_path)
    
    # Find material
    mat = None
    for m in gltf.materials:
        if m.name and "N00_004_01_Tops_01_CLOTH" in m.name:
            mat = m
            break
            
    if not mat:
        print("Material not found")
        return
        
    tex_idx = mat.pbrMetallicRoughness.baseColorTexture.index
    img_idx = gltf.textures[tex_idx].source
    img_info = gltf.images[img_idx]
    
    buffer_view_idx = img_info.bufferView
    buffer_view = gltf.bufferViews[buffer_view_idx]
    
    data = gltf.get_data_from_buffer_uri(gltf.buffers[buffer_view.buffer].uri)
    if data is None:
        # For glb, it's in the binary blob
        # The first buffer's uri might be None, in which case we need the binary_blob
        with open(path, "rb") as f:
            # Skip JSON chunk to get to BIN chunk
            # Actually pygltflib has a helper for glb
            pass
            
    # Or just use the already loaded gltf
    img_data = gltf.get_data_from_buffer_uri(str(buffer_view.buffer)) # sometimes works?
    
    # Pygltflib 1.16 provides gltf._glb_data for the binary chunk
    if hasattr(gltf, '_glb_data'):
        img_data = gltf._glb_data[buffer_view.byteOffset:buffer_view.byteOffset + buffer_view.byteLength]
    else:
        print("No glb data found.")
        return
        
    img = Image.open(io.BytesIO(img_data))
    img.save("base_tee.png")
    print("Saved base_tee.png", img.size)
    
if __name__ == "__main__":
    main()
