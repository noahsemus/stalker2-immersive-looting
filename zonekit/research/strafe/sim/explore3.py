import os, unreal
out = []
def P(*a): out.append(" ".join(str(x) for x in a))
base = "/Game/_STALKER2/SkeletalMeshes/SK_stalker_Skeleton.SK_stalker_Skeleton:"
for n in ("legs_blend_mask", "left_hand_blend_mask", "legs_and_camera_blend_mask", "under_hips", "lower_body_blend_mask"):
    o = unreal.find_object(None, base + n) or unreal.load_object(None, base + n)
    P("==", n, o)
    if o:
        P("  dir:", [d for d in dir(o) if not d.startswith('_')][:80])
        for pn in ("profile_entries", "mode", "ProfileEntries", "Mode"):
            try: P("  ", pn, o.get_editor_property(pn))
            except Exception as ex: P("  ERR", pn, ex)
coll = None
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_package_name("/Game/_STALKER2/Animations/Player/AnimCollection_fp_bh") or []:
    P("asset", a.asset_class_path, a.package_name)
f = unreal.ARFilter(package_paths=["/Game/_STALKER2"], recursive_paths=True)
import re
res = [a for a in ar.get_assets(unreal.ARFilter(package_paths=["/Game/_STALKER2/Animations"], recursive_paths=True)) if str(a.asset_name) == "AnimCollection_fp_bh"]
for a in res:
    P("coll", a.package_name, a.asset_class_path)
    c = unreal.load_asset(str(a.package_name))
    P(" dir", [d for d in dir(c) if not d.startswith('_')][:100])
open(os.path.join(SCRATCH, "sim_explore3.txt"), "w").write("\n".join(out))
