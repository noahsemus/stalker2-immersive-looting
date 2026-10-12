from agrid import *
def eul(q):
    f = qrot(q, (1,0,0)); l = qrot(q, (0,1,0))
    return round(math.degrees(math.atan2(f[1], f[0])),1), round(math.degrees(math.asin(max(-1,min(1,f[2])))),1), round(math.degrees(math.atan2(l[2], qrot(q,(0,0,1))[2])),1)
gdelta = local_delta(full("grab", 44 * 45 + 15), g0)
for mv in ("turn90r", "walk_left", "run_left", "jog_fwd"):
    for i in (0, len(deltas(mv))//3, 2*len(deltas(mv))//3):
        lp = apply_ms(sk, base, deltas(mv)[i]); C = comp(sk, lp)
        out = [mv, i, "VBcam yaw/pitch/roll", eul(C[VCAM][0]), "pos", tuple(round(x,1) for x in C[VCAM][1])]
        for look in (15, 23):
            ld = ms_delta(sk, full("look", look), full("idle", 0))
            Cs, cams = finish(copy(base), gdelta, None, ld); still = handcam(Cs, cams)
            Ce, came = finish(lp, gdelta, slot_X(X_of(s3_in_cam(C))), ld)
            out += [f"look{look} exact err", round(vlen(vsub(handcam(Ce, came), still)), 1)]
        print(*out)
