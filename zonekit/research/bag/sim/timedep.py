src = open("gen_bagfix.py").read().replace("\nmain()\n", "\n")
exec(compile(src, "gen_bagfix.py", "exec"))
idle = raw("bag_idle", 0)
for bname, base_key, look, lookbase in BLOCKS:
    for p in (0.0, -30.0, -60.0):
        d_idle = fix_delta(pre_table(base_key, look, lookbase, p, idle), idle)
        errs = []
        for bk, bf in TS:
            bag = raw(bk, bf); Ca = comp(sk, bag)
            pose = pre_table(base_key, look, lookbase, p, bag)
            out = apply_ms(sk, pose, d_idle); Co = comp(sk, out); cam = comp(sk, pose)[VCAM]
            X = qmul(cam[0], qinv(Ca[CAM][0]))
            e = max(vlen(vsub(Co[b][1], vadd(cam[1], qrot(X, vsub(Ca[b][1], Ca[CAM][1]))))) for b in (LW, RH))
            errs.append((round(e, 1), f"{bk}[{bf}]"))
        print(bname, p, "worst with the Idle's correction:", sorted(errs, reverse=True)[:5], " out:", [e for e in errs if e[1].startswith("bag_out")][::4])
