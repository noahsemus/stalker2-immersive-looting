import os, json, time, unreal
AL = unreal.AnimationLibrary; APE = unreal.AnimPoseExtensions; LOC = unreal.AnimPoseSpaces.LOCAL
A = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/"
SEQS = {}
for d in ("fl", "fr", "bl", "br", "bwd"):
    SEQS["walk_" + d] = A + f"stand/walk/Additive/AS_fp_bh_walk_{d}_add"
for d in ("fwd", "fl", "fr", "bl", "br", "bwd"):
    SEQS["run_" + d] = A + f"stand/run/Additive/fp_bh_run_{d}_add"
for d in ("fwd", "fl", "fr"):
    SEQS["jog_" + d] = A + f"stand/Jog/AS_fp_bh_jog_{d}"
    SEQS["sprint_" + d] = A + f"stand/sprint/fp_bh_sprint_{d}"
SEQS["turn90r"] = A + "stand/turn_in_place/AS_fp_bh_stand_turn90_r"
SEQS["look_sprint"] = A + "stand/fp_bh_stand_lookvertical_sprint"
def opts():
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW)
    o.set_editor_property("retrieve_additive_as_full_pose", True)
    o.set_editor_property("should_retarget", False)
    return o
idle = unreal.load_asset(A + "stand/fp_bh_idle_stand")
p0 = APE.get_anim_pose_at_frame(idle, 0, opts())
bones = [str(b) for b in APE.get_bone_names(p0)]
out = {"bones": bones, "seqs": {}, "meta": {}}
log = []
for key, path in SEQS.items():
    s = unreal.load_asset(path)
    if s is None:
        # search by name
        log.append(f"missing {path}"); continue
    n = AL.get_num_frames(s)
    out["meta"][key] = {"path": path, "frames": n, "len": s.get_play_length(), "additive": str(s.get_editor_property("additive_anim_type")),
        "refseq": (s.get_editor_property("ref_pose_seq").get_path_name() if s.get_editor_property("ref_pose_seq") else None)}
    frames = list(range(0, n, 2)) if n > 40 else list(range(n))
    fl = []
    for k in frames:
        pose = APE.get_anim_pose_at_frame(s, k, opts())
        r = []
        for b in bones:
            t = APE.get_bone_pose(pose, b, LOC); q = t.rotation; p = t.translation
            r.append([q.x, q.y, q.z, q.w, p.x, p.y, p.z])
        fl.append(r)
    out["seqs"][key] = {"frames": frames, "full": fl}
    log.append(f"{key} {n}")
json.dump(out, open(os.path.join(SCRATCH, "rev_dump2.json"), "w"))
open(os.path.join(SCRATCH, "rev_dump2_log.txt"), "w").write("\n".join(log))
