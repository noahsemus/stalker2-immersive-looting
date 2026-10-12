import unreal, os
log = []
outdir = os.path.join(SCRATCH, "rev_gltf"); os.makedirs(outdir, exist_ok=True)
paths = [l.strip() for l in open(ARGS[0] if ARGS else os.path.join(SCRATCH, "plmeshes.txt")).read().splitlines() if l.strip()]
for p in paths:
    name = p.split("/")[-1]
    m = unreal.load_asset(p)
    t = unreal.AssetExportTask()
    t.object = m; t.filename = os.path.join(outdir, name + ".gltf"); t.automated = True; t.prompt = False; t.replace_identical = True
    t.exporter = unreal.GLTFSkeletalMeshExporter()
    o = unreal.GLTFExportOptions()
    o.set_editor_property("bake_material_inputs", unreal.GLTFMaterialBakeMode.DISABLED)
    t.options = o
    ok = unreal.Exporter.run_asset_export_task(t)
    b = m.get_bounds()
    log.append(f"{name} export {ok} bounds o=({b.origin.x:.0f},{b.origin.y:.0f},{b.origin.z:.0f}) e=({b.box_extent.x:.0f},{b.box_extent.y:.0f},{b.box_extent.z:.0f})")
open(os.path.join(SCRATCH, "rev_gltf2.txt"), "w").write("\n".join(log))
