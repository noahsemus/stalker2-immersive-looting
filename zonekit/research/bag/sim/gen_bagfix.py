"""v1.3.2 aa: the empty-hands bag table AS_ImmLoot_BagFix, computed with the bag simulator (bagsim.py, validated on
the h probe: standing -32 sim (29, -27, 11) / probe (29, -27, 9); crouched -25 sim (40, -16, -25) / probe (41, -16, -26)).

Why every earlier table missed: the bag sequences key the shoulders (clavicles) too, from a body leaning far forward
(the anim's shoulders sit 4.5 cm AHEAD of its camera and 29 cm below it); in the bare-hands layer the LeftHand /
RightHand slots copy those locals onto the upright bare-hands chest (shoulders 28 cm BEHIND the camera), and the
standing look additive then counter-turns the arms. No rotation about the shoulders alone (the pitch fix, the
lowering, the servo) can bring the bag down to where the anim holds it.

The table (mesh-space rotation offset additive, FullBody, reference = frame 0): for each stance block, each bag time
sample and each view pitch row, every arm bone gets the rotation that turns it to the anim's own orientation relative
to the camera (W = Kv * inv(Ka) * A_b: Kv the live camera, Ka the anim's camera, A_b the anim's bone), its local
translation back to the anim's (the standing look additive moves the forearm's by up to 31 cm), and the two
shoulder roots a local translation that puts them where the anim has them relative to the camera. The result is the
vanilla bag exactly as the game frames it (left hand / bag (39, -17, -26) cm in view axes at the Idle), at every pitch.

Layout: frame 0 = reference (bh idle); frame 1 + block * NP + pi, pi = pitch row (0 = 0 deg, 18 = -90 deg, 5 deg
steps; a fractional position blends two pitches). One correction for every bag time (the Idle's): the anim's camera
sits within 1.6 deg of its chest throughout, so the rotations barely change; the shoulders' lean does, but the hand /
bag stay within 4.5 cm of the anim up to the Out's frame 16 (8 cm at frame 18, below the view; timedep.py). With the
table still full while the Out's slot blends out, both hands leave downward (blendout.py). Blocks: 0 stand (camera >=
145 cm), 1 crouch (115..145: the standing look, unverified), 2 low crouch (< 115).
Output: bagfix_keys.json (local keys per frame for every track) for set_bagfix.py (editor), bagfix_check.txt."""
from bagsim import *

PITCHES = [-5.0 * i for i in range(19)]
TS_ALL = [("bag_in", k) for k in range(0, 46, 3)] + [("bag_idle", 0)] + [("bag_out", k) for k in range(21)]
TS = [("bag_idle", 0)]
BLOCKS = [("stand", "idle", "look", "idle"), ("crouch", "idle_crouch", "look", "idle"), ("lowcrouch", "idle_lowcrouch", "look_lowcrouch", "idle_lowcrouch")]
NP, NT = len(PITCHES), len(TS)
SHOULDERS = [I["jnt_l_shoulder"], I["jnt_r_shoulder"]]
TRACKS = [b for b in B if b in M["bag_in"]["tracks"] or I[b] in ARMS]   # the bag's 110 tracks + every arm mask bone


def pre_table(base_key, look, lookbase, pitch, bag):
    pose = raw(base_key, 0)
    pose = lbb_local(sk, pose, bag, RM)
    pose = lbb_local(sk, pose, bag, LM)
    pose = apply_ms(sk, pose, ms_delta(sk, vb_fix(look_pose(look, pitch)), raw(lookbase, 0)))
    return pose


def look_pose(look, pitch):
    f = (90.0 - pitch) / 6.0
    k0 = max(0, min(int(math.floor(f)), 29)); a = f - k0
    return lbb_local(sk, raw(look, k0), raw(look, k0 + 1), [a] * len(B)) if a > 1e-6 else raw(look, k0)


def fix_delta(pose, bag):
    """the mesh-space delta (rotation per arm bone, local translation on the shoulder roots) that puts the arms where
    the anim has them relative to the camera"""
    C = comp(sk, pose); R = ms_rot(sk, pose)
    Ca = comp(sk, bag)
    Kv, Pv = C[VCAM]          # CopyBone_2: the live camera = VB jnt_camera
    Ka, Pa = Ca[CAM]
    X = qmul(Kv, qinv(Ka))    # anim camera frame -> live camera frame
    d = [[QI, (0.0, 0.0, 0.0)] for _ in B]
    for i in ARMS:
        W = qmul(X, Ca[i][0])
        d[i][0] = qnorm(qmul(W, qinv(R[i])))
    for i in ARMS:            # the standing look additive also moves arm bones' local translations (the forearm
        d[i][1] = vsub(bag[i][1], pose[i][1])   # 31 cm at -60: the bare-hands "stretched sleeve"): back to the anim's
    for i in SHOULDERS:
        want = vadd(Pv, qrot(X, vsub(Ca[i][1], Pa)))
        par = sk.parents[i]
        d[i][1] = qrot(qinv(C[par][0]), vsub(want, C[i][1]))
    return d


def main():
    base0 = raw("idle", 0)
    R0 = ms_rot(sk, base0)
    frames = [base0]
    check = []
    worst = 0.0
    for bi, (bname, base_key, look, lookbase) in enumerate(BLOCKS):
        idle = raw("bag_idle", 0)
        for pi, p in enumerate(PITCHES):
            d = fix_delta(pre_table(base_key, look, lookbase, p, idle), idle)
            # the frame's keys: mesh rotations delta * reference, translations reference + delta
            Rk = [qnorm(qmul(d[i][0], R0[i])) for i in range(len(B))]
            Tk = [vadd(base0[i][1], d[i][1]) for i in range(len(B))]
            frames.append(from_ms_rot(sk, Rk, Tk))
            ue_d = ms_delta(sk, frames[-1], base0)   # the delta UE computes (frame vs the reference)
            for bk, bf in TS_ALL:
                bag = raw(bk, bf); Ca = comp(sk, bag)
                pose = pre_table(base_key, look, lookbase, p, bag)
                out = apply_ms(sk, pose, ue_d)
                Co = comp(sk, out); cam = comp(sk, pose)[VCAM]
                X = qmul(cam[0], qinv(Ca[CAM][0]))
                e = max(vlen(vsub(Co[b][1], vadd(cam[1], qrot(X, vsub(Ca[b][1], Ca[CAM][1]))))) for b in (LW, RH))
                if not (bk == "bag_out" and bf > 16) and bk != "bag_in":
                    worst = max(worst, e)
                if (bk == "bag_idle" and pi % 3 == 0) or (bk == "bag_out" and bf in (0, 8, 16) and pi in (0, 9, 12)):
                    ang = max(qangle(d[i][0], QI) for i in ARMS)
                    sh = max(vlen(d[i][1]) for i in SHOULDERS)
                    check.append(f"{bname} {bk}[{bf}] pitch {p:+.0f}: l_weapon view {view(Co, cam, p)} (anim {anim_view(bk, bf / 30.0)[0]}), "
                                 f"err {e:.1f} cm, max arm turn {ang:.0f} deg, shoulder move {sh:.1f} cm, before {view(comp(sk, pose), cam, p)}")
    check.append(f"worst |left weapon bone / right hand - anim| (Idle, Out to frame 16): {worst:.2f} cm; frames {len(frames)} (NP {NP} x {len(BLOCKS)} + 1)")
    keys = {}
    for b in TRACKS:
        i = I[b]
        keys[b] = [[list(f[i][0]), list(f[i][1])] for f in frames]
    json.dump({"tracks": TRACKS, "frames": len(frames), "np": NP, "nt": NT, "keys": keys}, open(os.path.join(HERE, "bagfix_keys.json"), "w"))
    open(os.path.join(HERE, "bagfix_check.txt"), "w").write("\n".join(check))
    print("\n".join(check))


main()
