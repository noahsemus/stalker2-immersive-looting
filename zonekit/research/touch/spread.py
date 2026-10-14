import os, math, unreal
AL = unreal.AnimationLibrary
out = []
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)
def qinv(a): return (-a[0], -a[1], -a[2], a[3])
def qrot(a, p):
    r = qmul(qmul(a, (p[0], p[1], p[2], 0.0)), qinv(a)); return (r[0], r[1], r[2])
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def unit(a): n = math.sqrt(sum(x*x for x in a)); return tuple(x / n for x in a)
def angv(a, b): return math.degrees(math.acos(max(-1, min(1, sum(x*y for x, y in zip(unit(a), unit(b)))))))
def hand_space(s, k):
    # positions of finger joints in the hand bone's frame (chain from jnt_l_hand)
    res = {}
    for f in ("index", "middle", "ring", "pinky", "thumb"):
        q, p = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)
        chain = ([f"jnt_l_hand_{f}_meta"] if f != "thumb" else []) + [f"jnt_l_hand_{f}_01", f"jnt_l_hand_{f}_02", f"jnt_l_hand_{f}_03"]
        pts = []
        for b in chain:
            t = AL.get_bone_pose_for_frame(s, b, k, False)
            p = tuple(a + c for a, c in zip(p, qrot(q, (t.translation.x, t.translation.y, t.translation.z))))
            q = qmul(q, (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w))
            pts.append(p)
        # fingertip guess: last joint + its direction
        res[f] = pts
    return res
ar_ = unreal.AssetRegistryHelpers.get_asset_registry()
P = '/Game/_STALKER2/Animations/Player/AnimSequences/'
f = unreal.ARFilter(package_paths=[P + 'Dialog_animations', P + 'Interactables', P + 'contextual_action', P + 'bh', P + 'Items', P + 'InspectArtifact', P + 'player_death'], recursive_paths=True, class_paths=[unreal.TopLevelAssetPath('/Script/Engine','AnimSequence')])
cands = []
for a in ar_.get_assets(f):
    s = unreal.load_asset(str(a.package_name))
    try:
        n = AL.get_num_frames(s)
    except Exception:
        continue
    for k in range(0, n + 1, max(1, n // 12)):
        try:
            h = hand_space(s, k)
        except Exception:
            break
        d = {x: sub(h[x][-1], h[x][-3 if x != "thumb" else 0]) for x in h}   # finger direction (base joint -> last joint)
        curl = max(angv(sub(h[x][-1], h[x][-2]), sub(h[x][-2], h[x][-3])) for x in ("index", "middle", "ring", "pinky"))
        spread = angv(d["index"], d["pinky"])
        cands.append(((spread if curl < 35 else -1), spread, curl, str(a.asset_name), k))
cands.sort(reverse=True)
for c in cands[:12]:
    out.append(f"{c[3]} k{c[4]}: index-pinky spread {c[1]:.0f} deg, curl {c[2]:.0f} deg")
s = unreal.load_asset(P + "Dialog_animations/AS_fp_dialogue_openhands_expressive")
h = hand_space(s, 36); d = {x: sub(h[x][-1], h[x][-3 if x != "thumb" else 0]) for x in h}
out.append(f"current open hand (openhands_expressive k36): spread {angv(d['index'], d['pinky']):.0f}")
os.makedirs(SCRATCH, exist_ok=True)
open(os.path.join(SCRATCH, "spread.txt"), "w").write("\n".join(out))
