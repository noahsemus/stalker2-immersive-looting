"""v1.3.2 l (tester: "give me full control over every axis with sliders, not just dropdowns"): DEV pose-offset tables
for the MCM DEV menu. Each is a local-space additive (frame 0 = no offset, the reference) holding a grid of offsets,
one per frame; the actor plays it through a montage asset in the FullBody slot (after every other pose, like the
pitch fix), paused, and sets its position every tick from the MCM values (rounded to the grid; the fastest axis is
continuous: the montage interpolates between neighbouring frames).

  AS_ImmLoot_DevArmRot   both shoulders turned about their joints, in the spine's frame (mesh axes at rest:
                         X forward, Y right, Z up; it turns with the look): pitch / roll / yaw -60..+60 in 5s.
                         frame = 1 + (yaw_i * 25 + roll_i) * 25 + pitch_f
  AS_ImmLoot_DevArmPos   both shoulders moved, same frame: X / Y / Z -15..+15 cm in 1.5s.
                         frame = 1 + (x_i * 21 + y_i) * 21 + z_f
  AS_ImmLoot_DevHandRot  the left hand turned about the wrist, in its own bone axes (X along the hand):
                         roll (X) / pitch (Y) / yaw (Z) -90..+90 in 7.5s. frame = 1 + (yaw_i * 25 + pitch_i) * 25 + roll_f

Montages AM_ImmLoot_Dev* are made from them (DefaultSlot): the tester sets each one's slot to FullBody in the montage
editor once, then run again with CHECK=1. Run in the open editor with the harness ue_exec tool.
"""
import math
import os
import unreal

EAL = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary
DIR = f"{MOD_ROOT}/Runtime"
BASE = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand"
TEMPLATE = f"{DIR}/AS_ImmLoot_GrabAr"
out = []


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(a):
    return (-a[0], -a[1], -a[2], a[3])


def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a))
    return (r[0], r[1], r[2])


def rotq(roll, pitch, yaw):
    q = unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw).quaternion()
    return (q.x, q.y, q.z, q.w)


def cs_rot(seq, bone):
    q = (0.0, 0.0, 0.0, 1.0)
    for b in reversed([str(x) for x in AL.find_bone_path_to_root(seq, bone)]):
        t = AL.get_bone_pose_for_frame(seq, b, 0, False).rotation
        q = qmul(q, (t.x, t.y, t.z, t.w))
    return q


def parent(seq, bone):
    return [str(x) for x in AL.find_bone_path_to_root(seq, bone)][1]


# v1.3.2 m (tester: "bigger ranges, way bigger"): the same frame counts (the montages keep their length), the values
# spaced exponentially: fine near 0, coarse far out. value(i) = sign(i) * A * (B^|i| - 1), i = -H..H
ROT_A, ROT_B, ROT_H = 6.054235, 1.330347, 12      # 0, 2, 4.7, 8.2, 12.9, 19.2, 27.5, 38.6, 53.3, 73, 99, 134, 180 deg
POS_A, POS_B, POS_H = 1.054993, 1.473937, 10      # 0, 0.5, 1.2, 2.3, 3.9, 6.3, 9.8, 14.9, 22.5, 33.6, 50 cm
expv = lambda A, B, H: [math.copysign(A * (B ** abs(i) - 1), i) for i in range(-H, H + 1)]
AXIS = expv(ROT_A, ROT_B, ROT_H)
POS = expv(POS_A, POS_B, POS_H)
HAND = expv(ROT_A, ROT_B, ROT_H)


def build(name, bones, frames_fn):
    base = unreal.load_asset(BASE)
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, unreal.load_asset(TEMPLATE))
    seq = unreal.load_asset(path)
    rest = {b: AL.get_bone_pose_for_frame(base, b, 0, False) for b in bones}
    keys = {b: ([], [], []) for b in bones}
    n = 0
    for offs in frames_fn():          # offs: {bone: (local quat, local translation)}
        for b in bones:
            q, t = offs[b] if offs else ((rest[b].rotation.x, rest[b].rotation.y, rest[b].rotation.z, rest[b].rotation.w),
                                         (rest[b].translation.x, rest[b].translation.y, rest[b].translation.z))
            keys[b][0].append(unreal.Vector(*t))
            keys[b][1].append(unreal.Quat(*q))
            keys[b][2].append(rest[b].scale3d)
        n += 1
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket(f"ImmLoot {name}", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.set_frame_rate(unreal.FrameRate(30, 1), True)
    ctrl.set_number_of_frames(unreal.FrameNumber(n - 1), True)
    for b in bones:
        ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, *keys[b], True)
    ctrl.close_bracket(True)
    for tn in [str(x) for x in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    for cn in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, cn, False)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE)
    seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
    seq.set_editor_property("ref_frame_index", 0)
    out.append(f"{name}: {n} frames, bones {bones}, len {seq.get_play_length():.2f} s, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


def arm_frames(kind):
    base = unreal.load_asset(BASE)
    sh = ["jnt_l_shoulder", "jnt_r_shoulder"]
    rest = {b: AL.get_bone_pose_for_frame(base, b, 0, False) for b in sh}
    pq = {b: cs_rot(base, parent(base, b)) for b in sh}

    def gen():
        yield None
        if kind == "rot":
            for yaw in AXIS:
                for roll in AXIS:
                    for pitch in AXIS:
                        q = rotq(roll, pitch, yaw)
                        o = {}
                        for b in sh:
                            r = rest[b].rotation
                            o[b] = (qmul(qmul(qmul(qinv(pq[b]), q), pq[b]), (r.x, r.y, r.z, r.w)),
                                    (rest[b].translation.x, rest[b].translation.y, rest[b].translation.z))
                        yield o
        else:
            for x in POS:
                for y in POS:
                    for z in POS:
                        o = {}
                        for b in sh:
                            r, t = rest[b].rotation, rest[b].translation
                            d = qrot(qinv(pq[b]), (x, y, z))
                            o[b] = ((r.x, r.y, r.z, r.w), (t.x + d[0], t.y + d[1], t.z + d[2]))
                        yield o
    return sh, gen


def hand_frames():
    base = unreal.load_asset(BASE)
    b = "jnt_l_hand"
    rest = AL.get_bone_pose_for_frame(base, b, 0, False)

    def gen():
        yield None
        for yaw in HAND:
            for pitch in HAND:
                for roll in HAND:
                    r = rest.rotation
                    yield {b: (qmul((r.x, r.y, r.z, r.w), rotq(roll, pitch, yaw)), (rest.translation.x, rest.translation.y, rest.translation.z))}
    return [b], gen


MONTAGES = (("AM_ImmLoot_DevArmRot", "AS_ImmLoot_DevArmRot"), ("AM_ImmLoot_DevArmPos", "AS_ImmLoot_DevArmPos"),
            ("AM_ImmLoot_DevHandRot", "AS_ImmLoot_DevHandRot"))
try:
    if ARGS.get("PART") == "rot":
        # v1.3.2 o: the tables for the F7 panel's CutsceneSlot backend (dynamic montages: no montage assets needed)
        bones, gen = arm_frames("rot"); build("AS_ImmLoot_DevArmRot", bones, gen)
        bones, gen = hand_frames(); build("AS_ImmLoot_DevHandRot", bones, gen)
        raise SystemExit
    if not ARGS.get("CHECK"):
        bones, gen = arm_frames("rot"); build("AS_ImmLoot_DevArmRot", bones, gen)
        bones, gen = arm_frames("pos"); build("AS_ImmLoot_DevArmPos", bones, gen)
        bones, gen = hand_frames(); build("AS_ImmLoot_DevHandRot", bones, gen)
    for mname, sname in MONTAGES:
        path = f"{DIR}/{mname}"
        if not EAL.does_asset_exist(path):
            f = unreal.AnimMontageFactory()
            f.set_editor_property("source_animation", unreal.load_asset(f"{DIR}/{sname}"))
            unreal.AssetToolsHelpers.get_asset_tools().create_asset(mname, DIR, unreal.AnimMontage, f)
            out.append(f"created {path}")
        m = unreal.load_asset(path)
        a = m.get_editor_property("blend_in"); a.set_editor_property("blend_time", 0.2); m.set_editor_property("blend_in", a)
        b_ = m.get_editor_property("blend_out"); b_.set_editor_property("blend_time", 0.3); m.set_editor_property("blend_out", b_)
        m.set_editor_property("enable_auto_blend_out", False)
        slots = [str(s) for s in AL.get_montage_slot_names(m)]
        out.append(f"{mname}: slots {slots} {'OK' if slots == ['FullBody'] else '(needs FullBody)'}, group {m.get_group_name()}, "
                   f"length {m.get_play_length():.2f}, saved {EAL.save_loaded_asset(m, only_if_is_dirty=False)}")
except SystemExit:
    pass
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_dev_offsets.txt"), "w").write("\n".join(out))
