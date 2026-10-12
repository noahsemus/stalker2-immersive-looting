import os, unreal
out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
def P(*a): out.append(" ".join(str(x) for x in a))
sk = unreal.load_asset("/Game/_STALKER2/SkeletalMeshes/SK_stalker_Skeleton")
for prop in ("blend_profiles",):
    try:
        bps = sk.get_editor_property(prop)
        P("blend_profiles", len(bps))
        for bp in bps:
            P("== profile", bp.get_name())
            for pn in ("mode", "profile_entries"):
                try:
                    v = bp.get_editor_property(pn)
                    if pn == "profile_entries":
                        for e in v:
                            P("   ", e.get_editor_property("bone_reference").get_editor_property("bone_name"), e.get_editor_property("blend_scale"))
                    else: P("  ", pn, v)
                except Exception as ex: P("  ERR", pn, ex)
    except Exception as ex:
        P("ERR", prop, ex)
for bsn in ("BS_fp_bh_walk", "BS_fp_bh_run", "BS_fp_bh_crouch"):
    f = unreal.ARFilter(package_paths=["/Game/_STALKER2/Animations/Player"], recursive_paths=True)
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "BlendSpace")], package_paths=["/Game/_STALKER2/Animations/Player"], recursive_paths=True)
for a in ar.get_assets(f):
    n = str(a.package_name)
    if "fp_bh" not in n: continue
    bs = unreal.load_asset(n)
    P("== BS", n)
    try:
        for i, bp in enumerate(bs.get_editor_property("blend_parameters")):
            P("  axis", i, bp.get_editor_property("display_name"), bp.get_editor_property("min"), bp.get_editor_property("max"))
    except Exception as ex: P("  ERR axes", ex)
    try:
        for s in bs.get_editor_property("sample_data"):
            an = s.get_editor_property("animation"); sv = s.get_editor_property("sample_value")
            P("  sample", an.get_path_name() if an else None, round(sv.x,2), round(sv.y,2), s.get_editor_property("rate_scale"))
    except Exception as ex: P("  ERR samples", ex)
    for pn in ("additive_anim_type", "interpolation_param", "target_weight_interpolation_speed_per_sec", "per_bone_blend"):
        try: P("  ", pn, bs.get_editor_property(pn))
        except Exception as ex: pass
open(os.path.join(SCRATCH, "sim_explore2.txt"), "w").write("\n".join(out))
