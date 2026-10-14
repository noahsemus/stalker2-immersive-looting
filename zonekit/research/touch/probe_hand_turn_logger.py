# Patch script (2026-10-13, builds t / y): inserts the probe logger into zonekit/tools/gen_actor_looting.py. The
# anchors it replaces are from that day (the "_sqpf = sequence(...)" line and the "#   (probe, build l" comment were
# removed in the v1.2.0 cleanup): re-anchor before reuse. Run from the repo root with the kit Python, then
# setup_assets (variables), regenerate the paste, and add the variable names to the probe main.lua.
p = "zonekit/tools/gen_actor_looting.py"
c = open(p, encoding="utf-8").read()


def rep(a, b, n=1):
    global c
    assert c.count(a) == n, (a[:60], c.count(a))
    c = c.replace(a, b)


rep('_sqpf = sequence(X4 - 400, Y4 + 8600, "pitch fix, bag shown, Out ended, weapon shown, then the probe", 6)',
    '_sqpf = sequence(X4 - 400, Y4 + 8600, "pitch fix, bag shown, Out ended, weapon shown, then the probes", 7)')
LOGGER = r'''#   build t probe (tester: "no change. do you have a logger so you can see it?"): how fast the left hand turns, in the
#   camera bone's frame, for 2.5 s from our reach's start or its way back (the later): per tick, the larger angle of its
#   forward and up axes and of the forearm's up axis (twist) (TwStep, deg); the largest (TwMax, at montage position
#   TwMaxPos, TwMaxT s in), the sums (TwSum; TwLate = from montage position 1.1 s), steps over 20 deg (NTwBig)
LX_, LY_ = X4 + 300, Y4 + 12000
g.box("EdGraphNode_Comment_955", LX_ - 800, LY_ - 200, 4600, 1400, "Probe (build t): left-hand turn rate after a reach")
_tcam = member_pure(SC_, "GetSocketTransform", LX_ - 700, LY_ + 300, mesh, [
    ("InSocketName", "name", dict(extra='DefaultValue="jnt_camera",')),
    ("TransformSpace", "byte", dict(sub=EN("/Script/Engine.ERelativeTransformSpace"), extra='DefaultValue="RTS_World",')),
    ("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]


def _tw_axis(x, y, bone, fn):
    r = member_pure(SC_, "GetSocketRotation", x - 400, y, mesh, [("InSocketName", "name", dict(extra=f'DefaultValue="{bone}",')),
                                                              ("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
    a = kml(fn, x - 200, y, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(r, a["InRot"])
    n = kml("InverseTransformDirection", x, y, [("T", "struct", dict(sub=XFORM)), ("Direction", "struct", dict(sub=VEC)),
                                                ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_tcam, n["T"])
    g.link(a["ReturnValue"], n["Direction"])
    return n["ReturnValue"]


def _tw_ang(x, y, cur, prev_var):
    d = vop("Dot_VectorVector", x, y, cur, self_get(prev_var, "struct", x - 200, y + 80, sub=VEC), ret_sub="real")
    cl = kml("FClamp", x + 150, y, [D("Value"), D("Min", "-1.0"), D("Max", "1.0"), RD])
    g.link(d, cl["Value"])
    ac = kml("DegAcos", x + 300, y, [D("A"), RD])
    g.link(cl["ReturnValue"], ac["A"])
    return ac["ReturnValue"]


_twF = _tw_axis(LX_ - 300, LY_ + 400, "jnt_l_hand", "GetForwardVector")
_twU = _tw_axis(LX_ - 300, LY_ + 500, "jnt_l_hand", "GetUpVector")
_twA = _tw_axis(LX_ - 300, LY_ + 600, "jnt_l_fore_arm", "GetUpVector")
_twstep = d_op("FMax", LX_ + 500, LY_ + 450, d_op("FMax", LX_ + 400, LY_ + 400, _tw_ang(LX_, LY_ + 400, _twF, "TwPF"), _tw_ang(LX_, LY_ + 500, _twU, "TwPU")),
               _tw_ang(LX_, LY_ + 600, _twA, "TwPA"))
_twt0 = d_op("FMax", LX_ - 300, LY_ + 800, self_get("ReachStart", "real", LX_ - 500, LY_ + 800, subcat="double"), _back(LX_ - 500, LY_ + 870))
_twpos = member_pure(ANIMI, "Montage_GetPosition", LX_ - 300, LY_ + 950, anim, [("Montage", "object", dict(sub=MONT)), ("ReturnValue", "real", dict(subcat="float", out=True))])
_twpos.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", LX_ - 500, LY_ + 950, sub=MONT), _twpos["Montage"])
_twsq = sequence(LX_ - 500, LY_, "probe: new reach? / in its window / remember the axes", 3)
g.link(_sqpf["then_6"], _twsq["execute"])
_twnew = branch(LX_, LY_, "a new reach or way back? start over",
                d_op("NotEqual_DoubleDouble", LX_ - 100, LY_ + 150, _twt0, self_get("TwT0", "real", LX_ - 300, LY_ + 150, subcat="double"), ret=RB))
g.link(_twsq["then_0"], _twnew["execute"])
chain(_twnew, set_from("TwT0", "real", LX_ + 300, LY_, _twt0, "", subcat="double"),
      self_set("TwMax", "real", LX_ + 600, LY_, "", default="0.0", subcat="double"), self_set("TwSum", "real", LX_ + 900, LY_, "", default="0.0", subcat="double"),
      self_set("TwLate", "real", LX_ + 1200, LY_, "", default="0.0", subcat="double"), self_set("NTwBig", "int", LX_ + 1500, LY_, "", default="0"),
      self_set("TwMaxPos", "real", LX_ + 1800, LY_, "", default="0.0", subcat="double"), self_set("TwMaxT", "real", LX_ + 2100, LY_, "", default="0.0", subcat="double"))
_twin = branch(LX_, LY_ + 1100, "in the 2.5 s window (not the first tick)?",
               b_and(LX_ - 100, LY_ + 1250,
                     b_not(LX_ - 200, LY_ + 1250, d_op("NotEqual_DoubleDouble", LX_ - 400, LY_ + 1250, _twt0, self_get("TwT0", "real", LX_ - 600, LY_ + 1250, subcat="double"), ret=RB)),
                     d_op("Less_DoubleDouble", LX_ - 200, LY_ + 1320, d_op("Subtract_DoubleDouble", LX_ - 400, LY_ + 1320, now(LX_ - 600, LY_ + 1320), _twt0), b_const="2.5", ret=RB),
                     d_op("Greater_DoubleDouble", LX_ - 200, LY_ + 1390, _twt0, b_const="0.0", ret=RB)))
g.link(_twsq["then_1"], _twin["execute"])
_late = kml("SelectFloat", LX_ + 1000, LY_ + 1300, [D("A"), D("B", "0.0"), B("bPickA"), RD])
g.link(_twstep, _late["A"])
g.link(d_op("GreaterEqual_DoubleDouble", LX_ + 800, LY_ + 1350, _twpos["ReturnValue"], b_const="1.1", ret=RB), _late["bPickA"])
_twbig = branch(LX_ + 1500, LY_ + 1100, "a step over 20 deg?", d_op("Greater_DoubleDouble", LX_ + 1400, LY_ + 1300, _twstep, b_const="20.0", ret=RB))
chain(_twin, set_from("TwStep", "real", LX_ + 300, LY_ + 1100, _twstep, "this tick's turn", subcat="double"),
      set_from("TwPos", "real", LX_ + 600, LY_ + 1100, _twpos["ReturnValue"], "our montage's position", subcat="double"),
      set_from("TwSum", "real", LX_ + 900, LY_ + 1100, d_op("Add_DoubleDouble", LX_ + 800, LY_ + 1250, self_get("TwSum", "real", LX_ + 600, LY_ + 1300, subcat="double"), _twstep), "", subcat="double"),
      set_from("TwLate", "real", LX_ + 1200, LY_ + 1100, d_op("Add_DoubleDouble", LX_ + 1100, LY_ + 1250, self_get("TwLate", "real", LX_ + 900, LY_ + 1400, subcat="double"), _late["ReturnValue"]), "", subcat="double"),
      _twbig)
_twbn = inc("NTwBig", LX_ + 1800, LY_ + 1100, "")
g.link(_twbig["then"], _twbn["execute"])
_twmx = branch(LX_ + 2100, LY_ + 1100, "the largest so far?", d_op("Greater_DoubleDouble", LX_ + 2000, LY_ + 1300, _twstep, self_get("TwMax", "real", LX_ + 1800, LY_ + 1350, subcat="double"), ret=RB))
g.link(_twbn["then"], _twmx["execute"])
g.link(_twbig["else"], _twmx["execute"])
chain(_twmx, set_from("TwMax", "real", LX_ + 2400, LY_ + 1100, _twstep, "", subcat="double"),
      set_from("TwMaxPos", "real", LX_ + 2700, LY_ + 1100, _twpos["ReturnValue"], "", subcat="double"),
      set_from("TwMaxT", "real", LX_ + 3000, LY_ + 1100, d_op("Subtract_DoubleDouble", LX_ + 2900, LY_ + 1300, now(LX_ + 2700, LY_ + 1300), _twt0), "", subcat="double"))
_twr = set_from("TwPF", "struct", LX_ + 300, LY_ + 700, _twF, "remember the axes", sub=VEC)
chain(_twr, set_from("TwPU", "struct", LX_ + 600, LY_ + 700, _twU, "", sub=VEC), set_from("TwPA", "struct", LX_ + 900, LY_ + 700, _twA, "", sub=VEC))
g.link(_twsq["then_2"], _twr["execute"])
'''
rep('#   (probe, build l: "the right arm clips through the flap', LOGGER + '#   (probe, build l: "the right arm clips through the flap')
open(p, "w", encoding="utf-8", newline="\n").write(c)

p = "zonekit/tools/setup_assets.py"
c = open(p, encoding="utf-8").read()
a = '("WeaponShowTick", "int", None),'
assert a in c
c = c.replace(a, a + ' ("TwT0", "real", None), ("TwMax", "real", None), ("TwSum", "real", None), ("TwLate", "real", None), ("NTwBig", "int", None), ("TwMaxPos", "real", None), ("TwMaxT", "real", None), ("TwStep", "real", None), ("TwPos", "real", None), ("TwPF", "vector", None), ("TwPU", "vector", None), ("TwPA", "vector", None),', 1)
open(p, "w", encoding="utf-8", newline="\n").write(c)

p = "zonekit/tools/probe/ImmLootProbe/scripts/main.lua"
c = open(p, encoding="utf-8").read()
a = '"WeaponShowTick",'
assert a in c
c = c.replace(a, a + ' "TwMax", "TwMaxPos", "TwMaxT", "TwSum", "TwLate", "NTwBig", "TwStep", "TwPos",', 1)
open(p, "w", encoding="utf-8", newline="\n").write(c)
print("ok")
