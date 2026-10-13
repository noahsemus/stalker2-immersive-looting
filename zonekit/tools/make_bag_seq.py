"""1.1.2 bag looting (tester: "an optional MCM toggle, on by default, that uses the bag animation (like opening the
player's inventory) when looting bodies and stashes instead of the hand going out"). Run in the open editor with the
harness ue_exec tool (BUILD.md).

The game's own inventory animation is the montage MG_fp_backpack_inventory (MainActionSlot; In 1.5 s / Idle / Out
0.667 s / OutFast; the inventory opens at 0.567 s) on the player and MG_backpack_fp_inventory on the backpack mesh
(SK_bpa_pla_01, its material is the first-person "_fov" kind; its root bone is keyed in the PLAYER's component space,
so the mesh sits at the player mesh's origin). Its UseHandItem notify opens the inventory, so it is not played: the
player sequences are copied into AS_ImmLoot_BagIn / AS_ImmLoot_BagOut (every bone track, made from our own
AS_ImmLoot_Grab: the live editor cannot duplicate /Game assets) with
  - a HandIK "off" notify at the start of In and "on" at the end of Out (the left-hand IK would pull the hand to
    jnt_weapon, which the bag animation keys behind the back: that is where a held weapon goes meanwhile);
  - the same for the right hand (build n: a hidden weapon stays in the hands, its right-hand IK pins the hand);
  - left_hand_curve 1 (rifles with an underbarrel idle pin the left arm otherwise), back to 0 at the end of Out.
The bag mesh plays the vanilla AS_backpack_fp_inventory_in / _out as single-node animations (no copies needed).
Output: <SCRATCH>/make_bag_seq.txt
"""
import math
import os
import unreal

AL = unreal.AnimationLibrary
EAL = unreal.EditorAssetLibrary
DIR = f"{MOD_ROOT}/Runtime"
SRC = "/Game/_STALKER2/Animations/Player/AnimSequences/bpa/"
MONT = "/Game/_STALKER2/Animations/Player/AnimSequences/ar/ak74/MG_fp_ak74_weapon_grab"
TEMPLATE = f"{DIR}/AS_ImmLoot_Grab"
out = []


BASE_BH = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand"


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


def cs(seq, bone, k):
    q, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    for b in reversed([str(x) for x in AL.find_bone_path_to_root(seq, bone)]):
        t = AL.get_bone_pose_for_frame(seq, b, k, False)
        p = tuple(a + b_ for a, b_ in zip(p, qrot(q, (t.translation.x, t.translation.y, t.translation.z))))
        q = qmul(q, (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
    return p, q


def build(src_name, name, mode, add=False):
    """add (build g, empty hands; tester: "the bag hijacks the camera and looks down": in the bare-hands layer the bag
    played in MainActionSlot overrode the camera's look pitch, probe: view pitch -51 -> -75): a LOCAL-SPACE ADDITIVE
    played in FullBody (after everything; the camera, the legs and the look stay the game's): frame 0 = the base
    (fp_bh_idle_stand frame 0, every bone), frames 1.. = the bag pose on the upper body (jnt_spine_01 and below it; the
    spine's root turned so the upper body sits where the bag animation has it in component space despite the bare-hands
    hips), the base on every other bone (no change). Played from frame 1."""
    src = unreal.load_asset(SRC + src_name)
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, unreal.load_asset(TEMPLATE))
    seq = unreal.load_asset(path)
    nkeys = AL.get_num_keys(src)
    tracks = [str(t) for t in AL.get_animation_track_names(src)]
    base = unreal.load_asset(BASE_BH)
    upper = {b for b in tracks if "jnt_spine_01" in [str(x) for x in AL.find_bone_path_to_root(src, b)]}
    if add:
        hp, hq = cs(base, "jnt_hips", 0)
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot bag", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.set_number_of_frames(unreal.FrameNumber(nkeys - 1 + (1 if add else 0)), True)
    for b in tracks:
        pos, rot, scl = [], [], []
        if add:
            t0 = AL.get_bone_pose_for_frame(base, b, 0, False)
            pos.append(t0.translation); rot.append(t0.rotation); scl.append(t0.scale3d)
        for k in range(nkeys):
            if add and b not in upper:
                t = AL.get_bone_pose_for_frame(base, b, 0, False)
            elif add and b == "jnt_spine_01":
                sp, sq = cs(src, b, k)
                lq = qmul(qinv(hq), sq)
                lp = qrot(qinv(hq), tuple(x - y for x, y in zip(sp, hp)))
                t = unreal.Transform()
                t.translation = unreal.Vector(*lp)
                t.rotation = unreal.Quat(*lq)
                t.scale3d = AL.get_bone_pose_for_frame(src, b, k, False).scale3d
            else:
                t = AL.get_bone_pose_for_frame(src, b, k, False)
            pos.append(t.translation)
            rot.append(t.rotation)
            scl.append(t.scale3d)
        ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, pos, rot, scl, True)
    ctrl.close_bracket(True)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_LOCAL_SPACE_BASE if add else unreal.AdditiveAnimationType.AAT_NONE)
    if add:
        seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
        seq.set_editor_property("ref_frame_index", 0)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    track = "ImmLoot"
    if track not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.add_animation_notify_track(seq, track, unreal.LinearColor(0.2, 0.8, 0.2, 1.0))
    hand = None
    for e in AL.get_animation_notify_events(unreal.load_asset(MONT)):
        if e.notify is not None and e.notify.get_class().get_name() == "AnimNotify_HandIK":
            hand = e.notify.get_editor_property("hand_to_apply")
    hik = unreal.load_class(None, "/Script/Stalker2.AnimNotify_HandIK")
    length = seq.get_play_length()
    if mode in ("in", "out"):
        n = AL.add_animation_notify_event(seq, track, (0.02 if mode == "in" else length - 0.08) + (1 / 30 if add and mode == "in" else 0.0), hik)
        n.set_editor_property("hand_to_apply", hand)
        if mode == "out":
            n.set_editor_property("end_value", 1.0)
        # build n (tester, armed: "the right hand still holds the weapon that isn't there, the elbow bends up, the hand
        # doesn't go into the bag"): the weapon stays in the hands (hidden) since build m, so the weapon layer's
        # right-hand IK (TwoBoneIK_GSC to the weapon's jnt_r_hand socket, alpha HandsIKData.RightHand) pins the hand
        # to the grip: the same notify for the right hand
        n = AL.add_animation_notify_event(seq, track, (0.02 if mode == "in" else length - 0.08) + (1 / 30 if add and mode == "in" else 0.0), hik)
        n.set_editor_property("hand_to_apply", unreal.AnimationHands.RIGHT_HAND)
        if mode == "out":
            n.set_editor_property("end_value", 1.0)
    for c in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, c, False)
    AL.add_curve(seq, "left_hand_curve", unreal.RawCurveTrackTypes.RCT_FLOAT, False)
    if mode in ("in", "idle"):
        AL.add_float_curve_keys(seq, "left_hand_curve", [0.0, length], [1.0, 1.0])
    else:
        AL.add_float_curve_keys(seq, "left_hand_curve", [0.0, max(0.0, length - 0.2), length], [1.0, 1.0, 0.0])
    out.append(f"{name}: from {src_name}, {len(tracks)} tracks, {nkeys} keys, len {length:.3f} (src {src.get_play_length():.3f}), "
               f"notifies {[(e.notify.get_class().get_name(), round(AL.get_anim_notify_event_trigger_time(e), 3), e.notify.get_editor_property('end_value')) for e in AL.get_animation_notify_events(seq)]}, "
               f"curves {[str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]}, "
               f"saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")
    # check: a few bones match the source at a few frames (component of the pose, local space)
    for b in (() if add else ("jnt_l_hand", "jnt_r_hand", "jnt_weapon", "jnt_camera")):
        for k in (0, nkeys // 2, nkeys - 1):
            a_, b_ = AL.get_bone_pose_for_frame(src, b, k, False), AL.get_bone_pose_for_frame(seq, b, k, False)
            d = (a_.translation - b_.translation).length()
            if d > 0.01:
                out.append(f"  MISMATCH {b} k{k}: {d:.3f} cm")


LOOK_BH = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_stand_lookvertical_idle"


def build_pitch_fix(name="AS_ImmLoot_BagPitchFix"):
    """Build m (tester: empty hands, standing, "the bag happens way above the screen"; the right hand off the bag by
    7-28 cm). Probe + data: the game's bag posture turns the whole upper body with the view (the vanilla bag stays at
    (39, -17, -26) cm in view axes); the bare-hands look additive (fp_bh_stand_lookvertical_idle, mesh-space rotation
    offset on fp_bh_idle_stand) turns the spine, shoulders and camera with the view but, looking DOWN, keeps the hands'
    orientation (0 deg): the arms counter-turn, each about its own shoulder, so the bag stays low and the hands part.
    (fp_ar_stand_lookvertical and the low-crouch one turn everything rigidly.) This pose table undoes that on the arms:
    a mesh-space rotation offset additive, played in FullBody (after the look additive) at the frame of the view pitch:
    frame f = pitch -f deg (0..90), each bone from the shoulders down gets R(p) * inverse(D_b(p)) (R = the spine's turn,
    D_b = that bone's turn in the look additive), so the arms and the bag turn with the view as one piece."""
    look = unreal.load_asset(LOOK_BH)
    base = unreal.load_asset(BASE_BH)
    path = f"{DIR}/{name}"
    if not EAL.does_asset_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(name, DIR, unreal.load_asset(TEMPLATE))
    seq = unreal.load_asset(path)
    tracks = [str(t) for t in AL.get_animation_track_names(base)]
    par = {b: ([str(x) for x in AL.find_bone_path_to_root(base, b)] + [None])[1] for b in tracks}
    arms = {b for b in tracks if any(s in [str(x) for x in AL.find_bone_path_to_root(base, b)] for s in ("jnt_l_shoulder", "jnt_r_shoulder"))}
    order = sorted(tracks, key=lambda b: len(AL.find_bone_path_to_root(base, b)))

    def cs_time(seq_, t):
        """component rotations of every bone at time t (seconds)"""
        rot = {}
        for b in order:
            tr = AL.get_bone_pose_for_time(seq_, b, t, False)
            lq = (tr.rotation.x, tr.rotation.y, tr.rotation.z, tr.rotation.w)
            rot[b] = qmul(rot[par[b]], lq) if par[b] in rot else lq
        return rot

    base_rot = cs_time(base, 0.0)
    base_loc = {b: AL.get_bone_pose_for_frame(base, b, 0, False) for b in tracks}
    lb = cs_time(unreal.load_asset(look.get_editor_property("ref_pose_seq").get_path_name()), 0.0)   # the look additive's own base
    N = 91
    keys = {b: ([], [], []) for b in tracks}
    for f in range(N):
        p = -float(f)
        la = cs_time(look, (90.0 - p) / 180.0 * look.get_play_length())
        D = {b: qmul(la[b], qinv(lb[b])) for b in tracks}
        R = D["jnt_spine_03"]
        want = {}
        for b in order:
            want[b] = qmul(qmul(R, qinv(D[b])), base_rot[b]) if b in arms else base_rot[b]
        for b in tracks:
            if b in arms:
                lq = qmul(qinv(want[par[b]]), want[b]) if par[b] else want[b]
                q = unreal.Quat(*lq)
            else:
                q = base_loc[b].rotation
            keys[b][0].append(base_loc[b].translation)
            keys[b][1].append(q)
            keys[b][2].append(base_loc[b].scale3d)
        if f in (0, 30, 60, 90):
            out.append(f"PITCHFIX pitch {p:+.0f}: spine turn {math.degrees(2 * math.acos(min(1.0, abs(R[3])))):.0f} deg, "
                       f"l_hand look turn {math.degrees(2 * math.acos(min(1.0, abs(D['jnt_l_hand'][3])))):.0f}, "
                       f"r_hand look turn {math.degrees(2 * math.acos(min(1.0, abs(D['jnt_r_hand'][3])))):.0f}")
    ctrl = seq.get_editor_property("controller")
    ctrl.open_bracket("ImmLoot pitch fix", True)
    ctrl.remove_all_bone_tracks(True)
    ctrl.set_number_of_frames(unreal.FrameNumber(N - 1), True)
    for b in tracks:
        ctrl.add_bone_curve(b, True)
        ctrl.set_bone_track_keys(b, *keys[b], True)
    ctrl.close_bracket(True)
    for tn in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
        AL.remove_animation_notify_events_by_track(seq, tn)
    for c in [str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]:
        AL.remove_curve(seq, c, False)
    seq.set_editor_property("additive_anim_type", unreal.AdditiveAnimationType.AAT_ROTATION_OFFSET_MESH_SPACE)
    seq.set_editor_property("ref_pose_type", unreal.AdditiveBasePoseType.ABPT_LOCAL_ANIM_FRAME)
    seq.set_editor_property("ref_frame_index", 0)
    out.append(f"{name}: {len(tracks)} tracks ({len(arms)} arm bones corrected), {N} frames, len {seq.get_play_length():.3f}, "
               f"additive {seq.get_editor_property('additive_anim_type')}, saved {EAL.save_loaded_asset(seq, only_if_is_dirty=False)}")


try:
    if ARGS.get("PART", "") == "pitch":
        build_pitch_fix()
        raise SystemExit
    build("AS_fp_backpack_inventory_in", "AS_ImmLoot_BagIn", "in")
    build("AS_fp_backpack_inventory_out", "AS_ImmLoot_BagOut", "out")
    build("AS_fp_backpack_inventory_idle", "AS_ImmLoot_BagIdle", "idle")   # build e (tester: "copy the ENTIRE vanilla animation": the right hand goes into the bag)
    # (build g's additive copies AS_ImmLoot_Bag*Add are no longer built: unused since build k; removed for the release)
except SystemExit:
    pass
except Exception:
    import traceback
    out.append("EXCEPTION " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "make_bag_seq.txt"), "w").write("\n".join(out))
