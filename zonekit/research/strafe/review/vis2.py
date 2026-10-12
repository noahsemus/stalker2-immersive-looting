import pickle, sys
exec(open("vis.py").read().split("gdelta = ")[0])
from collections import Counter
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
allv = SK["verts"][::5]
for mv, i in (("idle", None), ("walk_right", 10), ("walk_left", 10)):
  for look in (15, 23, 29):
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    lp = copy(base) if i is None else apply_ms(sk, base, deltas(mv)[i])
    C, cam = finish(lp, gdelta, slot_X(X_of(s3_in_cam(comp(sk, lp)))) if i is not None else None, ld)
    vis = Counter(max(v[1], key=lambda x: x[1])[0] for v in allv if visible(incam(cam, skin(C, v))))
    # nearest-to-view mixed vertex: min off-axis angle among mixed with x>0
    best = 999
    for v in mixed:
        c = incam(cam, skin(C, v))
        if c[0] > 0: best = min(best, max(abs(math.degrees(math.atan2(c[1], c[0]))) - HF, abs(math.degrees(math.atan2(c[2], c[0]))) - VF))
    print(mv, look, "visible verts by dominant bone:", vis.most_common(8), "| mixed: closest to frustum edge (deg outside)", round(best, 1))
