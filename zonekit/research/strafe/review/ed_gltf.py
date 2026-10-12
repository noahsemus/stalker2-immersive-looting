import unreal, os
log = []
outdir = os.path.join(SCRATCH, "rev_gltf"); os.makedirs(outdir, exist_ok=True)
for name in ("SK_han_00_a",):
    m = unreal.load_asset("/Game/_STALKER2/SkeletalMeshes/characters/_han/" + name)
    t = unreal.AssetExportTask()
    t.object = m; t.filename = os.path.join(outdir, name + ".gltf"); t.automated = True; t.prompt = False; t.replace_identical = True
    t.exporter = unreal.GLTFSkeletalMeshExporter()
    o = unreal.GLTFExportOptions()
    try:
        o.set_editor_property("export_vertex_skin_weights", True)
    except Exception as e: log.append(f"opt err {e}")
    for p in ("bake_material_inputs", "export_textures", "export_unlit_materials"):
        try: o.set_editor_property(p, False if p != "bake_material_inputs" else unreal.GLTFMaterialBakeMode.DISABLED)
        except Exception as e: log.append(f"opt {p} err {e}")
    t.options = o
    ok = unreal.Exporter.run_asset_export_task(t)
    log.append(f"{name} export {ok} errors {list(t.errors) if hasattr(t,'errors') else ''}")
log.append(str(os.listdir(outdir)))
open(os.path.join(SCRATCH, "rev_gltf.txt"), "w").write("\n".join(log))
