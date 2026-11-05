"""aa probe: block 19 (crouch) gave the bag at (36, -23, +21) at -48 / (31, -20, +24) at -47 in view axes. Which real
pose + block gives that?"""
import json
from bagsim import *
K = json.load(open(os.path.join(HERE, "bagfix_keys.json")))
fr = [[None] * len(B) for _ in range(K["frames"])]
base0 = raw("idle", 0)
def frame(n):
    p = [list(x) for x in base0]
    for b in K["tracks"]:
        q, t = K["keys"][b][n]; p[I[b]] = [tuple(q), tuple(t)]
    return vb_fix(p)
def tdelta(block, pitch):
    pos = min(18, max(0, -pitch / 5)) + block + 1
    k0 = int(math.floor(pos)); a = pos - k0
    f = frame(k0) if a < 1e-6 else lbb_local(sk, frame(k0), frame(k0 + 1), [a] * len(B))
    return ms_delta(sk, f, base0)
STANCES = {"stand": ("idle", "look", "idle"), "crouch(stdlook)": ("idle_crouch", "look", "idle"),
           "crouch(nolook)": ("idle_crouch", None, None), "lowcrouch": ("idle_lowcrouch", "look_lowcrouch", "idle_lowcrouch"),
           "crouch(lclook)": ("idle_crouch", "look_lowcrouch", "idle_lowcrouch")}
bag = raw("bag_idle", 0)
for pitch in (-48.0, -47.0, -36.0):
    for sn, (bk, lk, lb) in STANCES.items():
        pose = raw(bk, 0)
        pose = lbb_local(sk, pose, bag, RM); pose = lbb_local(sk, pose, bag, LM)
        if lk: pose = apply_ms(sk, pose, look_pose_delta(lk, lb, pitch))
        cam = comp(sk, pose)[VCAM]
        for blk in (0, 19, 38):
            out = apply_ms(sk, pose, tdelta(blk, pitch))
            C = comp(sk, out)
            print(f"pitch {pitch:+.0f} {sn:16} blk {blk:2}: bag {view(C, cam, pitch)} L {view(C, cam, pitch, LH)}  camZ {cam[1][2]:.1f}")
