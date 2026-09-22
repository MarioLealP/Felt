import json
import numpy as np
import trimesh

def main():
    path = r"E:\Felt\felt-character-assets\felt-godot-overlay\characters\felt.vrm"
    scene = trimesh.load(path, force="scene", file_type="glb")
    
    # Print out meshes and their materials
    tops_mesh = None
    for name, geom in scene.geometry.items():
        if hasattr(geom.visual, 'material') and geom.visual.material:
            mat_name = geom.visual.material.name
            print(f"Mesh: {name}, Material: {mat_name}")
            if mat_name and "N00_004_01_Tops_01_CLOTH" in mat_name:
                tops_mesh = geom
    
    if tops_mesh is None:
        print("Tops mesh not found via material name.")
        return

    print("Found tops mesh")
    
    # Analyze triangles
    # tops_mesh.vertices, tops_mesh.faces, tops_mesh.face_normals, tops_mesh.visual.uv
    uvs = tops_mesh.visual.uv
    vertices = tops_mesh.vertices
    faces = tops_mesh.faces
    normals = tops_mesh.face_normals
    
    # Calculate bounding box of tops_mesh to estimate heights and widths
    min_x, min_y, min_z = np.min(vertices, axis=0)
    max_x, max_y, max_z = np.max(vertices, axis=0)
    print(f"Tops bounding box: X({min_x:.3f} to {max_x:.3f}), Y({min_y:.3f} to {max_y:.3f}), Z({min_z:.3f} to {max_z:.3f})")
    
    # Let's say torso width is 50% of the total X width (to avoid sleeves)
    width = max_x - min_x
    mid_x = (max_x + min_x) / 2.0
    x_threshold = width * 0.25 # +/- 25% from center
    
    # Height between collarbone and navel (roughly top 20% to top 70% of the tops mesh)
    # Actually, let's look at the actual Y values.
    # The top is usually the collar, the bottom is the hem.
    height = max_y - min_y
    y_top = max_y - height * 0.15 # below collar
    y_bottom = max_y - height * 0.65 # above navel/hem
    
    # Also find Z direction. Usually Z is forward or backward.
    # We can check max_z and min_z.
    
    front_uvs = []
    back_uvs = []
    
    for i, face in enumerate(faces):
        # face center
        center = np.mean(vertices[face], axis=0)
        cx, cy, cz = center
        
        # Check X and Y
        if abs(cx - mid_x) < x_threshold and y_bottom < cy < y_top:
            # Check Z normal
            nz = normals[i][2]
            
            if nz > 0.5: # Pointing +Z
                front_uvs.extend(uvs[face])
            elif nz < -0.5: # Pointing -Z
                back_uvs.extend(uvs[face])
                
    # Unity is +Z forward usually? Or -Z forward?
    # Let's just output both sets and we can see which has more or we can assume front has higher +Z or lower Z.
    print(f"Found {len(front_uvs)//3} front faces, {len(back_uvs)//3} back faces.")
    
    def get_uv_rect(uv_points):
        if not uv_points:
            return None
        pts = np.array(uv_points)
        return {
            "u_min": float(np.min(pts[:, 0])),
            "v_min": float(np.min(pts[:, 1])),
            "u_max": float(np.max(pts[:, 0])),
            "v_max": float(np.max(pts[:, 1]))
        }
        
    rect_z_pos = get_uv_rect(front_uvs)
    rect_z_neg = get_uv_rect(back_uvs)
    
    # Which is front?
    # In GLTF, +Z is usually backward, +Y is up, +X is right.
    # If +Z is backward, then -Z is forward (front).
    # Let's check mean Z of the triangles to confirm.
    if front_uvs and back_uvs:
        # Re-evaluate
        pass

    import json
    out_data = {
        "rect_z_pos": rect_z_pos,
        "rect_z_neg": rect_z_neg
    }
    with open("tee_uv.json", "w") as f:
        json.dump(out_data, f, indent=2)
    print("Saved tee_uv.json")
    
if __name__ == "__main__":
    main()
    
if __name__ == "__main__":
    main()
