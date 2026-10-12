import unreal, os
ar = unreal.AssetRegistryHelpers.get_asset_registry()
flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimMontage")], recursive_paths=True, package_paths=["/Game/_STALKER2/Animations/Player"])
assets = ar.get_assets(flt)
out = []
for a in assets:
    m = unreal.load_asset(str(a.package_name))
    try:
        slots = [str(t.get_editor_property("slot_name")) for t in m.get_editor_property("slot_anim_tracks")]
    except Exception as e:
        slots = [f"ERR {e}"]
    grp = ""
    try:
        grp = str(m.get_group_name())
    except Exception: pass
    if any(s in ("LeftHand", "DefaultSlot", "CameraSlot", "RightHand", "WeaponSlot") for s in slots):
        out.append(f"{a.package_name} | {','.join(slots)} | {grp}")
open(os.path.join(SCRATCH, "rev_mont.txt"), "w").write(f"{len(assets)} montages\n" + "\n".join(sorted(out)))
