"""How much the standing breathing additive (AS_fp_bh_stand_idle_long, applied only when not moving) moves the grabbing hand
(rel camera) - the 'normal' wobble a LeftHand-slot hold would remove at rest."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv = [sys.argv[0], "15"]
exec(open(os.path.join(HERE, "sim.py"), encoding="utf-8").read().split("out = []")[0])
base = full("idle", 0); look_delta = ms_delta(sk, full("look", 15), full("idle", 0)); g0 = full("grab", 0)
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
Cs, cvb, _ = compose("stand", base, None, gdelta, "none", look_delta); still = vsub(Cs[H][1], cvb[1])
d1, d2 = [], []
for k in S["idle_long"]["frames"]:
    md = ms_delta(sk, full("idle_long", k), base)
    C, c, _ = compose("stand", base, md, gdelta, "none", look_delta); d1.append(vlen(vsub(vsub(C[H][1], c[1]), still)))
    C, c, _ = compose("stand", base, md, gdelta, "c_lefthand_local", look_delta); d2.append(vlen(vsub(vsub(C[H][1], c[1]), still)))
print(f"idle_long (first 20 s, every 10th frame): hand rel cam moves {min(d1):.1f}-{max(d1):.1f} cm vanilla; with a LeftHand rest hold {min(d2):.1f}-{max(d2):.1f} cm")
