"""What the empty-hands walk / strafe animations do to the body and the left arm, frame by frame (component space)."""
import os, math, unreal
AL = unreal.AnimationLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)


def qinv(a): return (-a[0], -a[1], -a[2], a[3])


def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a)); return r[:3]


cache = {}


def cs(seq, bone, k):
    q, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
    key = (seq.get_path_name(), bone)
    if key not in cache:
        cache[key] = list(reversed([str(x) for x in AL.find_bone_path_to_root(seq, bone)]))
    for b in cache[key]:
        t = AL.get_bone_pose_for_frame(seq, b, k, False)
        p = tuple(a + c for a, c in zip(p, qrot(q, (t.translation.x, t.translation.y, t.translation.z))))
        q = qmul(q, (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
    return p, q


def yaw(q, axis):
    v = qrot(q, axis)
    return math.degrees(math.atan2(v[1], v[0]))


out = []
f = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")],
                    package_paths=["/Game/_STALKER2/Animations/Player/AnimSequences/bh"], recursive_paths=True)
names = sorted(str(a.package_name) for a in ar.get_assets(f))
pick = [n for n in names if n.rsplit("/", 1)[1] in ("AS_fp_bh_walk_left_add", "AS_fp_bh_walk_right_add", "fp_bh_run_left_add")]
out.append("candidates: " + ", ".join(p.rsplit("/", 1)[1] for p in pick))
idle = unreal.load_asset("/Game/_STALKER2/Animations/Player/AnimSequences/bh/stand/fp_bh_idle_stand")
_, hq0 = cs(idle, "jnt_hips", 0)
_, sq0 = cs(idle, "jnt_spine_03", 0)
_, lq0 = cs(idle, "jnt_l_shoulder", 0)
_, nq0 = cs(idle, "jnt_neck", 0)
_, dq0 = cs(idle, "jnt_head", 0)
NA = qrot(qinv(nq0), (1.0, 0.0, 0.0))
DA = qrot(qinv(dq0), (1.0, 0.0, 0.0))
HA = qrot(qinv(hq0), (1.0, 0.0, 0.0))   # the bone-local axes that point component-forward at rest
SA = qrot(qinv(sq0), (1.0, 0.0, 0.0))
LA = qrot(qinv(lq0), (1.0, 0.0, 0.0))
cam0, _ = cs(idle, "jnt_camera", 0)
lh0, _ = cs(idle, "jnt_l_hand", 0)
out.append(f"idle: left hand rel camera {tuple(round(a - b, 1) for a, b in zip(lh0, cam0))}")
for p in pick:
    s = unreal.load_asset(p)
    n = AL.get_num_frames(s) if hasattr(AL, "get_num_frames") else AL.get_num_keys(s)
    rows = []
    for k in range(0, n, max(1, n // 6)):
        try:
            _, hq = cs(s, "jnt_hips", k)
            _, sq = cs(s, "jnt_spine_03", k)
            _, lq = cs(s, "jnt_l_shoulder", k)
            cam, _ = cs(s, "jnt_camera", k)
            lh, _ = cs(s, "jnt_l_hand", k)
            _, nq = cs(s, "jnt_neck", k)
            _, dq = cs(s, "jnt_head", k)
            rows.append(f"f{k}: neck {yaw(nq, NA):+.0f} head {yaw(dq, DA):+.0f} hips {yaw(hq, HA):+.0f} spine3 {yaw(sq, SA):+.0f} Lshoulder {yaw(lq, LA):+.0f} Lhand-cam {tuple(round(a - b) for a, b in zip(lh, cam))}")
        except Exception as e:
            rows.append(f"f{k}: ERR {e}")
    out.append(f"== {p.rsplit('/', 1)[1]} ({n} frames)")
    out += ["   " + r for r in rows]
open(os.path.join(SCRATCH, "strafe_study.txt"), "w").write("\n".join(out))
