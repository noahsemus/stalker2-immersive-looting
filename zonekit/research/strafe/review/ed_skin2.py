import unreal, os
log = []
m = unreal.load_asset("/Game/_STALKER2/SkeletalMeshes/characters/_han/SK_han_00_a")
log.append("SkeletalMesh: " + ", ".join(x for x in dir(m) if not x.startswith("_") and any(k in x.lower() for k in ("vert", "skin", "weight", "lod", "mesh_desc", "bound", "section", "material"))))
ss = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
log.append("Subsystem: " + ", ".join(x for x in dir(ss) if not x.startswith("_")))
log.append("Exporters: " + ", ".join(x for x in dir(unreal) if "Export" in x and ("Skel" in x or "GLTF" in x or "Obj" in x or "Fbx" in x)))
try:
    b = m.get_bounds(); log.append(f"bounds origin {b.origin} extent {b.box_extent}")
except Exception as e: log.append(f"bounds err {e}")
try:
    log.append(f"materials {[str(x.material_slot_name) + ':' + (x.material_interface.get_path_name() if x.material_interface else '') for x in m.materials]}")
except Exception as e: log.append(f"mat err {e}")
try:
    log.append(f"num verts lod0 {ss.get_num_verts(m, 0)} sections {ss.get_num_sections(m, 0) if hasattr(ss,'get_num_sections') else ''}")
except Exception as e: log.append(f"nv err {e}")
open(os.path.join(SCRATCH, "rev_skin2.txt"), "w").write("\n".join(log))
