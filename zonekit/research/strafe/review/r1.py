import json, sys, os, math
SIM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim"); sys.path.insert(0, SIM)
from simcore import *
D = json.load(open(os.path.join(SIM, "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
print("parent of jnt_l_shoulder:", B[D["parents"][I["jnt_l_shoulder"]]])
print("parent of jnt_spine_03:", B[D["parents"][I["jnt_spine_03"]]], " jnt_camera:", B[D["parents"][I["jnt_camera"]]], " VB jnt_camera raw parent:", D["parents"][I["VB jnt_camera"]])
for k, m in D["meta"].items(): print(k, m["frames"], round(m["len"],3), m["additive"], m["ref"], m["refseq"], "curves", m["curves"][:6])
S = D["seqs"]
def full(key, k): s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03", "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
base = full("idle", 0)
# look deltas: which bones change
for lk, lb in (("look", "idle"), ("look_lowcrouch", "idle_lowcrouch")):
    n = len(S[lk]["frames"])
    for f in (0, n//4, n//2, 3*n//4, n-1):
        d = ms_delta(sk, full(lk, f), full(lb, 0))
        big = sorted(((qangle(dq, QI), vlen(dt), B[i]) for i, (dq, dt) in enumerate(d)), reverse=True)
        print(lk, f, "top rot:", [(round(a,1), round(t,1), b) for a, t, b in big[:6]])
        bigt = sorted(((vlen(dt), B[i]) for i, (dq, dt) in enumerate(d)), reverse=True)[:4]
        print("     top trans:", [(round(a,2), b) for a, b in bigt])
