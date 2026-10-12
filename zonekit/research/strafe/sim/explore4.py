import os, unreal
out = []
def P(*a): out.append(" ".join(str(x) for x in a))
def exp(obj, fn):
    t = unreal.AssetExportTask()
    t.object = obj; t.filename = fn; t.automated = True; t.prompt = False; t.replace_identical = True
    t.exporter = unreal.ObjectExporterT3D()
    ok = unreal.Exporter.run_asset_export_task(t)
    P("export", obj.get_name(), fn, ok)
base = "/Game/_STALKER2/SkeletalMeshes/SK_stalker_Skeleton.SK_stalker_Skeleton:"
d = os.path.join(SCRATCH, "simexp"); os.makedirs(d, exist_ok=True)
for n in ("legs_blend_mask", "left_hand_blend_mask", "legs_and_camera_blend_mask", "under_hips", "lower_body_blend_mask", "right_hand_blend_mask", "upper_body_blend_mask"):
    o = unreal.find_object(None, base + n)
    if o: exp(o, os.path.join(d, n + ".t3d"))
    else: P("missing", n)
c = unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimCollections/AnimCollection_fp_bh")
exp(c, os.path.join(d, "AnimCollection_fp_bh.t3d"))
open(os.path.join(SCRATCH, "sim_explore4.txt"), "w").write("\n".join(out))
