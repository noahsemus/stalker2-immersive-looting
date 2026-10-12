import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from simcore import *
D = json.load(open(os.path.join(os.path.dirname(__file__), "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
S = D["seqs"]
def full(key, k):
    s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
idle0 = full("idle", 0)
# scales
mx = 0
for key, s in S.items():
    for fr in s["full"][:3]:
        for r in fr: mx = max(mx, abs(r[7]-1), abs(r[8]-1), abs(r[9]-1))
print("max |scale-1| in full poses:", mx)
# VB parents: VB local vs target bone relative to candidate sources
C = comp(sk, idle0)
for vb in [b for b in B if b.startswith("VB ")]:
    i = I[vb]; q, t = idle0[i]
    best = []
    for j, b in enumerate(B):
        if b.startswith("VB "): continue
        pq, pt = C[j]
        for tb in B:
            pass
    # assume target = name after 'VB ' ; try every source
    tgt = vb[3:]
    if tgt in I:
        tq, tt = C[I[tgt]]
        for j, b in enumerate(B):
            if b.startswith("VB "): continue
            pq, pt = C[j]
            rel_t = qrot(qinv(pq), vsub(tt, pt)); rel_q = qmul(qinv(pq), tq)
            if vlen(vsub(rel_t, t)) < 0.01 and qangle(rel_q, q) < 0.05: best.append(b)
    print(vb, "local t", tuple(round(x, 2) for x in t), "matches source candidates:", best[:5])
# additive math check: walk_left
for key, base in (("walk_left", idle0), ("run_right", idle0), ("lowcrouch_left", full("idle_lowcrouch", 0))):
    s = S[key]
    for kstr, adds in s["add"].items():
        k = int(kstr)
        mine = ms_delta(sk, full(key, k), base)
        ue = to_pose(adds["raw"])
        ra = max(qangle(a[0], b[0]) for a, b in zip(mine, ue)); ta = max(vlen(vsub(a[1], b[1])) for a, b in zip(mine, ue))
        # also test local-delta convention (should NOT match)
        ml = local_delta(full(key, k), base)
        rl = max(qangle(a[0], b[0]) for a, b in zip(ml, ue))
        # apply UE compressed additive to base, compare to UE compressed full
        uec = to_pose(adds["comp"]); fullc = to_pose(s["fullcomp"][kstr])
        app = apply_ms(sk, base, uec)
        Ca, Cf = comp(sk, app), comp(sk, fullc)
        pa = max(vlen(vsub(a[1], b[1])) for a, b in zip(Ca, Cf))
        # raw full vs comp full: compression error on the hand
        Cr = comp(sk, full(key, k))
        ce = vlen(vsub(Cr[I['jnt_l_hand']][1], Cf[I['jnt_l_hand']][1]))
        print(f"{key} f{k}: my mesh delta vs UE additive: max rot {ra:.3f} deg, trans {ta:.3f}; local-delta convention max rot {rl:.2f} deg | apply(UE comp add) vs UE comp full: max comp pos err {pa:.3f} cm | raw vs compressed hand {ce:.2f} cm")
# grab
g = S["grab"]
g0 = full("grab", 0)
tr = D["meta"]["grab"]["tracks"]
d0 = max(qangle(g0[I[b]][0], idle0[I[b]][0]) for b in tr)
print("grab frame0 vs idle0 on tracked bones max rot diff", round(d0, 3), "deg")
for kstr, adds in g["add"].items():
    k = int(kstr)
    mine = local_delta(full("grab", k), g0); ue = to_pose(adds["raw"])
    ra = max(qangle(a[0], b[0]) for a, b in zip(mine, ue)); ta = max(vlen(vsub(a[1], b[1])) for a, b in zip(mine, ue))
    app = apply_local(idle0, ue); Ca = comp(sk, app); Cg = comp(sk, full("grab", k))
    he = vlen(vsub(Ca[I['jnt_l_hand']][1], Cg[I['jnt_l_hand']][1]))
    print(f"grab f{k}: my local delta vs UE additive: max rot {ra:.3f} deg trans {ta:.3f}; idle0 + UE additive -> hand vs grab full frame: {he:.3f} cm")
# which bones does the walk animate (local change across frames)?
for key in ("walk_left", "run_left", "lowcrouch_left"):
    s = S[key]; frs = [to_pose(f) for f in s["full"]]
    for b in ("jnt_root", "jnt_camera", "VB jnt_camera", "jnt_hips"):
        i = I[b]
        tv = max(vlen(vsub(f[i][1], frs[0][i][1])) for f in frs); rv = max(qangle(f[i][0], frs[0][i][0]) for f in frs)
        t0 = vlen(vsub(frs[0][i][1], idle0[i][1])); r0 = qangle(frs[0][i][0], idle0[i][0])
        print(f"  {key} {b}: vs idle0 at f0: {t0:.2f} cm {r0:.1f} deg; range over frames {tv:.2f} cm {rv:.1f} deg")
