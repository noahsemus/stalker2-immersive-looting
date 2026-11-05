"""Editor (ue_exec, --arg KEYS=<path to bagfix_keys.json>): writes AS_ImmLoot_BagFix from gen_bagfix.py's keys
(mesh-space rotation offset additive, reference = frame 0, 30 fps), then reads UE's own additive back for a few frames
and compares it with the keys' intended delta. Output: SCRATCH/set_bagfix.txt"""
import json, os, math, unreal
AL = unreal.AnimationLibrary
EAL = unreal.EditorAssetLibrary
APE = unreal.AnimPoseExtensions
DIR = f"{MOD_ROOT}/Runtime"
NAME = "AS_ImmLoot_BagFix"
out = []
try:
    K = json.load(open(ARGS["KEYS"]))
    path = f"{DIR}/{NAME}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME, DIR, unreal.load_asset(f"{DIR}/AS_ImmLoot_BagServo"))
    seq = unreal.load_asset(path)
    n = K["frames"]
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot bag fix", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(n - 1), True)
    for b in K["tracks"]:
        ks = K["keys"][b]
        pos = [unreal.Vector(*k[1]) for k in ks]
        rot = [unreal.Quat(*k[0]) for k in ks]
        scl = [unreal.Vector(1.0, 1.0, 1.0) for _ in ks]
        ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    for c in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, c, False)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE)
    seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
    seq.set_editor_property("ref_frame_index", 0)
    out.append(f"{NAME}: {len(K['tracks'])} tracks, {n} frames, len {seq.get_play_length():.4f} s, frames {AL.get_num_frames(seq)}, "
               f"saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")
    # read back: the keyed rotation of a few bones vs the keys
    worst = 0.0
    for b in ("jnt_l_shoulder", "jnt_l_hand", "jnt_r_hand", "jnt_l_weapon"):
        if b not in K["tracks"]:
            continue
        for f in (0, 1, 10, 19, 20, 38, 39, n - 1):
            t = AL.get_bone_pose_for_frame(seq, b, f, False)
            k = K["keys"][b][f]
            d = abs(t.rotation.x * k[0][0] + t.rotation.y * k[0][1] + t.rotation.z * k[0][2] + t.rotation.w * k[0][3])
            worst = max(worst, math.degrees(2 * math.acos(min(1.0, d))))
            worst = max(worst, (t.translation - unreal.Vector(*k[1])).length())
    out.append(f"read back vs keys: worst {worst:.4f} (deg / cm)")
    o = unreal.AnimPoseEvaluationOptions()
    o.set_editor_property("evaluation_type", unreal.AnimDataEvalType.COMPRESSED)
    o.set_editor_property("retrieve_additive_as_full_pose", False)
    o.set_editor_property("should_retarget", False)
    for f in (1, 10, 19, 39):
        p = APE.get_anim_pose_at_frame(seq, f, o)
        tr = APE.get_bone_pose(p, "jnt_l_hand", unreal.AnimPoseSpaces.LOCAL)
        sh = APE.get_bone_pose(p, "jnt_l_shoulder", unreal.AnimPoseSpaces.LOCAL)
        out.append(f"  compressed additive frame {f}: l_hand turn {math.degrees(2 * math.acos(min(1.0, abs(tr.rotation.w)))):.1f} deg, "
                   f"l_shoulder move {sh.translation.length():.1f} cm")
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "set_bagfix.txt"), "w").write("\n".join(out))
