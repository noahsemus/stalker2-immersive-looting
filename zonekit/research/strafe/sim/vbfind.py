import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from simcore import *
D = json.load(open(os.path.join(os.path.dirname(__file__), "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
for key in ("idle", "walk_left"):
    p = to_pose(D["seqs"][key]["full"][0]); C = comp(sk, p)
    for vb in [b for b in B if b.startswith("VB ")]:
        q, t = p[I[vb]]; res = []
        for s, sb in enumerate(B):
            if sb.startswith("VB "): continue
            for g, gb in enumerate(B):
                if gb.startswith("VB "): continue
                pq, pt = C[s]; tq, tt = C[g]
                if vlen(vsub(qrot(qinv(pq), vsub(tt, pt)), t)) < 0.01 and qangle(qmul(qinv(pq), tq), q) < 0.05: res.append((sb, gb))
        print(key, vb, res[:4])
