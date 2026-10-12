import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from simcore import *
D = json.load(open(os.path.join(os.path.dirname(__file__), "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03", "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
idle0 = to_pose(D["seqs"]["idle"]["full"][0])
for key, basek in (("walk_left", "idle"), ("look", "idle"), ("lowcrouch_left", "idle_lowcrouch")):
    s = D["seqs"][key]; base = to_pose(D["seqs"][basek]["full"][0])
    for kstr, adds in s["add"].items():
        k = int(kstr); ue = to_pose(adds["raw"]); mine = ms_delta(sk, to_pose(s["full"][s["frames"].index(k)]), base)
        diff = sorted(((qangle(a[0], b[0]), B[i]) for i, (a, b) in enumerate(zip(mine, ue))), reverse=True)[:3]
        sel = {b: round(qangle(ue[I[b]][0], QI), 1) for b in ("jnt_spine_01", "jnt_spine_03", "jnt_l_shoulder", "jnt_l_arm", "jnt_camera", "VB jnt_camera")}
        print(key, k, "worst mine-vs-UE:", [(round(a, 3), b) for a, b in diff], "UE delta deg:", sel)
