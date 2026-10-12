import json, struct, os, sys, math, itertools, pickle
from common import *
exec(open("gl2.py").read().split("print(\"verts\"")[0].split("from common import *")[1])
from collections import Counter
cnt = Counter()
for p, inf in verts:
    for b, w in inf: cnt[b] += 1
print({b: cnt[b] for b in ("jnt_spine_03", "jnt_spine_02", "jnt_neck", "jnt_l_shoulder", "jnt_r_shoulder", "jnt_l_shoulder_roll", "jnt_l_shoulder_armor", "jnt_l_armor", "jnt_l_arm")})
xs = [p for p, _ in verts]
for k in range(3): print("gltf axis", k, min(v[k] for v in xs), max(v[k] for v in xs))
REF = to_pose(D["refpose"]); CR = comp(sk, REF)
print("ref l_shoulder", CR[I["jnt_l_shoulder"]][1], "l_arm", CR[I["jnt_l_arm"]][1], "l_hand", CR[I["jnt_l_hand"]][1], "spine_03", CR[I["jnt_spine_03"]][1])
