import os, unreal
out = []
AL = unreal.AnimationLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()
def refs(pkg):
    o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
    return [str(x) for x in (ar.get_referencers(pkg, o) or [])]
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")],
                    package_paths=["/Game/_STALKER2/Animations/Player/AnimSequences/bh"], recursive_paths=True)
for a in sorted(ar.get_assets(f), key=lambda a: str(a.package_name)):
    n = str(a.package_name)
    nm = n.rsplit('/',1)[1]
    if any(k in nm.lower() for k in ('walk','run','crouch','idle','strafe','move')):
        s = unreal.load_asset(n)
        try:
            at = s.get_editor_property('additive_anim_type'); bt = s.get_editor_property('ref_pose_type'); rs = s.get_editor_property('ref_pose_seq'); rf = s.get_editor_property('ref_frame_index')
        except Exception as e:
            at = bt = rs = rf = str(e)
        nf = AL.get_num_frames(s); ln = s.get_play_length()
        out.append(f"{n} at={at} ref={bt} refseq={rs.get_path_name() if rs else None} rf={rf} frames={nf} len={ln:.3f} refs={[r.rsplit('/',1)[1] for r in refs(n)][:8]}")
open(os.path.join(SCRATCH, "sim_explore1.txt"), "w").write("\n".join(out))
