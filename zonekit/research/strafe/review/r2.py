import json, sys, os, math
SIM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sim"); sys.path.insert(0, SIM)
from simcore import *
D = json.load(open(os.path.join(SIM, "simdump.json")))
sk = Skel(D); B = sk.bones; I = sk.idx
VBP = {"VB jnt_r_knee_target": "jnt_r_foot", "VB jnt_l_knee_target": "jnt_l_foot", "VB jnt_camera": "jnt_spine_03", "VB jnt_weapon": "jnt_spine_03", "VB jnt_item": "jnt_spine_03", "VB jnt_r_hand_jnt_weapon": "jnt_r_hand"}
for v, p in VBP.items(): sk.parents[I[v]] = I[p]
sk.order = sk._order()
S = D["seqs"]
def full(key, k): s = S[key]; return to_pose(s["full"][s["frames"].index(k)])
def tmul(a, b): return (qmul(a[0], b[0]), vadd(a[1], qrot(a[0], b[1])))
def tinv(a): qi = qinv(a[0]); return (qi, qrot(qi, vmul(a[1], -1)))
def eul(q):
    f = qrot(q, (1,0,0)); l = qrot(q,(0,1,0))
    yaw = math.degrees(math.atan2(f[1], f[0])); pit = math.degrees(math.atan2(f[2], math.hypot(f[0], f[1])))
    return yaw, pit
base = full("idle", 0)
VC, S3, SH, H = I["VB jnt_camera"], I["jnt_spine_03"], I["jnt_l_shoulder"], I["jnt_l_hand"]
print("frame | ms-delta deg: spine_03 VBcam l_sh l_arm | VBcam comp yaw/pitch | spine_03 comp pos | hand rel VBcam (cam axes) | s3-in-cam pos")
for f in range(0, 30, 3):
    d = ms_delta(sk, full("look", f), base)
    p = apply_ms(sk, base, d); C = comp(sk, p)
    hc = tmul(tinv(C[VC]), C[H])[1]; s3c = tmul(tinv(C[VC]), C[S3])
    print(f, [round(qangle(d[i][0], QI),1) for i in (S3, VC, SH, I["jnt_l_arm"])], tuple(round(x,1) for x in eul(C[VC][0])), tuple(round(x,1) for x in C[S3][1]), tuple(round(x,1) for x in hc), tuple(round(x,1) for x in s3c[1]), round(qangle(s3c[0], tmul(tinv(comp(sk,base)[VC]), comp(sk,base)[S3])[0]),1))
