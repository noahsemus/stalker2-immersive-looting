import json, struct, os, sys, math, itertools, pickle
from common import *
G = r"C:/Users/noahs/AppData/Local/Temp/stalker2-harness/rev_gltf/"
g = json.load(open(G + "SK_han_00_a.gltf")); binb = open(G + "SK_han_00_a.bin", "rb").read()
CT = {5126: ("f", 4), 5123: ("H", 2), 5121: ("B", 1), 5125: ("I", 4)}; NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
def acc(i):
    a = g["accessors"][i]; bv = g["bufferViews"][a["bufferView"]]
    fmt, sz = CT[a["componentType"]]; n = NC[a["type"]]; off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", sz * n)
    return [struct.unpack_from("<" + fmt * n, binb, off + k * stride) for k in range(a["count"])]
skin = g["skins"][0]; jn = [g["nodes"][j]["name"] for j in skin["joints"]]
IBM = acc(skin["inverseBindMatrices"])
verts = []
for prim in g["meshes"][0]["primitives"]:
    A = prim["attributes"]
    P = acc(A["POSITION"]); J0 = acc(A["JOINTS_0"]); J1 = acc(A["JOINTS_1"]); W0 = acc(A["WEIGHTS_0"]); W1 = acc(A["WEIGHTS_1"])
    for p, j0, j1, w0, w1 in zip(P, J0, J1, W0, W1):
        inf = [(jn[j], w) for j, w in zip(j0 + j1, w0 + w1) if w > 0]
        verts.append((p, inf))
print("verts", len(verts))
from collections import Counter
cnt = Counter(); 
for p, inf in verts:
    for b, w in inf: cnt[b] += 1
print("influences:", cnt.most_common(40))
# rest-pose in UE: refpose
REF = to_pose(D["refpose"]); CR = comp(sk, REF)
def m4(ib):  # glTF column-major
    return [[ib[c*4 + r] for c in range(4)] for r in range(4)]
def mv(M, v): return tuple(sum(M[r][c] * (v[c] if c < 3 else 1.0) for c in range(4)) for r in range(3))
# find C: UE = C^-1 gltf ; try signed permutations with scale 100
best = None
sample = [v for v in verts[::200] if v[1]][:60]
for perm in itertools.permutations(range(3)):
    for sg in itertools.product((1, -1), repeat=3):
        def cinv(v): return tuple(sg[k] * v[perm[k]] * 100.0 for k in range(3))
        err = 0
        for p, inf in sample:
            ue = cinv(p)
            acc_ = (0, 0, 0)
            for b, w in inf:
                j = jn.index(b); loc = cinv(mv(m4(IBM[j]), p))
                q, t = CR[I[b]]; wp = vadd(t, qrot(q, loc)); acc_ = vadd(acc_, vmul(wp, w))
            err = max(err, vlen(vsub(acc_, ue)))
        if best is None or err < best[0]: best = (err, perm, sg)
print("best C^-1", best)
err, perm, sg = best
def cinv(v): return tuple(sg[k] * v[perm[k]] * 100.0 for k in range(3))
# store vertices as (ue rest pos, [(bone, w, local_pos_in_bone_UE)])
VL = []
for p, inf in verts:
    L = []
    for b, w in inf:
        j = jn.index(b); L.append((b, w, cinv(mv(m4(IBM[j]), p))))
    VL.append((cinv(p), L))
pickle.dump(VL, open("han_verts.pkl", "wb"))
