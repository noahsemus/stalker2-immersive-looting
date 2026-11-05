src = open("gen_bagfix.py").read().replace("\nmain()\n", "\n")
exec(compile(src, "gen_bagfix.py", "exec"))
idle = raw("bag_idle", 0)
def elev(v):  # degrees above the view centre, and sideways
    return round(math.degrees(math.atan2(v[2], v[0])), 0), round(math.degrees(math.atan2(v[1], v[0])), 0)
for bname, base_key, look, lookbase in BLOCKS:
    for p in (0.0, -40.0, -70.0):
        d = fix_delta(pre_table(base_key, look, lookbase, p, idle), idle)
        o18 = raw("bag_out", 18)
        rows = []
        for w in (0.0, 0.25, 0.5, 0.75, 1.0):
            base = raw(base_key, 0)
            arm = lbb_local(sk, o18, base, [w] * len(B))     # the slot blending out to the rest
            for mode in ("a", "b"):
                pose = pre_table(base_key, look, lookbase, p, arm)
                out = apply_ms(sk, pose, d, w=(1.0 if mode == "a" else 1.0 - w))
                Co = comp(sk, out); cam = comp(sk, pose)[VCAM]
                rows.append(f"{mode} w{w}: L {view(Co, cam, p, LW)} {elev(view(Co, cam, p, LW))} R {elev(view(Co, cam, p, RH))}")
        print(bname, p); print("   " + "\n   ".join(rows))
