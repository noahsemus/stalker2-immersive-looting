import os, time, unreal
AL = unreal.AnimationLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()
t0 = time.time(); out = []; n = 0
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")], package_paths=["/Game/_STALKER2/Animations/Player"], recursive_paths=True)
assets = ar.get_assets(f)
out.append(f"{len(assets)} sequences")
for a in assets:
    tags = None
    try:
        s = unreal.load_asset(str(a.package_name)); n += 1
        cn = [str(c) for c in AL.get_animation_curve_names(s, unreal.RawCurveTrackTypes.RCT_FLOAT)]
        hit = [c for c in cn if "Moving" in c or "UpperBody" in c]
        if hit: out.append(f"{a.package_name}: {hit}")
    except Exception as e:
        out.append(f"ERR {a.package_name} {e}")
    if time.time() - t0 > 500: out.append("TIMEOUT"); break
out.append(f"scanned {n} in {time.time()-t0:.0f}s")
open(os.path.join(SCRATCH, "sim_curvescan.txt"), "w").write("\n".join(out))
