import pickle, sys
exec(open("vis.py").read().split("gdelta = ")[0])
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
ld = ms_delta(sk, full("look", 23), full("idle", 0))
C, cam = finish(copy(base), gdelta, None, ld)
print("cam", cam)
print("hand bone in cam", incam(cam, C[H][1]))
hv = [v for v in SK["verts"] if v[1] and max(v[1], key=lambda x: x[1])[0] == "jnt_l_hand"][:3]
for v in hv: print("hand vert rest", v[0], "skinned in cam", incam(cam, skin(C, v)), [ (b, round(w,2)) for b, w, _ in v[1]])
CR0 = comp(sk, to_pose(D["refpose"]))
print("refpose l_hand", CR0[H][1], " idle l_hand", comp(sk, base)[H][1])
v = hv[0]; print("idle-skinned hand vert (no grab) comp", skin(comp(sk, base), v), "ref-skinned", skin(CR0, v))
