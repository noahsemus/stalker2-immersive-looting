from common import *
import time, random
random.seed(1)
t0 = time.time()
print("bones", len(B))
# ---------- pose generators ----------
def pose_from(spec):
    """spec = list of (mv, phase, weight) -> base + ms additive of the blended delta"""
    ds = [phase_delta(mv, ph) for mv, ph, w in spec]; ws = [w for *_, w in spec]
    tw = sum(ws)
    if len(ds) == 1: return apply_ms(sk, base, ds[0], w=ws[0])
    d = blend_deltas(ds, [w / tw for w in ws])
    return apply_ms(sk, base, d, w=min(1.0, tw))
DIRS = ["left","right","fwd","fl","fr","bl","br","bwd"]
ADJ = [("left","fl"),("left","bl"),("fwd","fl"),("fwd","fr"),("right","fr"),("right","br"),("bwd","bl"),("bwd","br")]
def specs(train):
    W = (0.25, 0.5, 0.75, 1.0) if train else (0.15, 0.4, 0.65, 0.9, 1.0)
    PH = [i/12 for i in range(12)] if train else [i/12 + 1/24 for i in range(12)]
    out = []
    for g in ("walk", "run"):
        for d in DIRS:
            for w in W:
                for ph in PH: out.append((f"{g}_{d} w{w}", [(f"{g}_{d}", ph, w)]))
        for a, b in ADJ:
            for r in ((0.5,) if train else (0.3, 0.7)):
                for ph in PH[::2]: out.append((f"{g}_{a}+{b} {r}", [(f"{g}_{a}", ph, r), (f"{g}_{b}", ph, 1-r)]))
        for r in ((0.5, 0.25) if train else (0.4, 0.15)):
            for ph in PH[::2]: out.append((f"{g} L/R {r}", [(f"{g}_left", ph, r), (f"{g}_right", ph, 1-r)]))
    for d in DIRS:
        for r in ((0.5,) if train else (0.3, 0.7)):
            for ph in PH[::3]: out.append((f"walk/run_{d} {r}", [(f"walk_{d}", ph, r), (f"run_{d}", ph, 1-r)]))
    for m in ("jog_fwd", "sprint_fwd", "turn90r"):
        for w in ((0.5, 1.0) if train else (0.3, 0.8)):
            for ph in PH[::2]: out.append((f"{m} w{w}", [(m, ph, w)]))
    return out
TR, TE = specs(True), specs(False)
print("train", len(TR), "test", len(TE))
def s3c_of(spec):
    C = comp(sk, pose_from(spec)); return s3_in_cam(C)
TRS = [(n, s3c_of(sp)) for n, sp in TR]
print("train s3c done", round(time.time()-t0,1))
import pickle
pickle.dump({"TR": TR, "TE": TE, "TRS": TRS}, open("r5_sets.pkl", "wb"))
