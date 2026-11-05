from bagsim import *
for k in ("idle", "idle_crouch", "idle_lowcrouch", "ar_idle"):
    C = comp(sk, raw(k, 0)); print(k, "camera", tuple(round(x, 1) for x in C[CAM][1]), "VB cam", tuple(round(x,1) for x in C[VCAM][1]), "spine3", tuple(round(x,1) for x in C[SP3][1]))
