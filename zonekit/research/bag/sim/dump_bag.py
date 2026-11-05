"""Read-only (open editor, ue_exec): local bone poses for the bag simulator -> SCRATCH/bagdump.json.
raw = the keyed local transforms (AnimationLibrary), ue_add = UE's own additive delta for a frame (AnimPose, additive
not applied), ue_addc = the same from the compressed data."""
import os, json, time, unreal
AL = unreal.AnimationLibrary
APE = unreal.AnimPoseExtensions
LOC = unreal.AnimPoseSpaces.LOCAL
t0 = time.time()
A = "/Game/_STALKER2/Animations/Player/AnimSequences/"
R = "/ImmersiveLooting/Runtime/"
SEQS = {   # key: (path, frames or None = all, dump UE's additive for these frames)
    "idle": (A + "bh/stand/fp_bh_idle_stand", [0], []),
    "idle_lowcrouch": (A + "bh/lowcrouch/fp_bh_idle_lowcrouch", [0], []),
    "idle_crouch": (A + "bh/crouch/fp_bh_idle_crouch", [0], []),
    "ar_idle": (A + "ar/common/stand/fp_ar_idle_stand", [0], []),
    "look": (A + "bh/stand/fp_bh_stand_lookvertical_idle", None, [0, 15, 25]),
    "look_lowcrouch": (A + "bh/lowcrouch/AS_fp_bh_lowcrouch_lookvertical", None, [0, 15, 25]),
    "bag_in": (R + "AS_ImmLoot_BagIn", None, []),
    "bag_idle": (R + "AS_ImmLoot_BagIdle", [0, 30, 60], []),
    "bag_out": (R + "AS_ImmLoot_BagOut", None, []),
    "pitchfix": (R + "AS_ImmLoot_BagPitchFix", None, [0, 30, 59, 90]),
    "servo": (R + "AS_ImmLoot_BagServo", [0, 1, 12, 13, 14, 25 * 30 + 13, 25 * 30 + 18, 25 * 45 + 13, 25 * 45 + 18, 25 * 45 + 8, 25 * 59 + 13, 25 * 59 + 18], [13, 25 * 45 + 13, 25 * 45 + 18]),
    "grabview": (R + "AS_ImmLoot_GrabBHView", [0], []),
    "grabviewcr": (R + "AS_ImmLoot_GrabBHViewCrouch", [0], []),
}


def opts(full, raw):
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.RAW if raw else unreal.AnimDataEvalType.COMPRESSED)
    o.set_editor_property("retrieve_additive_as_full_pose", full)
    o.set_editor_property("should_retarget", False)
    return o


def pose_list(pose, bones):
    r = []
    for b in bones:
        t = APE.get_bone_pose(pose, b, LOC)
        q, p = t.rotation, t.translation
        r.append([q.x, q.y, q.z, q.w, p.x, p.y, p.z])
    return r


idle = unreal.load_asset(SEQS["idle"][0])
p0 = APE.get_anim_pose_at_frame(idle, 0, opts(True, True))
bones = [str(b) for b in APE.get_bone_names(p0)]
parents = []
for b in bones:
    path = [str(x) for x in AL.find_bone_path_to_root(idle, b)]
    parents.append(bones.index(path[1]) if len(path) > 1 and path[1] in bones else -1)
out = {"bones": bones, "parents": parents, "seqs": {}, "meta": {}}
sk = idle.get_editor_property("skeleton")
out["refpose"] = pose_list(APE.get_reference_pose(sk), bones)
log = []
for key, (path, frames, addf) in SEQS.items():
    s = unreal.load_asset(path)
    if s is None:
        log.append(f"missing {path}"); continue
    n = AL.get_num_frames(s)
    tracks = [str(t) for t in AL.get_animation_track_names(s)]
    rps = s.get_editor_property("ref_pose_seq")
    out["meta"][key] = {"path": path, "frames": n, "len": s.get_play_length(), "additive": str(s.get_editor_property("additive_anim_type")),
                        "ref": str(s.get_editor_property("ref_pose_type")), "rf": s.get_editor_property("ref_frame_index"),
                        "refseq": rps.get_path_name() if rps else None, "tracks": tracks}
    fr = list(range(n + 1)) if frames is None else [f for f in frames if f <= n]
    d = {"frames": fr, "raw": [], "ue_add": {}, "ue_addc": {}}
    for k in fr:   # raw keys: tracked bones from the track data, others from the reference pose
        rows = []
        for i, b in enumerate(bones):
            if b in tracks:
                t = AL.get_bone_pose_for_frame(s, b, k, False)
                rows.append([t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, t.translation.x, t.translation.y, t.translation.z])
            else:
                rows.append(None)
        d["raw"].append(rows)
    for k in addf:
        if k <= n:
            d["ue_add"][str(k)] = pose_list(APE.get_anim_pose_at_frame(s, k, opts(False, True)), bones)
            d["ue_addc"][str(k)] = pose_list(APE.get_anim_pose_at_frame(s, k, opts(False, False)), bones)
    out["seqs"][key] = d
    log.append(f"{key}: {len(fr)} frames ({time.time() - t0:.1f}s) n={n} additive={out['meta'][key]['additive']} rf={out['meta'][key]['rf']}")
json.dump(out, open(os.path.join(SCRATCH, "bagdump.json"), "w"))
log.append(f"bones {len(bones)} done {time.time() - t0:.1f}s")
open(os.path.join(SCRATCH, "bagdump_log.txt"), "w").write("\n".join(log))
