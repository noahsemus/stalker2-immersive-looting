"""Read-only: component-space path of the left arm in the vanilla grab (fp_ar_weapon_grab) relative to jnt_camera,
per frame, plus the bone chain. Run in the open editor through ue_exec (harness tools).
Output: <SCRATCH>/inspect_grab.txt
"""
import os
import unreal

AL = unreal.AnimationLibrary
SRC = ARGS.get("SRC", "/Game/_STALKER2/Animations/Player/AnimSequences/ar/common/grabitem/fp_ar_weapon_grab")
seq = unreal.load_asset(SRC)
out = []


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), (-a[0], -a[1], -a[2], a[3]))
    return (r[0], r[1], r[2])


def cs(bone, frame):
    path = [str(b) for b in AL.find_bone_path_to_root(seq, bone)]   # bone ... root
    q, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    for b in reversed(path):
        t = AL.get_bone_pose_for_frame(seq, b, frame, False)
        lq = (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)
        lp = (t.translation.x, t.translation.y, t.translation.z)
        rp = qrot(q, lp)
        p = (p[0] + rp[0], p[1] + rp[1], p[2] + rp[2])
        q = qmul(q, lq)
    return p, q


n = AL.get_num_frames(seq)
out.append(f"frames {n} len {seq.get_play_length():.3f}")
for b in ("jnt_l_hand", "jnt_l_weapon", "jnt_camera"):
    out.append(f"path {b}: {[str(x) for x in AL.find_bone_path_to_root(seq, b)]}")
out.append(f"notifies: {[(e.notify.get_class().get_name() if e.notify else None) for e in AL.get_animation_notify_events(seq)]}")
for f in range(0, n + 1, 3):
    cam, cq = cs("jnt_camera", f)
    row = [f"f{f:02d}"]
    for b in ("jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand", "jnt_l_weapon"):
        p, _ = cs(b, f)
        row.append(f"{b[6:]}=({p[0]-cam[0]:.1f},{p[1]-cam[1]:.1f},{p[2]-cam[2]:.1f})")
    fwd = qrot(cq, (1.0, 0.0, 0.0))
    row.append(f"camX=({fwd[0]:.2f},{fwd[1]:.2f},{fwd[2]:.2f}) cam=({cam[0]:.1f},{cam[1]:.1f},{cam[2]:.1f})")
    out.append(" ".join(row))
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "inspect_grab.txt"), "w").write("\n".join(out))
