import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from simcore import *
D = json.load(open(os.path.join(os.path.dirname(__file__), "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03", "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
for key, basek in (("look", "idle"), ("look_lowcrouch", "idle_lowcrouch")):
    s = D["seqs"][key]; base = to_pose(D["seqs"][basek]["full"][0])
    for k in (0, 15, 29):
        p = to_pose(s["full"][k]); d = ms_delta(sk, p, base)
        moved = [(B[i], round(qangle(dq, QI), 1), round(vlen(dt), 2)) for i, (dq, dt) in enumerate(d) if qangle(dq, QI) > 0.5 or vlen(dt) > 0.2]
        print(key, k, moved[:20])
