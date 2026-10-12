"""Same fixes as sim.py, but measuring the hand against the jnt_camera BONE (= if the CopyBone VB jnt_camera->jnt_camera were off)."""
import sys, os
sys.argv = [sys.argv[0], "15"]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import importlib.util
src = open(os.path.join(HERE, "sim.py"), encoding="utf-8").read().split("out = []")[0]   # definitions only
exec(src)
st = "stand"; cfg = STANCES[st]; base = full("idle", 0)
look_delta = ms_delta(sk, full("look", 15), full("idle", 0)); g0 = full("grab", 0)
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
Cs, cvb_s, cb_s = compose(st, base, None, gdelta, "none", look_delta)
still = vsub(Cs[H][1], cb_s[1])
for fix in ("none", "a_twist_ideal", "b_mainaction_idle_legsmask", "d_curve_AdditiveMovingUpperBody"):
    cells = []
    for mv, mb in cfg["moves"]:
        ref = full(mb, 0); d = []
        for k in S[mv]["frames"]:
            C, cvb, cb = compose(st, base, ms_delta(sk, full(mv, k), ref), gdelta, fix, look_delta)
            d.append(vlen(vsub(vsub(C[H][1], cb[1]), still)))
        cells.append(f"{mv} {min(d):.1f}-{max(d):.1f}")
    print(f"{fix:34s} hand vs jnt_camera bone: " + " | ".join(cells))
