import os, math, unreal
AL = unreal.AnimationLibrary
out = []
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def ang(a, b):
    d = qmul(a, qinv(b)); return math.degrees(2 * math.acos(min(1.0, abs(d[3]))))
def q(t): return (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)
D = f"{MOD_ROOT}/Runtime/"
for i in range(25):
    s = unreal.load_asset(D + f"AS_ImmLoot_Touch{i}")
    n = AL.get_num_frames(s)
    tracks = [str(t) for t in AL.get_animation_track_names(s)]
    arm = [b for b in tracks if b.startswith("jnt_l_") and not "hand_" in b]
    worst = (0, "", 0)
    for b in arm:
        prev = None
        for k in range(n + 1):
            r = q(AL.get_bone_pose_for_frame(s, b, k, False))
            if prev is not None:
                a = ang(r, prev)
                if a > worst[0]: worst = (a, b, k)
            prev = r
    nt = [(e.notify.get_class().get_name(), round(AL.get_anim_notify_event_trigger_time(e), 3), e.notify.get_editor_property("end_value") if e.notify.get_class().get_name() == "AnimNotify_HandIK" else "") for e in AL.get_animation_notify_events(s) if e.notify]
    out.append(f"Touch{i}: frames {n} len {s.get_play_length():.3f} worst step {worst[0]:.1f} deg {worst[1]} @k{worst[2]} notifies {nt}")
    if i == 12:
        out.append("  arm bones: " + ", ".join(arm))
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "touchscan.txt"), "w").write("\n".join(out))
