"""Generalisation: NN table trained on left/right strafes only, tested on walk forward (not in the table) and on a 50/50
left+forward mix (diagonal-like)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv = [sys.argv[0], "15", "6", "0.25,0.5,0.75,1.0", "seg"]
src = open(os.path.join(HERE, "sim3.py"), encoding="utf-8").read().split("SEGS = {")[0]
exec(src)
DELTAS["walk_fwd"] = [ms_delta(sk, full("walk_fwd", k), full("idle", 0)) for k in S["walk_fwd"]["frames"]]
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
Cs, cams = finish(copy(base), gdelta); still = vsub(Cs[H][1], cams[1])
for name, mk in (("walk_fwd", lambda i: loco("walk_fwd", i)),
                 ("0.5 left + 0.5 fwd", lambda i: apply_ms(sk, apply_ms(sk, base, DELTAS["walk_left"][i], w=0.5), DELTAS["walk_fwd"][i], w=0.5))):
    r = {}
    for var in ("none", "f_nn_table"):
        m = 0
        for i in range(0, 74, 2):
            lp = mk(i); C0 = comp(sk, lp); s3c = s3_in_cam(C0)
            slot = None if var == "none" else slot_from_s3cam(nn(s3c))
            C, cam = finish(lp, gdelta, slot); m = max(m, vlen(vsub(vsub(C[H][1], cam[1]), still)))
        r[var] = m
    print(f"{name}: max hand displacement none {r['none']:.1f} cm, f_nn_table (trained on left/right only) {r['f_nn_table']:.1f} cm")
