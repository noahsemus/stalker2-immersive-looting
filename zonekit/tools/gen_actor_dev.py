# v1.3.2 n / o (tester: "can we do something like ZST's custom menu to live change the hand positioning instead of MCM?
# it should still be dev only, not in full releases"): the DEV tools of BP_ImmLootActor. Exec'd at the end of
# gen_actor_looting.py when IMMLOOT_DEV=1 (the default during development; a release is generated with IMMLOOT_DEV=0
# and the /ImmersiveLooting/Dev/ assets are left out of its classifier list).
#   - once per world, ~2 s in: Dev/ABP_ImmLootDevPose becomes the player mesh's post-process anim instance (the mesh
#     swap path of ImmersiveDialogue 2.1 / Campfires; never Reinit, never swapped again), enabled for good;
#   - F7: the panel Dev/W_ImmLootDev (sliders S_<i>, labels T_<i>, dev_params.PARAMS) shown / hidden, with the mouse;
#   - F8: every slider back to its default;  F9: backpack preview (empty hands: the real bag path, held at its Idle
#     until F9 again, then its Out);
#   - every tick: the labels show their live value; the values go to the post-process layer in WORLD space from the
#     camera's axes: the arms while the bag is out with empty hands (standing / crouched values by the camera height),
#     the left hand while an empty-handed crouched pickup plays; reach height -> DevCrouchElevF; time scale.
import importlib
import dev_params
importlib.reload(dev_params)
PARAMS = dev_params.PARAMS

WDEV = "\"/Script/UMG.WidgetBlueprintGeneratedClass'/ImmersiveLooting/Dev/W_ImmLootDev.W_ImmLootDev_C'\""
WDEV_PATH = "/ImmersiveLooting/Dev/W_ImmLootDev.W_ImmLootDev_C"
ABPDEV = "\"/Script/Engine.AnimBlueprintGeneratedClass'/ImmersiveLooting/Dev/ABP_ImmLootDevPose.ABP_ImmLootDevPose_C'\""
ABPDEV_PATH = "/ImmersiveLooting/Dev/ABP_ImmLootDevPose.ABP_ImmLootDevPose_C"
SLIDER = cls("/Script/UMG.Slider")
TEXTB = cls("/Script/UMG.TextBlock")
WIDGET = cls("/Script/UMG.Widget")
SHADOW = "/Game/_STALKER2/SkeletalMeshes/player/sta/sta_03/SK_pla_sta_03_SHA.SK_pla_sta_03_SHA"
KAL = cls("/Script/Engine.KismetArrayLibrary")
ZX, ZY = -6000, 40000
_pctl = lib_pure(GS, "GameplayStatics", "GetPlayerController", ZX - 600, ZY + 900,
                 [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)), ("PlayerIndex", "int", dict(extra='DefaultValue="0",')),
                  ("ReturnValue", "object", dict(sub=PCC, out=True))])["ReturnValue"]
g.box("EdGraphNode_Comment_995", ZX - 100, ZY - 300, 9000, 9000, "DEV tools (dev builds only): post-process pose layer, F7 panel, F8 reset, F9 backpack preview")

# the tick: slp -> DEV steps -> the menu gate
_dsq = sequence(ZX, ZY, "DEV steps", 7)
_gate_in = [q for q in slp["then"].links]
for _q in _gate_in:
    slp["then"].links.remove(_q); _q.links.remove(slp["then"])
g.link(slp["then"], _dsq["execute"])
for _q in _gate_in:
    g.link(_dsq["then_6"], _q)

# ---- D0: (v1.3.2 o) nothing: the post-process layer is gone (ImmersiveDialogue owns that slot; the tester runs all
#      mods together). The panel drives dynamic montages in CutsceneSlot instead (D5) ----
# ---- keys: down now, not down last tick (polled: the panel needs no input binding) ----
def _key_edge(x, y, key, prev_var, comment):
    kd = member_pure(PCC, "IsInputKeyDown", x - 300, y + 200, _pctl, [("Key", "struct", dict(sub=KEY, extra=f'DefaultValue="{key}",')), RB])["ReturnValue"]
    s = sequence(x, y, f"{key}: edge, then remember", 2)
    b = branch(x + 300, y, comment, b_and(x + 200, y + 200, kd, b_not(x, y + 270, self_get(prev_var, "bool", x - 200, y + 270))))
    g.link(s["then_0"], b["execute"])
    g.link(s["then_1"], set_from(prev_var, "bool", x + 300, y + 400, kd, "")["execute"])
    return s, b


# ---- D1: F7 the panel ----
_s7, _b7 = _key_edge(ZX + 300, ZY + 1200, "F7", "DevF7Prev", "DEV: F7 pressed? the panel")
g.link(_dsq["then_1"], _s7["execute"])
_pnl = lambda x, y: self_get("DevPanel", "object", x, y, sub=WDEV)
_b7n = branch(ZX + 700, ZY + 1200, "no panel yet? made", b_not(ZX + 600, ZY + 1400, is_valid(ZX + 400, ZY + 1400, _pnl(ZX + 200, ZY + 1400))))
_swa = self_set("DevWantAttach", "bool", ZX + 550, ZY + 1050, "the pose layer attaches next tick", default="true")
g.link(_b7["then"], _swa["execute"])
g.link(_swa["then"], _b7n["execute"])
_cw = exec_pins(Node(g, "/Script/UMGEditor.K2Node_CreateWidget", nm("K2Node_CreateWidget"), ZX + 1000, ZY + 1100, "the DEV panel"))
_cw.pin("Class", "class", sub=UW, extra=f'DefaultObject="{WDEV_PATH}",')
_cw.pin("ReturnValue", "object", sub=WDEV, out=True)
_cw.pin("OwningPlayer", "object", sub=PCC)
g.link(_pctl, _cw["OwningPlayer"])
g.link(_b7n["then"], _cw["execute"])
_spn = set_from("DevPanel", "object", ZX + 1300, ZY + 1100, _cw["ReturnValue"], "", sub=WDEV)
_atv = member_call(UW, "AddToViewport", ZX + 1600, ZY + 1100, _pnl(ZX + 1400, ZY + 1300), "on screen", [("ZOrder", "int", dict(extra='DefaultValue="50",'))])
chain(_cw, _spn, _atv)
_shown = lambda x, y: self_get("DevPanelShown", "bool", x, y)
_b7v = branch(ZX + 1900, ZY + 1200, "shown? hide it (else show)", _shown(ZX + 1700, ZY + 1400))
g.link(_atv["then"], _b7v["execute"])
g.link(_b7n["else"], _b7v["execute"])
_svis = lambda x, y, vis: member_call(WIDGET, "SetVisibility", x, y, _pnl(x - 200, y + 200), vis,
                                      [("InVisibility", "byte", dict(sub=EN("/Script/UMG.ESlateVisibility"), extra=f'DefaultValue="{vis}",'))])
def _curs(x, y, on):
    n = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), x, y, "mouse cursor",
                       [f'VariableReference=(MemberParent={PCC},MemberName="bShowMouseCursor")']))
    n.pin("bShowMouseCursor", "bool", extra=f'DefaultValue="{on}",')
    n.pin("Output_Get", "bool", out=True)
    n.pin("self", "object", sub=PCC, extra=TGT)
    g.link(_pctl, n["self"])
    return n


chain(_b7v, _svis(ZX + 2200, ZY + 1000, "Collapsed"), self_set("DevPanelShown", "bool", ZX + 2400, ZY + 1000, "", default="false"))
_v7 = _svis(ZX + 2200, ZY + 1400, "Visible")
g.link(_b7v["else"], _v7["execute"])
chain(_v7, self_set("DevPanelShown", "bool", ZX + 2400, ZY + 1400, "", default="true"))

_sl = lambda i, x, y: other_get(WDEV, f"S_{i}", "object", x, y, _pnl(x - 200, y), sub=SLIDER)
_tl = lambda i, x, y: other_get(WDEV, f"T_{i}", "object", x, y, _pnl(x - 200, y), sub=TEXTB)
_pv = is_valid(ZX + 100, ZY + 2000, _pnl(ZX - 100, ZY + 2000))

# ---- D2: F8 reset ----
_s8, _b8 = _key_edge(ZX + 300, ZY + 2200, "F8", "DevF8Prev", "DEV: F8 pressed, the panel made? every slider to its default")
g.link(_dsq["then_2"], _s8["execute"])
_b8p = branch(ZX + 700, ZY + 2200, "panel?", is_valid(ZX + 600, ZY + 2400, _pnl(ZX + 400, ZY + 2400)))
g.link(_b8["then"], _b8p["execute"])
_prev = _b8p["then"]
for i, (label, unit, lo, hi, step, d) in enumerate(PARAMS):
    n = member_call(SLIDER, "SetValue", ZX + 1000 + 250 * i, ZY + 2200, _sl(i, ZX + 900 + 250 * i, ZY + 2400), f"S_{i} = {d:g}" if i == 0 else "",
                    [("InValue", "real", dict(subcat="float", extra=f'DefaultValue="{d:.6f}",'))])
    g.link(_prev, n["execute"])
    _prev = n["then"]

# ---- D3 (v1.3.2 q; tester: "F9 seems broken, we don't need it"): the numpad drives the panel while it is shown:
#      8 / 2 select the row, 4 / 6 lower / raise its value (held: each tick, faster the longer it is held), 5 = its
#      default. The selected row's label starts with ">>". ----
_sel_ = lambda x, y: self_get("DevSel", "int", x, y)
_d3 = sequence(ZX + 300, ZY + 3000, "DEV numpad: up, down, change, default, backpack preview", 5)
g.link(_dsq["then_3"], _d3["execute"])
_shownp = b_and(ZX + 200, ZY + 2900, _pv, self_get("DevPanelShown", "bool", ZX, ZY + 2900))
_s8u, _b8u = _key_edge(ZX + 600, ZY + 3000, "NumPadEight", "DevN8Prev", "Num 8: the row above")
_s2d, _b2d = _key_edge(ZX + 600, ZY + 3300, "NumPadTwo", "DevN2Prev", "Num 2: the row below")
_s5r, _b5r = _key_edge(ZX + 600, ZY + 3900, "NumPadFive", "DevN5Prev", "Num 5: the row's default")
_g8 = branch(ZX + 450, ZY + 3000, "panel shown?", _shownp); g.link(_d3["then_0"], _g8["execute"]); g.link(_g8["then"], _s8u["execute"])
_g2 = branch(ZX + 450, ZY + 3300, "panel shown?", _shownp); g.link(_d3["then_1"], _g2["execute"]); g.link(_g2["then"], _s2d["execute"])
_g5 = branch(ZX + 450, ZY + 3900, "panel shown?", _shownp); g.link(_d3["then_3"], _g5["execute"]); g.link(_g5["then"], _s5r["execute"])


def _wrap(x, y, delta):
    a = kml("Add_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{delta + len(PARAMS)}",')), ("ReturnValue", "int", dict(out=True))])
    g.link(_sel_(x - 200, y), a["A"])
    m = kml("Percent_IntInt", x + 150, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{len(PARAMS)}",')), ("ReturnValue", "int", dict(out=True))])
    g.link(a["ReturnValue"], m["A"])
    return m["ReturnValue"]


g.link(_b8u["then"], set_from("DevSel", "int", ZX + 1000, ZY + 3000, _wrap(ZX + 800, ZY + 3100, -1), "")["execute"])
g.link(_b2d["then"], set_from("DevSel", "int", ZX + 1000, ZY + 3300, _wrap(ZX + 800, ZY + 3400, 1), "")["execute"])
#   change: direction from Num 4 / Num 6 held, speed from how long (DevHoldTicks)
_k4 = member_pure(PCC, "IsInputKeyDown", ZX + 300, ZY + 3700, _pctl, [("Key", "struct", dict(sub=KEY, extra='DefaultValue="NumPadFour",')), RB])["ReturnValue"]
_k6 = member_pure(PCC, "IsInputKeyDown", ZX + 300, ZY + 3770, _pctl, [("Key", "struct", dict(sub=KEY, extra='DefaultValue="NumPadSix",')), RB])["ReturnValue"]
_dir = d_op("Subtract_DoubleDouble", ZX + 700, ZY + 3700,
            (lambda n: (g.link(_k6, n["bPickA"]), n["ReturnValue"])[-1])(kml("SelectFloat", ZX + 500, ZY + 3700, [D("A", "1.0"), D("B", "0.0"), B("bPickA"), RD])),
            (lambda n: (g.link(_k4, n["bPickA"]), n["ReturnValue"])[-1])(kml("SelectFloat", ZX + 500, ZY + 3770, [D("A", "1.0"), D("B", "0.0"), B("bPickA"), RD])))
_held = b_or(ZX + 500, ZY + 3850, _k4, _k6)
_bch = branch(ZX + 900, ZY + 3600, "Num 4 / 6 held, panel shown? the row's value changes", b_and(ZX + 800, ZY + 3800, _held, _shownp))
g.link(_d3["then_2"], _bch["execute"])
_hold = lambda x, y: self_get("DevHoldTicks", "int", x, y)
_inc = inc("DevHoldTicks", ZX + 1200, ZY + 3600, "held for")
g.link(_bch["then"], _inc["execute"])
g.link(_bch["else"], self_set("DevHoldTicks", "int", ZX + 1200, ZY + 3800, "released", default="0")["execute"])
#   per tick: unit step x 0.25 x (1 + held ticks / 20), capped at 6x
_hd = kml("Conv_IntToDouble", ZX + 1100, ZY + 4000, [("InInt", "int"), RD]); g.link(_hold(ZX + 900, ZY + 4000), _hd["InInt"])
_spd = kml("FMin", ZX + 1400, ZY + 4000, [D("A"), D("B", "6.0"), RD])
g.link(d_op("Add_DoubleDouble", ZX + 1300, ZY + 4050, d_op("Divide_DoubleDouble", ZX + 1200, ZY + 4100, _hd["ReturnValue"], b_const="20.0"), b_const="1.0"), _spd["A"])
_prev = _inc["then"]
_prev5 = _b5r["then"]
for i, (label, unit, lo, hi, step, d) in enumerate(PARAMS):
    x0 = ZX + 1600 + 300 * i
    eq = kml("EqualEqual_IntInt", x0 - 100, ZY + 3800, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{i}",')), RB])
    g.link(_sel_(x0 - 300, ZY + 3800), eq["A"])
    bi = branch(x0, ZY + 3600, f"row {i}?" if i else "the selected row: its value + direction x step x speed", eq["ReturnValue"])
    g.link(_prev, bi["execute"])
    gv = member_pure(SLIDER, "GetValue", x0 - 100, ZY + 3900, _sl(i, x0 - 300, ZY + 3900), [("ReturnValue", "real", dict(subcat="float", out=True))])
    nv = d_op("Add_DoubleDouble", x0 + 100, ZY + 3950, gv["ReturnValue"],
              d_op("Multiply_DoubleDouble", x0, ZY + 4050, d_op("Multiply_DoubleDouble", x0 - 100, ZY + 4100, _dir, _spd["ReturnValue"]), b_const=f"{step * 0.25}"))
    cl = kml("FClamp", x0 + 200, ZY + 3950, [D("Value"), D("Min", f"{lo}"), D("Max", f"{hi}"), RD])
    g.link(nv, cl["Value"])
    sv = member_call(SLIDER, "SetValue", x0 + 200, ZY + 3600, _sl(i, x0, ZY + 3750), "", [("InValue", "real", dict(subcat="float"))])
    g.link(cl["ReturnValue"], sv["InValue"])
    g.link(bi["then"], sv["execute"])
    _prev = bi["else"]
    # Num 5: this row to its default if selected
    b5 = branch(x0, ZY + 4300, "", eq["ReturnValue"])
    g.link(_prev5, b5["execute"])
    s5 = member_call(SLIDER, "SetValue", x0 + 200, ZY + 4300, _sl(i, x0, ZY + 4450), "", [("InValue", "real", dict(subcat="float", extra=f'DefaultValue="{d:.6f}",'))])
    g.link(b5["then"], s5["execute"])
    _prev5 = b5["else"]

#   v1.3.2 s (tester: "F7 isn't doing anything when looting a body": the loot window takes the keys and covers the bag;
#   q's F9 was the game's quick load): the backpack preview is back on Num 0 (panel shown): empty hands, the real bag
#   path held at its Idle until Num 0 again, then its Out
_s0, _b0 = _key_edge(ZX + 600, ZY + 4600, "NumPadZero", "DevN0Prev", "Num 0: backpack preview on / off")
_g0 = branch(ZX + 450, ZY + 4600, "panel shown?", _shownp)
g.link(_d3["then_4"], _g0["execute"])
g.link(_g0["then"], _s0["execute"])
_b9b = branch(ZX + 1000, ZY + 4600, "a bag out? it goes back (its Out) / else: empty hands? the bag comes out and stays at its Idle",
              is_valid(ZX + 900, ZY + 4800, bag_actor(ZX + 700, ZY + 4800)))
g.link(_b0["then"], _b9b["execute"])
bag_out(ZX + 1300, ZY + 4500, _b9b["then"])
_b9e = branch(ZX + 1300, ZY + 4900, "empty hands?", b_not(ZX + 1200, ZY + 5100, obj_q("HasItemInMainHand", ZX + 1000, ZY + 5100, as_pc)))
g.link(_b9b["else"], _b9e["execute"])
_pv_last = self_set("TouchState", "int", ZX + 2800, ZY + 4900, "preview: idle touch state", default="0")
chain(_b9e, self_set("LootReach", "bool", ZX + 1600, ZY + 4900, "the touch state the bag's hold needs", default="true"),
      self_set("TouchIsBody", "bool", ZX + 1900, ZY + 4900, "", default="false"),
      self_set("LootPaused", "bool", ZX + 2200, ZY + 4900, "", default="false"),
      self_set("LootReverse", "bool", ZX + 2500, ZY + 4900, "", default="false"), _pv_last)
g.link(_pv_last["then"], _bbw["execute"])

# ---- the values: a slider's value, or its default while there is no panel ----
_val = {}
for i, (label, unit, lo, hi, step, d) in enumerate(PARAMS):
    sv = kml("SelectFloat", ZX + 400, ZY + 4000 + 80 * i, [D("A"), D("B", f"{d}"), B("bPickA"), RD])
    gv = member_pure(SLIDER, "GetValue", ZX + 200, ZY + 4000 + 80 * i, _sl(i, ZX, ZY + 4000 + 80 * i), [("ReturnValue", "real", dict(subcat="float", out=True))])
    g.link(gv["ReturnValue"], sv["A"])
    g.link(_pv, sv["bPickA"])
    _val[i] = sv["ReturnValue"]

# ---- D4: the labels (panel shown) ----
_b4 = branch(ZX + 300, ZY + 5600, "DEV: the panel shown? its labels with the live values", b_and(ZX + 200, ZY + 5800, _pv, _shown(ZX, ZY + 5800)))
g.link(_dsq["then_4"], _b4["execute"])
_prev = _b4["then"]
for i, (label, unit, lo, hi, step, d) in enumerate(PARAMS):
    bs = lib_pure(KSTR, "KismetStringLibrary", "BuildString_Double", ZX + 600 + 300 * i, ZY + 5900, [
        ("AppendTo", "string", dict(extra=f'DefaultValue="{label}   [{lo:g} .. {hi:g} {unit}, default {d:g}]",')),
        ("Prefix", "string", dict(extra='DefaultValue="   now ",')), D("InDouble"), ("Suffix", "string", dict(extra=f'DefaultValue=" {unit}",')),
        ("ReturnValue", "string", dict(out=True))])
    g.link(_val[i], bs["InDouble"])
    #   q: the selected row starts with ">> "
    eqs = kml("EqualEqual_IntInt", ZX + 400 + 300 * i, ZY + 6100, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{i}",')), RB])
    g.link(self_get("DevSel", "int", ZX + 200 + 300 * i, ZY + 6100), eqs["A"])
    mk = kml("SelectString", ZX + 450 + 300 * i, ZY + 6200, [("A", "string", dict(extra='DefaultValue=">> ",')), ("B", "string", dict(extra='DefaultValue="     ",')),
                                                             B("bPickA"), ("ReturnValue", "string", dict(out=True))])
    g.link(eqs["ReturnValue"], mk["bPickA"])
    cc = lib_pure(KSTR, "KismetStringLibrary", "Concat_StrStr", ZX + 650 + 300 * i, ZY + 6200, [("A", "string"), ("B", "string"), ("ReturnValue", "string", dict(out=True))])
    g.link(mk["ReturnValue"], cc["A"])
    g.link(bs["ReturnValue"], cc["B"])
    tx = lib_pure(KTXT, "KismetTextLibrary", "Conv_StringToText", ZX + 650 + 300 * i, ZY + 6000, [("InString", "string"), ("ReturnValue", "text", dict(out=True))])
    g.link(cc["ReturnValue"], tx["InString"])
    st = member_call(TEXTB, "SetText", ZX + 600 + 300 * i, ZY + 5600, _tl(i, ZX + 500 + 300 * i, ZY + 5750), "", [("InText", "text")])
    g.link(tx["ReturnValue"], st["InText"])
    g.link(_prev, st["execute"])
    _prev = st["then"]

# ---- D5 (v1.3.2 o): the values out. The tester runs ImmersiveDialogue (it owns the player's post-process layer) with
#      everything else, so the live offsets are local-space additive grids (make_dev_offsets.py PART=rot) played as a
#      paused dynamic montage in CutsceneSlot: AnimBP_Player evaluates it after FullBody and DeathSlot (CutsceneSlot ->
#      ControlRig -> Root), and nothing of ours or the game's plays in CutsceneGroup outside cutscenes. One table at a
#      time: the arms while the bag is out with empty hands, the left hand while an empty-handed crouched pickup plays.
#      Only once the panel was opened (F7), so a normal session never plays anything there. ----
DEV_AROT = "/ImmersiveLooting/Runtime/AS_ImmLoot_DevArmRot.AS_ImmLoot_DevArmRot"
DEV_HROT = "/ImmersiveLooting/Runtime/AS_ImmLoot_DevHandRot.AS_ImmLoot_DevHandRot"
ROTG = (6.054235, 1.330347, 12)   # make_dev_offsets ROT_A / ROT_B / ROT_H: value(i) = sign(i) A (B^|i| - 1)
_dcl, _dcf, _dcr, _dcu, _ = cam_basis(ZX - 400, ZY + 6800)
_dz = kml("BreakVector", ZX - 100, ZY + 7300, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                              ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(_to_mesh(ZX - 300, ZY + 7300, _dcl), _dz["InVec"])
_dstand = d_op("GreaterEqual_DoubleDouble", ZX + 100, ZY + 7300, _dz["Z"], b_const="130.0", ret=RB)


def _sel(x, y, a, b, pick):
    n = kml("SelectFloat", x, y, [D("A"), D("B"), B("bPickA"), RD])
    g.link(a, n["A"]); g.link(b, n["B"]); g.link(pick, n["bPickA"])
    return n["ReturnValue"]


def _gidx(x, y, v, A, Bb, H, cont=False):
    """grid index of v on value(i) = sign(i) A (B^|i| - 1): clamp(sign(v) ln(|v| / A + 1) / ln B, -H, H) + H"""
    ab = kml("Abs", x - 600, y + 80, [D("A"), RD]); g.link(v, ab["A"])
    ln_ = kml("Loge", x - 300, y + 80, [D("A"), RD])
    g.link(d_op("Add_DoubleDouble", x - 450, y + 80, d_op("Divide_DoubleDouble", x - 500, y + 160, ab["ReturnValue"], b_const=str(A)), b_const="1.0"), ln_["A"])
    sg = kml("SignOfFloat", x - 450, y + 240, [D("A"), RD]); g.link(v, sg["A"])
    ix = d_op("Multiply_DoubleDouble", x - 150, y + 80, d_op("Divide_DoubleDouble", x - 200, y + 160, ln_["ReturnValue"], b_const=repr(math.log(Bb))), sg["ReturnValue"])
    cl = kml("FClamp", x + 200, y, [D("Value"), D("Min", "0.0"), D("Max", f"{2 * H}.0"), RD])
    g.link(d_op("Add_DoubleDouble", x, y + 80, ix, b_const=f"{H}.0"), cl["Value"])
    if cont:
        return cl["ReturnValue"]
    rd = kml("Round", x + 400, y, [D("A"), ("ReturnValue", "int", dict(out=True))])
    g.link(cl["ReturnValue"], rd["A"])
    cv = kml("Conv_IntToDouble", x + 550, y, [("InInt", "int"), RD])
    g.link(rd["ReturnValue"], cv["InInt"])
    return cv["ReturnValue"]


def _grid_s(x, y, slow, mid, fast, n):
    """montage seconds of grid frame 1 + (slow * n + mid) * n + fast"""
    a = d_op("Add_DoubleDouble", x + 300, y, d_op("Multiply_DoubleDouble", x + 150, y, slow, b_const=str(float(n))), mid)
    f = d_op("Add_DoubleDouble", x + 600, y, d_op("Multiply_DoubleDouble", x + 450, y, a, b_const=str(float(n))), fast)
    return d_op("Divide_DoubleDouble", x + 900, y, d_op("Add_DoubleDouble", x + 750, y, f, b_const="1.0"), b_const="30.0")


#   the arms table: (yaw slow, roll mid, pitch fast); the hand table: (yaw slow, pitch mid, roll fast)
_ap, _ay, _arl = (_sel(ZX + 300, ZY + 7000 + 70 * k, _val[k], _val[k + 3], _dstand) for k in range(3))
_t_arm = _grid_s(ZX + 1400, ZY + 7000, _gidx(ZX + 800, ZY + 6900, _ay, *ROTG), _gidx(ZX + 800, ZY + 7000, _arl, *ROTG),
                 _gidx(ZX + 800, ZY + 7100, _ap, *ROTG, cont=True), 25)
_t_hand = _grid_s(ZX + 1400, ZY + 7600, _gidx(ZX + 800, ZY + 7500, _val[8], *ROTG), _gidx(ZX + 800, ZY + 7600, _val[7], *ROTG),
                  _gidx(ZX + 800, ZY + 7700, _val[6], *ROTG, cont=True), 25)
_armon = b_and(ZX + 300, ZY + 8000, is_valid(ZX + 100, ZY + 8000, bag_actor(ZX - 100, ZY + 8000)), b_not(ZX + 100, ZY + 8070, self_get("BagWeapon", "bool", ZX - 100, ZY + 8070)))
_handon = b_and(ZX + 300, ZY + 8200, self_get("GrabBH", "bool", ZX + 100, ZY + 8200), grab_active(ZX + 100, ZY + 8270), b_not(ZX + 100, ZY + 8340, _dstand))
_dm = lambda x, y: self_get("DevMont", "object", x, y, sub=MONT)
_dk = lambda x, y: self_get("DevMontKind", "int", x, y)
_dmon = b_and(ZX + 300, ZY + 8500, is_valid(ZX + 100, ZY + 8500, _dm(ZX - 100, ZY + 8500)),
              (lambda n: (n.pins["Montage"].__setattr__("const", True), g.link(_dm(ZX - 100, ZY + 8570), n["Montage"]), n["ReturnValue"])[-1])(
                  member_pure(ANIMI, "Montage_IsActive", ZX + 100, ZY + 8570, anim, [("Montage", "object", dict(sub=MONT)), RB])))


def _kind_is(x, y, k):
    n = kml("EqualEqual_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{k}",')), RB])
    g.link(_dk(x - 200, y), n["A"])
    return n["ReturnValue"]


def _dev_play(x, y, asset, kind, t, comment):
    """the table in CutsceneSlot from the right frame, paused; DevMont / DevMontKind"""
    n = member_call(ANIMI, "PlaySlotAnimationAsDynamicMontage", x, y, anim, comment, [
        ("Asset", "object", dict(sub=ANIMSEQB, extra=f'DefaultObject="{asset}",')),
        ("SlotNodeName", "name", dict(extra='DefaultValue="CutsceneSlot",')),
        ("BlendInTime", "real", dict(subcat="float", extra='DefaultValue="0.200000",')),
        ("BlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.250000",')),
        ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",')),
        ("LoopCount", "int", dict(extra='DefaultValue="1",')),
        ("BlendOutTriggerTime", "real", dict(subcat="float", extra='DefaultValue="-1.000000",')),
        ("InTimeToStartMontageAt", "real", dict(subcat="float")),
        ("ReturnValue", "object", dict(sub=MONT, out=True))])
    g.link(t, n["InTimeToStartMontageAt"])
    ps = member_call(ANIMI, "Montage_Pause", x + 300, y, anim, "held", [("Montage", "object", dict(sub=MONT))])
    g.link(n["ReturnValue"], ps["Montage"])
    chain(n, set_from("DevMont", "object", x + 150, y - 150, n["ReturnValue"], "", sub=MONT), ps,
          self_set("DevMontKind", "int", x + 600, y, "", default=str(kind)))
    return n


def _dev_setpos(x, y, t):
    n = member_call(ANIMI, "Montage_SetPosition", x, y, anim, "at the panel's value", [("Montage", "object", dict(sub=MONT)), ("NewPosition", "real", dict(subcat="float"))])
    g.link(_dm(x - 200, y + 200), n["Montage"])
    g.link(t, n["NewPosition"])
    return n


_d5 = sequence(ZX + 400, ZY + 6500, "DEV: values out", 3)
g.link(_dsq["then_5"], _d5["execute"])
_b5p = branch(ZX + 700, ZY + 6400, "DEV: the panel opened once?", _pv)
g.link(_d5["then_0"], _b5p["execute"])
_b5a = branch(ZX + 1000, ZY + 6400, "the bag out with empty hands? the arms table", _armon)
g.link(_b5p["then"], _b5a["execute"])
_b5a2 = branch(ZX + 1300, ZY + 6300, "already playing? its frame (else start it)", b_and(ZX + 1200, ZY + 6200, _dmon, _kind_is(ZX + 1000, ZY + 6200, 1)))
g.link(_b5a["then"], _b5a2["execute"])
g.link(_b5a2["then"], _dev_setpos(ZX + 1600, ZY + 6300, _t_arm)["execute"])
g.link(_b5a2["else"], _dev_play(ZX + 1600, ZY + 6100, DEV_AROT, 1, _t_arm, "DEV: the arms table (CutsceneSlot)")["execute"])
_b5h = branch(ZX + 1300, ZY + 6600, "an empty-handed crouched pickup? the hand table", _handon)
g.link(_b5a["else"], _b5h["execute"])
_b5h2 = branch(ZX + 1600, ZY + 6600, "already playing? its frame (else start it)", b_and(ZX + 1500, ZY + 6500, _dmon, _kind_is(ZX + 1300, ZY + 6500, 2)))
g.link(_b5h["then"], _b5h2["execute"])
g.link(_b5h2["then"], _dev_setpos(ZX + 1900, ZY + 6600, _t_hand)["execute"])
g.link(_b5h2["else"], _dev_play(ZX + 1900, ZY + 6800, DEV_HROT, 2, _t_hand, "DEV: the hand table (CutsceneSlot)")["execute"])
_b5o = branch(ZX + 1600, ZY + 7000, "neither, a table still on? out", _dmon)
g.link(_b5h["else"], _b5o["execute"])
_ms5 = member_call(ANIMI, "Montage_Stop", ZX + 1900, ZY + 7000, anim, "out (0.25 s)", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.250000",')), ("Montage", "object", dict(sub=MONT))])
_ms5.pins["Montage"].const = True
g.link(_dm(ZX + 1700, ZY + 7200), _ms5["Montage"])
chain(_b5o, _ms5, self_set("DevMontKind", "int", ZX + 2200, ZY + 7000, "", default="0"))
g.link(_d5["then_1"], set_from("DevCrouchElevF", "real", ZX + 1000, ZY + 6900 + 400, _val[9], "DEV: crouched reach height", subcat="double")["execute"])
_b5t = branch(ZX + 700, ZY + 7500, "panel made? its time scale", _pv)
g.link(_d5["then_2"], _b5t["execute"])
_gtd = lib_call(GS, "SetGlobalTimeDilation", ZX + 1000, ZY + 7500, "time scale", [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)), ("TimeDilation", "real", dict(subcat="float"))],
                "/Script/Engine.Default__GameplayStatics")
g.link(_val[10], _gtd["TimeDilation"])
g.link(_b5t["then"], _gtd["execute"])
