exec(open("r16.py").read().split("gdelta = local_delta")[0])
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
for look in (15, 23):
    ld = ms_delta(sk, full("look", look), full("idle", 0))
    Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
    dv, dt_, dx = [], [], []
    for k in S["idle_long"]["frames"]:
        md = ms_delta(sk, full("idle_long", k), base); lp = apply_ms(sk, base, md); s3c = s3_in_cam(comp(sk, lp))
        C, cam = finish(lp, gdelta, None, ld); dv.append(vlen(vsub(handcam(C, cam), still)))
        C, cam = finish(lp, gdelta, slot_X(G[fam_by_pitch(s3c)].lookup(s3c)), ld); dt_.append(vlen(vsub(handcam(C, cam), still)))
        C, cam = finish(lp, gdelta, slot_X(X_of(s3c)), ld); dx.append(vlen(vsub(handcam(C, cam), still)))
    print(f"look{look} standing breathing (idle_long, 20 s): hand moves vanilla {min(dv):.1f}-{max(dv):.1f} cm | C1 table {min(dt_):.1f}-{max(dt_):.1f} | exact {min(dx):.1f}-{max(dx):.1f}")
