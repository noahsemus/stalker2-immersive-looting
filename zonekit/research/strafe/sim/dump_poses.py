"""Read-only: dump local bone transforms of the animations the simulator needs to JSON (SCRATCH/simdump.json)."""
import os, json, time, unreal
AL = unreal.AnimationLibrary
APE = unreal.AnimPoseExtensions
LOC = unreal.AnimPoseSpaces.LOCAL
t0 = time.time()
log = []
A = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/"
SEQS = {
    "idle": A + "stand/fp_bh_idle_stand",
    "idle_crouch": A + "crouch/fp_bh_idle_crouch",
    "idle_lowcrouch": A + "lowcrouch/fp_bh_idle_lowcrouch",
    "walk_left": A + "stand/walk/Additive/AS_fp_bh_walk_left_add",
    "walk_right": A + "stand/walk/Additive/AS_fp_bh_walk_right_add",
    "walk_fwd": A + "stand/walk/Additive/AS_fp_bh_walk_fwd_add",
    "run_left": A + "stand/run/Additive/fp_bh_run_left_add",
    "run_right": A + "stand/run/Additive/fp_bh_run_right_add",
    "lowcrouch_left": A + "lowcrouch/move/Additive/fp_bh_lowcrouch_left_add",
    "lowcrouch_right": A + "lowcrouch/move/Additive/fp_bh_lowcrouch_right_add",
    "crouch_left": A + "crouch/move/Additive/fp_bh_crouch_left_add",
    "crouch_right": A + "crouch/move/Additive/fp_bh_crouch_right_add",
    "look": A + "stand/fp_bh_stand_lookvertical_idle",
    "look_lowcrouch": A + "lowcrouch/AS_fp_bh_lowcrouch_lookvertical",
    "idle_long": A + "idle/AS_fp_bh_stand_idle_long",
    "grab": "/ImmersiveLooting/Runtime/AS_ImmLoot_GrabBHAdd",
    "grab_crouch": "/ImmersiveLooting/Runtime/AS_ImmLoot_GrabBHAddCrouch",
}
SEG2 = 45
GRAB_SEGS = [44, 66, 6 * 19 + 6]          # (elev -50, az 0), (elev -35, az 15), (elev +10, az 0)
GRAB_FR = [0, 6, 12, 15, 20, 24, 30]


def opts(full=True, raw=True):
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW if raw else unreal.AnimDataEvalType.COMPRESSED)
    o.set_editor_property("retrieve_additive_as_full_pose", full)
    o.set_editor_property("should_retarget", False)
    return o


def pose_list(pose, bones):
    r = []
    for b in bones:
        t = APE.get_bone_pose(pose, b, LOC)
        q = t.rotation; p = t.translation; s = t.scale3d
        r.append([q.x, q.y, q.z, q.w, p.x, p.y, p.z, s.x, s.y, s.z])
    return r


idle = unreal.load_asset(SEQS["idle"])
p0 = APE.get_anim_pose_at_frame(idle, 0, opts())
bones = [str(b) for b in APE.get_bone_names(p0)]
parents = []
for b in bones:
    path = [str(x) for x in AL.find_bone_path_to_root(idle, b)]
    parents.append(bones.index(path[1]) if len(path) > 1 and path[1] in bones else -1)
out = {"bones": bones, "parents": parents, "seqs": {}, "meta": {}}
sk = idle.get_editor_property("skeleton")
try:
    out["refpose"] = pose_list(APE.get_reference_pose(sk), bones)
except Exception as e:
    log.append(f"refpose ERR {e}")
for key, path in SEQS.items():
    s = unreal.load_asset(path)
    if s is None:
        log.append(f"missing {path}"); continue
    n = AL.get_num_frames(s)
    meta = {"path": path, "frames": n, "len": s.get_play_length(), "additive": str(s.get_editor_property("additive_anim_type")),
            "ref": str(s.get_editor_property("ref_pose_type")), "rf": s.get_editor_property("ref_frame_index"),
            "refseq": (s.get_editor_property("ref_pose_seq").get_path_name() if s.get_editor_property("ref_pose_seq") else None),
            "curves": [str(c) for c in AL.get_animation_curve_names(s, unreal.RawCurveTrackTypes.RCT_FLOAT)],
            "tracks": [str(t) for t in AL.get_animation_track_names(s)]}
    out["meta"][key] = meta
    if key.startswith("grab"):
        frames = sorted(set([0] + [sg * SEG2 + f for sg in GRAB_SEGS for f in GRAB_FR]))
    elif key in ("look", "look_lowcrouch"):
        frames = list(range(n))
    elif key == "idle_long":
        frames = list(range(0, min(n, 600), 10))
    elif key.startswith("idle"):
        frames = [0]
    else:
        frames = list(range(n))
    d = {"frames": frames, "full": [], "add": {}}
    for k in frames:
        d["full"].append(pose_list(APE.get_anim_pose_at_frame(s, k, opts(True, True)), bones))
    if meta["additive"] != "AdditiveAnimationType.AAT_NONE":
        for k in frames[:: max(1, len(frames) // 4)][:5]:
            d["add"][str(k)] = {"raw": pose_list(APE.get_anim_pose_at_frame(s, k, opts(False, True)), bones),
                                "comp": pose_list(APE.get_anim_pose_at_frame(s, k, opts(False, False)), bones)}
        d["fullcomp"] = {str(k): pose_list(APE.get_anim_pose_at_frame(s, k, opts(True, False)), bones) for k in frames[:: max(1, len(frames) // 4)][:5]}
    out["seqs"][key] = d
    log.append(f"{key}: {len(frames)} frames dumped ({time.time() - t0:.1f}s)")
json.dump(out, open(os.path.join(SCRATCH, "simdump.json"), "w"))
log.append(f"bones {len(bones)} done {time.time() - t0:.1f}s")
open(os.path.join(SCRATCH, "sim_dump_log.txt"), "w").write("\n".join(log))
