exec(open("r11.py").read().split("gdelta = local_delta")[0])
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
ld = ms_delta(sk, full("look", 15), full("idle", 0))
Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
rows = []
for name, spec in TE:
    if not name.startswith("run_") or "+" in name: continue
    lp = pose_from(spec); s3c = s3_in_cam(comp(sk, lp))
    C, cam = finish(lp, gdelta, slot_X(grids["run"].lookup(s3c)), ld); e = vlen(vsub(handcam(C, cam), still))
    y,p,ro,x,yy,z = feats6(s3c); rows.append((e, name, round(y), round(p), round(math.degrees(math.atan2(yy,-x))), round(math.hypot(x,yy)), round(z)))
rows.sort(reverse=True)
for r in rows[:12]: print(r)
