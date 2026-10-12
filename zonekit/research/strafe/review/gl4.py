import json, struct, os, sys, math, itertools, pickle
from common import *
G = r"C:/Users/noahs/AppData/Local/Temp/stalker2-harness/rev_gltf/"
NAME = sys.argv[1] if len(sys.argv) > 1 else "SK_pla_skif_01"
g = json.load(open(G + NAME + ".gltf")); binb = open(G + NAME + ".bin", "rb").read()
CT = {5126: ("f", 4), 5123: ("H", 2), 5121: ("B", 1), 5125: ("I", 4)}; NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
def acc(i):
    a = g["accessors"][i]; bv = g["bufferViews"][a["bufferView"]]
    fmt, sz = CT[a["componentType"]]; n = NC[a["type"]]; off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", sz * n)
    return [struct.unpack_from("<" + fmt * n, binb, off + k * stride) for k in range(a["count"])]
skin = g["skins"][0]; jn = [g["nodes"][j]["name"] for j in skin["joints"]]
IBM = acc(skin["inverseBindMatrices"])
def inv_affine(ib):
    M = [[ib[c*4 + r] for c in range(4)] for r in range(4)]
    R = [row[:3] for row in M[:3]]; t = [M[r][3] for r in range(3)]
    # inverse of rotation*scale part via transpose assumption (orthonormal): bind translation = -R^T t
    Rt = [[R[c][r] for c in range(3)] for r in range(3)]
    return tuple(-sum(Rt[r][c] * t[c] for c in range(3)) for r in range(3))
REF = to_pose(D["refpose"]); CR = comp(sk, REF)
jpos = {jn[j]: inv_affine(IBM[j]) for j in range(len(jn))}
best = None
for perm in itertools.permutations(range(3)):
    for sg in itertools.product((1, -1), repeat=3):
        def cinv(v): return tuple(sg[k] * v[perm[k]] * 100.0 for k in range(3))
        e = max(vlen(vsub(cinv(jpos[b]), CR[I[b]][1])) for b in ("jnt_l_shoulder", "jnt_l_hand", "jnt_spine_03", "jnt_r_hand", "jnt_l_foot") if b in jpos)
        if best is None or e < best[0]: best = (e, perm, sg)
print(NAME, "joint-pos fit", best)
e, perm, sg = best
def cinv(v): return tuple(sg[k] * v[perm[k]] * 100.0 for k in range(3))
print("max joint mismatch vs refpose over all joints:", max((vlen(vsub(cinv(jpos[b]), CR[I[b]][1])), b) for b in jpos if b in I))
verts = []
for prim in g["meshes"][0]["primitives"]:
    A = prim["attributes"]
    P = acc(A["POSITION"]); Js = [acc(A[k]) for k in sorted(A) if k.startswith("JOINTS")]; Ws = [acc(A[k]) for k in sorted(A) if k.startswith("WEIGHTS")]
    for idx, p in enumerate(P):
        jj = sum((Js[k][idx] for k in range(len(Js))), ()); ww = sum((Ws[k][idx] for k in range(len(Ws))), ())
        inf = [(jn[j], w) for j, w in zip(jj, ww) if w > 0]
        v = cinv(p)
        L = [(b, w, tmul(tinv(CR[I[b]]), (QI, v))[1]) for b, w in inf]
        verts.append((v, L))
# shoulder subtree
SUB = set()
for i in range(len(B)):
    j = i
    while j >= 0:
        if B[j] == "jnt_l_shoulder": SUB.add(B[i]); break
        j = D["parents"][j]
mixed = [v for v in verts if any(b in SUB for b, _, _ in v[1]) and any(b not in SUB for b, _, _ in v[1])]
pure = [v for v in verts if all(b in SUB for b, _, _ in v[1])]
print("verts", len(verts), "shoulder-subtree only", len(pure), "MIXED shoulder+other", len(mixed))
from collections import Counter
print("mixed partner bones:", Counter(b for v in mixed for b, _, _ in v[1] if b not in SUB).most_common(8))
print("mixed shoulder-side bones:", Counter(b for v in mixed for b, _, _ in v[1] if b in SUB).most_common(8))
pickle.dump({"verts": verts, "mixed": mixed, "SUB": SUB}, open(f"skin_{NAME}.pkl", "wb"))
