import sys
sys.argv = ["x"]
src = open("gen_bagfix.py").read().replace("\nmain()\n", "\n")
exec(compile(src, "gen_bagfix.py", "exec"))
bag = raw("bag_idle", 0); Ca = comp(sk, bag)
for p in (0.0, -45.0):
    pose = pre_table("idle", "look", "idle", p, bag)
    d = fix_delta(pose, bag)
    out = apply_ms(sk, pose, d)
    C = comp(sk, pose); Co = comp(sk, out); cam = C[VCAM]
    X = qmul(cam[0], qinv(Ca[CAM][0]))
    for b in ("jnt_l_shoulder", "jnt_l_arm", "jnt_l_fore_arm", "jnt_l_hand", "jnt_l_weapon"):
        i = I[b]
        want = vadd(cam[1], qrot(X, vsub(Ca[i][1], Ca[CAM][1])))
        wantq = qmul(X, Ca[i][0])
        print(p, b, "pos err", round(vlen(vsub(Co[i][1], want)), 2), "rot err", round(qangle(Co[i][0], wantq), 2), "in ARMS", i in ARMS)
    print("cam X elev", math.degrees(math.asin(qrot(cam[0], (1,0,0))[2])), "anim cam X elev", math.degrees(math.asin(qrot(Ca[CAM][0], (1,0,0))[2])))
