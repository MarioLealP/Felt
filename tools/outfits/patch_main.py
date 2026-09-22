import sys

with open("E:/Felt/felt-character-assets/felt-godot-overlay/main.gd", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add garment and screenshot APIs to _handle_tag_line
target_str = """	if parsed.has("expression"):
		_expression_targets = {}
		var expr: Dictionary = parsed["expression"]
		for key in expr:
			_expression_targets[key] = float(expr[key])
		_expression_decay_timer = -1.0  # don't decay while explicitly set"""

replacement_str = target_str + """
	if parsed.has("garment"):
		_apply_garment(parsed["garment"])
	if parsed.has("screenshot"):
		if not _screenshot_started:
			var fname: String = "screenshot"
			if typeof(parsed["screenshot"]) == TYPE_STRING:
				fname = parsed["screenshot"]
			_screenshot_started = true
			_schedule_screenshot(fname)

var _original_garment_materials: Dictionary = {}

func _apply_garment(g: Dictionary) -> void:
	if not character:
		return
	var mat_name: String = g.get("material", "")
	if mat_name.is_empty():
		return
		
	var target_mats: Array[ShaderMaterial] = []
	var meshes: Array = []
	_collect_mesh_instances(character, meshes)
	for child in meshes:
		var mesh_inst := child as MeshInstance3D
		for surf_idx in range(mesh_inst.get_surface_override_material_count()):
			var mat = mesh_inst.get_active_material(surf_idx)
			if mat is ShaderMaterial and mat.resource_name == mat_name:
				if mat not in target_mats:
					target_mats.append(mat)
		if mesh_inst.mesh != null:
			for surf_idx in range(mesh_inst.mesh.get_surface_count()):
				var mat = mesh_inst.mesh.surface_get_material(surf_idx)
				if mat is ShaderMaterial and mat.resource_name == mat_name:
					if mat not in target_mats:
						target_mats.append(mat)
						
	if target_mats.is_empty():
		return
		
	for mat in target_mats:
		if not _original_garment_materials.has(mat):
			_original_garment_materials[mat] = {
				"_MainTex": mat.get_shader_parameter("_MainTex"),
				"_ShadeTexture": mat.get_shader_parameter("_ShadeTexture")
			}
			
	if g.get("reset", false):
		for mat in target_mats:
			var orig = _original_garment_materials[mat]
			mat.set_shader_parameter("_MainTex", orig["_MainTex"])
			mat.set_shader_parameter("_ShadeTexture", orig["_ShadeTexture"])
		return
		
	var albedo_path: String = g.get("albedo", "")
	var shade_path: String = g.get("shade", "")
	
	var albedo_tex: ImageTexture = null
	if not albedo_path.is_empty():
		var img = Image.new()
		var err = img.load(albedo_path)
		if err == OK:
			albedo_tex = ImageTexture.create_from_image(img)
		else:
			print("Failed to load albedo from: ", albedo_path)
			
	var shade_tex: ImageTexture = null
	if not shade_path.is_empty():
		var img = Image.new()
		var err = img.load(shade_path)
		if err == OK:
			shade_tex = ImageTexture.create_from_image(img)
			
	for mat in target_mats:
		if albedo_tex:
			mat.set_shader_parameter("_MainTex", albedo_tex)
		if shade_tex:
			mat.set_shader_parameter("_ShadeTexture", shade_tex)
"""

if target_str in content:
    content = content.replace(target_str, replacement_str)
else:
    print("Could not find target_str")

# 2. Update _schedule_screenshot
target_str2 = """func _schedule_screenshot() -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().create_timer(1.0).timeout
	var img1: Image = get_viewport().get_texture().get_image()
	var ts1: String = Time.get_datetime_string_from_system().replace(":", "-").replace("T", "_") + "_1"
	var path1: String = "E:/Felt/scratch/felt_screenshot_" + ts1 + ".png"
	img1.save_png(path1)
	print("Screenshot 1 saved: ", path1)
	
	await get_tree().create_timer(1.0).timeout
	var img2: Image = get_viewport().get_texture().get_image()
	var ts2: String = Time.get_datetime_string_from_system().replace(":", "-").replace("T", "_") + "_2"
	var path2: String = "E:/Felt/scratch/felt_screenshot_" + ts2 + ".png"
	img2.save_png(path2)
	print("Screenshot 2 saved: ", path2)
	
	get_tree().quit()"""

replacement_str2 = """func _schedule_screenshot(fname: String = "screenshot") -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().create_timer(1.0).timeout
	var img1: Image = get_viewport().get_texture().get_image()
	var path1: String = "E:/Felt/scratch/" + fname + ".png"
	img1.save_png(path1)
	print("Screenshot 1 saved: ", path1)
	_screenshot_started = false"""

if target_str2 in content:
    content = content.replace(target_str2, replacement_str2)
else:
    print("Could not find target_str2")

with open("E:/Felt/felt-character-assets/felt-godot-overlay/main.gd", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched main.gd successfully.")
