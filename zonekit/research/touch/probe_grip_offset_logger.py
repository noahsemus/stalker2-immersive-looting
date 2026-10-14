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


rep('''_twsq = sequence(LX_ - 500, LY_, "probe: new reach? / in its window / remember the axes", 3)''',
    '''_twsq = sequence(LX_ - 500, LY_, "probe: new reach? / in its window / remember the axes / hand vs the weapon's grip", 4)''')
rep('''      self_set("TwMaxPos", "real", LX_ + 1800, LY_, "", default="0.0", subcat="double"), self_set("TwMaxT", "real", LX_ + 2100, LY_, "", default="0.0", subcat="double"))''',
    '''      self_set("TwMaxPos", "real", LX_ + 1800, LY_, "", default="0.0", subcat="double"), self_set("TwMaxT", "real", LX_ + 2100, LY_, "", default="0.0", subcat="double"),
      self_set("TwRMax", "real", LX_ + 2400, LY_, "", default="-100.0", subcat="double"), self_set("TwRMaxPos", "real", LX_ + 2700, LY_, "", default="0.0", subcat="double"))''')
rep('''g.link(_twsq["then_2"], _twr["execute"])
''', '''g.link(_twsq["then_2"], _twr["execute"])
#   build y probe (tester: "on the way back the hand goes too far right, clipping the gun, then left into place"): the
#   left hand's offset from the held weapon's own left-hand socket in view axes (TwGF / TwGR / TwGU cm, every tick in
#   the window) and the largest rightward one (TwRMax at montage position TwRMaxPos)
_twwm = member_pure(OBJC, "GetWeaponInHandsMeshComponent", LX_ - 500, LY_ + 1700, as_pc, [("ReturnValue", "object", dict(sub=SKC, out=True))])["ReturnValue"]
_twws = member_pure(SC_, "GetSocketLocation", LX_ - 300, LY_ + 1700, _twwm, [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_hand",')),
                                                                          ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_twhs = member_pure(SC_, "GetSocketLocation", LX_ - 300, LY_ + 1800, mesh, [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_hand",')),
                                                                         ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_twdiff = vop("Subtract_VectorVector", LX_ - 200, LY_ + 1850, _twhs, _twws)
_twcr = member_pure(PCM, "GetCameraRotation", LX_ - 300, LY_ + 2000, _bcm, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_twax = {}
for j_, (nm_, fn_) in enumerate((("F", "GetForwardVector"), ("R", "GetRightVector"), ("U", "GetUpVector"))):
    a_ = kml(fn_, LX_ - 100, LY_ + 2000 + 100 * j_, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_twcr, a_["InRot"])
    _twax[nm_] = vop("Dot_VectorVector", LX_ + 100, LY_ + 2000 + 100 * j_, _twdiff, a_["ReturnValue"], ret_sub="real")
_twg = branch(LX_ + 300, LY_ + 1600, "probe: a weapon in hand and in the window?",
              b_and(LX_ + 200, LY_ + 1700, is_valid(LX_, LY_ + 1700, _twwm),
                    d_op("Less_DoubleDouble", LX_ + 100, LY_ + 1900, d_op("Subtract_DoubleDouble", LX_ - 100, LY_ + 1900, now(LX_ - 300, LY_ + 1900), _twt0), b_const="2.5", ret=RB)))
g.link(_twsq["then_3"], _twg["execute"])
_twgs = [set_from(v, "real", LX_ + 600 + 300 * j, LY_ + 1600, _twax[a], "hand minus the weapon's grip, view axes (cm)" if j == 0 else "", subcat="double")
         for j, (v, a) in enumerate((("TwGF", "F"), ("TwGR", "R"), ("TwGU", "U")))]
chain(_twg, *_twgs)
_twrm = branch(LX_ + 1600, LY_ + 1600, "the farthest right so far?", d_op("Greater_DoubleDouble", LX_ + 1500, LY_ + 1800, _twax["R"], self_get("TwRMax", "real", LX_ + 1300, LY_ + 1850, subcat="double"), ret=RB))
g.link(_twgs[-1]["then"], _twrm["execute"])
chain(_twrm, set_from("TwRMax", "real", LX_ + 1900, LY_ + 1600, _twax["R"], "", subcat="double"),
      set_from("TwRMaxPos", "real", LX_ + 2200, LY_ + 1600, _twpos["ReturnValue"], "", subcat="double"))
''')
open(p, "w", encoding="utf-8", newline="\n").write(c)

p = "zonekit/tools/setup_assets.py"
c = open(p, encoding="utf-8").read()
a = '("TwPA", "vector", None),'
assert a in c
c = c.replace(a, a + ' ("TwRMax", "real", -100.0), ("TwRMaxPos", "real", None), ("TwGF", "real", None), ("TwGR", "real", None), ("TwGU", "real", None),', 1)
open(p, "w", encoding="utf-8", newline="\n").write(c)

p = "zonekit/tools/probe/ImmLootProbe/scripts/main.lua"
c = open(p, encoding="utf-8").read()
a = '"TwPos",'
assert a in c
c = c.replace(a, a + ' "TwRMax", "TwRMaxPos", "TwGF", "TwGR", "TwGU",', 1)
open(p, "w", encoding="utf-8", newline="\n").write(c)
print("ok")
