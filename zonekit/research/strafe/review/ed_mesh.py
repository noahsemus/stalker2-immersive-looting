import unreal, os
ar = unreal.AssetRegistryHelpers.get_asset_registry()
out = []
flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "SkeletalMesh")], recursive_paths=True, package_paths=["/Game/_STALKER2/SkeletalMeshes", "/Game/_Stalker_2"])
assets = ar.get_assets(flt)
for a in assets:
    n = str(a.asset_name); p = str(a.package_name)
    tags = {}
    try:
        sk = a.get_tag_value("Skeleton")
    except Exception: sk = ""
    if "stalker_Skeleton" in str(sk) or any(s in n.lower() for s in ("player", "hands", "fp_", "_fp", "skif", "arms")):
        out.append(f"{p} | skel={sk}")
open(os.path.join(SCRATCH, "rev_mesh.txt"), "w").write(f"{len(assets)} meshes\n" + "\n".join(sorted(out)))
