"""Generates the whole BP_ImmLootActor event graph (select all in the graph, delete, paste this, compile, save).

What it does (PLAN.md):
  Event Tick -> player -> Sequence
    0 Once: tick after the animation update (TG_PostUpdateWork), so the left-hand bone is this frame's.
    1 Picked up?  The loose item we were looking at (cached by step 2, seen < SeenWindow s ago) is gone:
                  destroyed, its mesh hidden, or moved away. -> NPickups += 1, then
                  skip (sprint, aim, MainActionSlot action, another left-hand montage, dialogue, cutscene,
                  detector or binoculars in hand, Enabled off) -> NSkips += 1, SkipBits = why
                  else -> reach: the grab montage (AM_ImmLoot_Grab, LeftHand slot) unless one is already
                  before its pocketing frame, and a copy of the item (StaticMeshActor / SkeletalMeshActor)
                  spawned where the item was.
    2 Track:      PC.GetInteractionTarget -> owner -> InteractableItemContainer: remember the actor, its
                  mesh component and mesh asset (when the target changes) and its world transform (every tick).
    3 Fly:        the copy eases to the left-hand bone jnt_l_weapon, arriving at the grab frame; then it is
                  attached to the hand and destroyed at the pocketing frame.
    4 Recover:    our montage stopped before its "hand back on the grip" notify (interrupted) while a weapon
                  is held and no other left-hand montage runs -> play MG_fp_return_left_hand_on_item.
Montage times are in montage seconds (GrabTime, PocketTime, IKOnTime); real time = montage time / PlayRate.
Variables: see VARS in setup_assets.py (added from Python before the paste).
Usage: python gen_actor_looting.py <out.txt>
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "harness", "tools", "t3d"))
from bp_t3d import cls, TGT, write
from bp_graph import Graph, Node

BG = "/Script/BlueprintGraph."
PC = cls("/Script/Stalker2.PC")
OBJC = cls("/Script/Stalker2.Obj")
CHAR = cls("/Script/Engine.Character")
ACTOR = cls("/Script/Engine.Actor")
PAWN = cls("/Script/Engine.Pawn")
OBJ = cls("/Script/CoreUObject.Object")
ACOMP = cls("/Script/Engine.ActorComponent")
SC_ = cls("/Script/Engine.SceneComponent")
PRIM = cls("/Script/Engine.PrimitiveComponent")
SMC = cls("/Script/Engine.StaticMeshComponent")
SKC = cls("/Script/Engine.SkeletalMeshComponent")
SM = cls("/Script/Engine.StaticMesh")
SKMESH = cls("/Script/Engine.SkeletalMesh")
SMA = cls("/Script/Engine.StaticMeshActor")
SKA = cls("/Script/Engine.SkeletalMeshActor")
ANIMI = cls("/Script/Engine.AnimInstance")
MONT = cls("/Script/Engine.AnimMontage")
ICOMP = cls("/Script/Stalker2.InteractionComponent")
IIC = "/Script/Stalker2.InteractableItemContainer"
GS = cls("/Script/Engine.GameplayStatics")
KML = cls("/Script/Engine.KismetMathLibrary")
KSL = cls("/Script/Engine.KismetSystemLibrary")
VEC = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Vector'\""
ROT = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Rotator'\""
XFORM = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Transform'\""
HIT = "\"/Script/CoreUObject.ScriptStruct'/Script/Engine.HitResult'\""
EN = lambda p: "\"/Script/CoreUObject.Enum'%s'\"" % p
SELF = "\"/Script/Engine.BlueprintGeneratedClass'/ImmersiveLooting/Runtime/BP_ImmLootActor.BP_ImmLootActor_C'\""
GRAB = "/ImmersiveLooting/Runtime/AM_ImmLoot_Grab.AM_ImmLoot_Grab"
RETURN = ("/Game/_STALKER2/Animations/Player/AnimSequences/ar/common/showhide/lefthand/"
          "MG_fp_return_left_hand_on_item.MG_fp_return_left_hand_on_item")
HAND = "jnt_l_weapon"
GET_TIP = 'PinToolTip="Retrieves the value of the variable, can use instead of a separate Get node",'

g = Graph()
seq = [0]


def nm(kind):
    seq[0] += 1
    return f"{kind}_{900 + seq[0]}"


def exec_pins(n):
    n.pin("execute", "exec")
    n.pin("then", "exec", out=True)
    return n


def add_pins(n, pins):
    for p in pins:
        n.pin(*p[:2], **p[2]) if len(p) > 2 else n.pin(*p)
    return n


# ---------- node factories (same shapes as ImmersiveCampfires' gen_actor_seated_mode.py) ----------
def lib_pure(lib, libname, member, x, y, pins, comment=""):
    n = Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), x, y, comment,
             ["bIsPureFunc=True", f"FunctionReference=(MemberParent={lib},MemberName=\"{member}\")"])
    n.pin("self", "object", sub=lib, hidden=True, extra=f'DefaultObject="/Script/Engine.Default__{libname}",')
    return add_pins(n, pins)


def kml(member, x, y, pins):
    return lib_pure(KML, "KismetMathLibrary", member, x, y, pins)


def member_pure(owner_cls, member, x, y, target, pins):
    n = Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), x, y, "",
             ["bIsPureFunc=True", f"FunctionReference=(MemberParent={owner_cls},MemberName=\"{member}\")"])
    n.pin("self", "object", sub=owner_cls, extra=TGT)
    add_pins(n, pins)
    g.link(target, n["self"])
    return n


def member_call(owner_cls, member, x, y, target, comment, pins=()):
    n = exec_pins(Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), x, y, comment,
                       [f"FunctionReference=(MemberParent={owner_cls},MemberName=\"{member}\")"]))
    n.pin("self", "object", sub=owner_cls, extra=TGT)
    add_pins(n, pins)
    g.link(target, n["self"])
    return n


def self_call(member, x, y, comment, pins=()):
    n = exec_pins(Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), x, y, comment,
                       [f'FunctionReference=(MemberName="{member}",bSelfContext=True)']))
    n.pin("self", "object", sub=SELF, extra=TGT)
    return add_pins(n, pins)


def self_get(var, cat, x, y, sub="None", subcat=""):
    n = Node(g, BG + "K2Node_VariableGet", nm("K2Node_VariableGet"), x, y, "",
             [f'VariableReference=(MemberName="{var}",bSelfContext=True)'])
    n.pin(var, cat, sub=sub, subcat=subcat, out=True)
    n.pin("self", "object", sub=SELF, hidden=True, extra=TGT)
    return n[var]


def self_set(var, cat, x, y, comment="", default=None, sub="None", subcat=""):
    n = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), x, y, comment,
                       [f'VariableReference=(MemberName="{var}",bSelfContext=True)']))
    n.pin(var, cat, sub=sub, subcat=subcat, extra=f'DefaultValue="{default}",' if default is not None else "")
    n.pin("Output_Get", cat, sub=sub, subcat=subcat, out=True, extra=GET_TIP)
    n.pin("self", "object", sub=SELF, hidden=True, extra=TGT)
    return n


def other_get(owner_cls, var, cat, x, y, target, sub="None", subcat=""):
    n = Node(g, BG + "K2Node_VariableGet", nm("K2Node_VariableGet"), x, y, "",
             [f'VariableReference=(MemberParent={owner_cls},MemberName="{var}")'])
    n.pin(var, cat, sub=sub, subcat=subcat, out=True)
    n.pin("self", "object", sub=owner_cls, extra=TGT)
    g.link(target, n["self"])
    return n[var]


def branch(x, y, comment, cond):
    n = Node(g, BG + "K2Node_IfThenElse", nm("K2Node_IfThenElse"), x, y, comment)
    n.pin("execute", "exec")
    n.pin("Condition", "bool", extra='DefaultValue="true",')
    n.pin("then", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "true", "true"),')
    n.pin("else", "exec", out=True, extra='PinFriendlyName=NSLOCTEXT("K2Node", "false", "false"),')
    g.link(cond, n["Condition"])
    return n


def sequence(x, y, comment, n_out):
    n = Node(g, BG + "K2Node_ExecutionSequence", nm("K2Node_ExecutionSequence"), x, y, comment)
    n.pin("execute", "exec")
    for k in range(n_out):
        n.pin(f"then_{k}", "exec", out=True)
    return n


def chain(*nodes):
    for a, b in zip(nodes, nodes[1:]):
        g.link(a["then"], b["execute"])


B = lambda name, d="false": (name, "bool", dict(extra=f'DefaultValue="{d}",'))
D = lambda name, d="0.0": (name, "real", dict(subcat="double", extra=f'DefaultValue="{d}",'))
RB = ("ReturnValue", "bool", dict(out=True))
RD = ("ReturnValue", "real", dict(subcat="double", out=True))


def b_op(member, x, y, a, b):
    n = kml(member, x, y, [B("A"), B("B"), RB])
    g.link(a, n["A"])
    g.link(b, n["B"])
    return n["ReturnValue"]


def b_and(x, y, *xs):
    out = xs[0]
    for k, v in enumerate(xs[1:]):
        out = b_op("BooleanAND", x + 40 * k, y + 60 * k, out, v)
    return out


def b_or(x, y, *xs):
    out = xs[0]
    for k, v in enumerate(xs[1:]):
        out = b_op("BooleanOR", x + 40 * k, y + 60 * k, out, v)
    return out


def b_not(x, y, a):
    n = kml("Not_PreBool", x, y, [B("A"), RB])
    g.link(a, n["A"])
    return n["ReturnValue"]


def d_op(member, x, y, a, b=None, b_const="0.0", ret=RD):
    n = kml(member, x, y, [D("A"), D("B", b_const), ret])
    g.link(a, n["A"])
    if b is not None:
        g.link(b, n["B"])
    return n["ReturnValue"]


def is_valid(x, y, obj_pin):
    n = lib_pure(KSL, "KismetSystemLibrary", "IsValid", x, y, [("Object", "object", dict(sub=OBJ)), RB])
    g.link(obj_pin, n["Object"])
    return n["ReturnValue"]


def now(x, y):
    return lib_pure(KSL, "KismetSystemLibrary", "GetGameTimeInSeconds", x, y,
                    [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)), RD])["ReturnValue"]


def inc(var, x, y, comment=""):
    n = kml("Add_IntInt", x, y + 160, [("A", "int", dict(extra='DefaultValue="0",')),
                                       ("B", "int", dict(extra='DefaultValue="1",')), ("ReturnValue", "int", dict(out=True))])
    g.link(self_get(var, "int", x - 180, y + 160), n["A"])
    s = self_set(var, "int", x, y, comment)
    g.link(n["ReturnValue"], s[var])
    return s


def set_from(var, cat, x, y, src, comment="", sub="None", subcat=""):
    s = self_set(var, cat, x, y, comment, sub=sub, subcat=subcat)
    g.link(src, s[var])
    return s


def montage_time_since_reach(x, y):
    """(now - ReachStart) * PlayRate = where our montage is, in montage seconds."""
    dt = d_op("Subtract_DoubleDouble", x, y, now(x - 200, y), self_get("ReachStart", "real", x - 200, y + 80, subcat="double"))
    return d_op("Multiply_DoubleDouble", x + 180, y, dt, self_get("PlayRate", "real", x, y + 120, subcat="double"))


def montage_play(x, y, anim_pin, asset, rate_pin, comment):
    n = member_call(ANIMI, "Montage_Play", x, y, anim_pin, comment, [
        ("MontageToPlay", "object", dict(sub=MONT, extra=f'DefaultObject="{asset}",')),
        ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",')),
        ("ReturnValueType", "byte", dict(sub=EN("/Script/Engine.EMontagePlayReturnType"), extra='DefaultValue="MontageLength",')),
        ("InTimeToStartMontageAt", "real", dict(subcat="float", extra='DefaultValue="0.000000",')),
        ("bStopAllMontages", "bool", dict(extra='DefaultValue="false",')),
        ("ReturnValue", "real", dict(subcat="float", out=True))])
    if rate_pin is not None:
        g.link(rate_pin, n["InPlayRate"])
    return n


def montage_active(x, y, anim_pin, asset):
    n = member_pure(ANIMI, "Montage_IsActive", x, y, anim_pin,
                    [("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{asset}",')), RB])
    n.pins["Montage"].const = True
    return n["ReturnValue"]


def slot_active(x, y, anim_pin, slot):
    return member_pure(ANIMI, "IsSlotActive", x, y, anim_pin,
                       [("SlotNodeName", "name", dict(extra=f'DefaultValue="{slot}",')), RB])["ReturnValue"]


def obj_q(member, x, y, target, owner=OBJC):
    return member_pure(owner, member, x, y, target, [RB])["ReturnValue"]


def comp_of(x, y, actor_pin, comp_cls):
    return member_pure(ACTOR, "GetComponentByClass", x, y, actor_pin, [
        ("ComponentClass", "class", dict(sub=ACOMP, extra=f'DefaultObject="{comp_cls.split(chr(39))[1]}",')),
        ("ReturnValue", "object", dict(sub=comp_cls, out=True))])["ReturnValue"]


# =====================================================================
# Tick
# =====================================================================
g.box("EdGraphNode_Comment_900", -80, -160, 1500, 760, "Tick: player, mesh, anim instance")
tick = Node(g, BG + "K2Node_Event", nm("K2Node_Event"), 0, 0, "",
            [f"EventReference=(MemberParent={ACTOR},MemberName=\"ReceiveTick\")", "bOverrideFunction=True"])
tick.pin("OutputDelegate", "delegate", out=True)
tick.pins["OutputDelegate"].member_ref = f'MemberParent={ACTOR},MemberName="ReceiveTick"'
tick.pin("then", "exec", out=True)
tick.pin("DeltaSeconds", "real", subcat="float", out=True)

gp = lib_pure(GS, "GameplayStatics", "GetPlayerPawn", 0, 220,
              [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
               ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PAWN, out=True))])
cast = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), 300, 0, "player",
                      [f"TargetType=\"/Script/CoreUObject.Class'/Script/Stalker2.PC'\""]))
cast.pin("CastFailed", "exec", out=True)
cast.pin("Object", "object", sub=OBJ)
cast.pin("AsPC", "object", sub=PC, out=True)
cast.pin("bSuccess", "bool", out=True)
g.link(gp["ReturnValue"], cast["Object"])
g.link(tick["then"], cast["execute"])
as_pc = cast["AsPC"]
sq = sequence(700, 0, "tick steps", 5)
g.link(cast["then"], sq["execute"])
mesh = other_get(CHAR, "Mesh", "object", 700, 300, as_pc, sub=SKC)
anim = member_pure(SKC, "GetAnimInstance", 950, 300, mesh, [("ReturnValue", "object", dict(sub=ANIMI, out=True))])["ReturnValue"]

# ---- 0: once: tick after the animation update ----
X0, Y0 = 1200, -600
g.box("EdGraphNode_Comment_901", X0 - 80, Y0 - 120, 1200, 360, "Once: tick after the animation (hand bone of this frame)")
br0 = branch(X0, Y0, "first tick?", b_not(X0 - 160, Y0 + 160, self_get("Init", "bool", X0 - 340, Y0 + 160)))
g.link(sq["then_0"], br0["execute"])
stg = self_call("SetTickGroup", X0 + 300, Y0, "tick after anim update", [
    ("NewTickGroup", "byte", dict(sub=EN("/Script/Engine.ETickingGroup"), extra='DefaultValue="TG_PostUpdateWork",'))])
si0 = self_set("Init", "bool", X0 + 650, Y0, "", default="true")
g.link(br0["then"], stg["execute"])
g.link(stg["then"], si0["execute"])

# ---- 1: picked up? -> reach (or skip) ----
X1, Y1 = 1200, 1000
g.box("EdGraphNode_Comment_902", X1 - 80, Y1 - 200, 6200, 2600, "Picked up? Then reach with the left hand and fly a copy of the item into it")
item = lambda x, y: self_get("Item", "object", x, y, sub=ACTOR)
icomp = lambda x, y: self_get("ItemComp", "object", x, y, sub=SC_)
recent = d_op("Less_DoubleDouble", X1 - 100, Y1 + 600,
              d_op("Subtract_DoubleDouble", X1 - 300, Y1 + 600, now(X1 - 500, Y1 + 600),
                   self_get("ItemSeen", "real", X1 - 500, Y1 + 680, subcat="double")),
              self_get("SeenWindow", "real", X1 - 300, Y1 + 720, subcat="double"), ret=RB)
loc_now = member_pure(SC_, "K2_GetComponentLocation", X1 - 500, Y1 + 1100, icomp(X1 - 700, Y1 + 1100),
                      [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
bx = kml("BreakTransform", X1 - 500, Y1 + 1220, [("InTransform", "struct", dict(sub=XFORM)),
                                                ("Location", "struct", dict(sub=VEC, out=True)),
                                                ("Rotation", "struct", dict(sub=ROT, out=True)),
                                                ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(self_get("ItemXf", "struct", X1 - 700, Y1 + 1220, sub=XFORM), bx["InTransform"])
dist = kml("Vector_Distance", X1 - 300, Y1 + 1160, [("V1", "struct", dict(sub=VEC)), ("V2", "struct", dict(sub=VEC)), RD])
g.link(loc_now, dist["V1"])
g.link(bx["Location"], dist["V2"])
moved = d_op("Greater_DoubleDouble", X1 - 120, Y1 + 1160, dist["ReturnValue"], b_const="150.0", ret=RB)
vis = member_pure(SC_, "IsVisible", X1 - 500, Y1 + 1000, icomp(X1 - 700, Y1 + 1000), [RB])["ReturnValue"]
gone = b_or(X1 - 100, Y1 + 800,
            b_not(X1 - 300, Y1 + 800, is_valid(X1 - 500, Y1 + 800, item(X1 - 700, Y1 + 800))),
            b_not(X1 - 300, Y1 + 900, is_valid(X1 - 500, Y1 + 900, icomp(X1 - 700, Y1 + 900))),
            b_not(X1 - 300, Y1 + 1000, vis), moved)
br1 = branch(X1, Y1, "the item we looked at is gone? (picked up)",
             b_and(X1 - 80, Y1 + 400, self_get("ItemArmed", "bool", X1 - 300, Y1 + 400), recent, gone))
g.link(sq["then_1"], br1["execute"])
dis1 = self_set("ItemArmed", "bool", X1 + 300, Y1, "handled", default="false")
np1 = inc("NPickups", X1 + 600, Y1, "count pickups")
g.link(br1["then"], dis1["execute"])
g.link(dis1["then"], np1["execute"])

# skip conditions (each also a bit in SkipBits for the probe)
SX, SY = X1 + 400, Y1 + 600
conds = [
    ("sprint", obj_q("IsSprinting", SX, SY, as_pc)),
    ("aim", obj_q("IsAiming", SX, SY + 80, as_pc)),
    ("action", slot_active(SX, SY + 160, anim, "MainActionSlot")),
    ("lefthand", b_and(SX + 240, SY + 240, slot_active(SX, SY + 240, anim, "LeftHand"),
                       b_not(SX + 200, SY + 320, montage_active(SX, SY + 320, anim, GRAB)))),
    ("dialog", obj_q("IsInStaticDialog", SX, SY + 400, as_pc, owner=PC)),
    ("cinematic", obj_q("IsInCinematic", SX, SY + 480, as_pc)),
    ("detector", obj_q("IsDetectorInHands", SX, SY + 560, as_pc)),
    ("binoculars", obj_q("IsBinocularsInHands", SX, SY + 640, as_pc)),
    ("disabled", b_not(SX + 200, SY + 720, self_get("Enabled", "bool", SX, SY + 720))),
]
skip = b_or(SX + 600, SY, *[c for _, c in conds])
bits = None
for k, (_, c) in enumerate(conds + [("lefthandbusy", obj_q("IsLeftHandBusy", SX, SY + 800, as_pc))]):
    sel = kml("SelectInt", SX + 900, SY + 100 * k, [("A", "int", dict(extra=f'DefaultValue="{1 << k}",')),
                                                    ("B", "int", dict(extra='DefaultValue="0",')),
                                                    ("bPickA", "bool", dict(extra='DefaultValue="false",')),
                                                    ("ReturnValue", "int", dict(out=True))])
    g.link(c, sel["bPickA"])
    if bits is None:
        bits = sel["ReturnValue"]
    else:
        add = kml("Add_IntInt", SX + 1100, SY + 100 * k, [("A", "int", dict(extra='DefaultValue="0",')),
                                                          ("B", "int", dict(extra='DefaultValue="0",')),
                                                          ("ReturnValue", "int", dict(out=True))])
        g.link(bits, add["A"])
        g.link(sel["ReturnValue"], add["B"])
        bits = add["ReturnValue"]
sbits = set_from("SkipBits", "int", X1 + 900, Y1, bits, "why (probe): 1 sprint 2 aim 4 action 8 left-hand montage "
                 "16 dialog 32 cutscene 64 detector 128 binoculars 256 disabled 512 IsLeftHandBusy (info)")
g.link(np1["then"], sbits["execute"])
brs = branch(X1 + 1250, Y1, "skip? (vanilla pickup, no reach)", skip)
g.link(sbits["then"], brs["execute"])
ns = inc("NSkips", X1 + 1550, Y1 - 300, "count skips")
g.link(brs["then"], ns["execute"])

# reach
sqr = sequence(X1 + 1550, Y1 + 100, "reach steps", 3)
g.link(brs["else"], sqr["execute"])
#   a) an older flying copy goes away
fv = branch(X1 + 1850, Y1 - 100, "older copy still flying?", is_valid(X1 + 1700, Y1 - 160, self_get("Fly", "object", X1 + 1500, Y1 - 160, sub=ACTOR)))
g.link(sqr["then_0"], fv["execute"])
fd = member_call(ACTOR, "K2_DestroyActor", X1 + 2150, Y1 - 100, self_get("Fly", "object", X1 + 1950, Y1 - 160, sub=ACTOR), "remove it")
g.link(fv["then"], fd["execute"])
#   b) the montage, unless one is already before its pocketing frame
early = d_op("Less_DoubleDouble", X1 + 1900, Y1 + 500, montage_time_since_reach(X1 + 1700, Y1 + 500),
             d_op("Subtract_DoubleDouble", X1 + 1700, Y1 + 640, self_get("PocketTime", "real", X1 + 1500, Y1 + 640, subcat="double"),
                  b_const="0.1"), ret=RB)
inreach = b_and(X1 + 2050, Y1 + 420, montage_active(X1 + 1850, Y1 + 400, anim, GRAB), early)
bm = branch(X1 + 2150, Y1 + 150, "a reach already before its pocketing frame? (then the new item joins it)", inreach)
g.link(sqr["then_1"], bm["execute"])
mp = montage_play(X1 + 2450, Y1 + 250, anim, GRAB, self_get("PlayRate", "real", X1 + 2250, Y1 + 450, subcat="double"),
                  "left-hand grab (LeftHand slot)")
g.link(bm["else"], mp["execute"])
srs = set_from("ReachStart", "real", X1 + 2800, Y1 + 250, now(X1 + 2650, Y1 + 450), "reach started", subcat="double")
srg = self_set("Reaching", "bool", X1 + 3100, Y1 + 250, "", default="true")
nr = inc("NReaches", X1 + 3400, Y1 + 250, "count reaches")
chain(mp, srs, srg, nr)
#   c) the flying copy
FX, FY = X1 + 1850, Y1 + 900
sfs = set_from("FlyStart", "real", FX, FY, now(FX - 150, FY + 200), "flight starts", subcat="double")
g.link(sqr["then_2"], sfs["execute"])
grab_real = d_op("Divide_DoubleDouble", FX + 100, FY + 350, self_get("GrabTime", "real", FX - 100, FY + 350, subcat="double"),
                 self_get("PlayRate", "real", FX - 100, FY + 430, subcat="double"))
arrive = d_op("Add_DoubleDouble", FX + 280, FY + 350, self_get("ReachStart", "real", FX + 100, FY + 270, subcat="double"), grab_real)
left = d_op("Subtract_DoubleDouble", FX + 460, FY + 350, arrive, now(FX + 280, FY + 450))
fdur = d_op("FMax", FX + 640, FY + 350, left, b_const="0.12")
sfd = set_from("FlyDur", "real", FX + 300, FY, fdur, "arrive at the grab frame (at least 0.12 s)", subcat="double")
sfa = self_set("FlyAttached", "bool", FX + 600, FY, "", default="false")
bx2 = kml("BreakTransform", FX + 700, FY + 500, [("InTransform", "struct", dict(sub=XFORM)),
                                                ("Location", "struct", dict(sub=VEC, out=True)),
                                                ("Rotation", "struct", dict(sub=ROT, out=True)),
                                                ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(self_get("ItemXf", "struct", FX + 500, FY + 500, sub=XFORM), bx2["InTransform"])
sff = set_from("FlyFrom", "struct", FX + 900, FY, bx2["Location"], "from where the item was", sub=VEC)
chain(sfs, sfd, sfa, sff)
bsm = branch(FX + 1200, FY, "static mesh item?", is_valid(FX + 1050, FY + 200, self_get("ItemMesh", "object", FX + 850, FY + 200, sub=SM)))
g.link(sff["then"], bsm["execute"])


def spawn_copy(x, y, actor_cls, comp_var, comment):
    sp = exec_pins(Node(g, BG + "K2Node_SpawnActorFromClass", nm("K2Node_SpawnActorFromClass"), x, y, comment))
    sp.pin("Class", "class", sub=ACTOR, extra=f'DefaultObject="{actor_cls.split(chr(39))[1]}",')
    sp.pin("ReturnValue", "object", sub=actor_cls, out=True)
    sp.pin("WorldContextObject", "object", sub=OBJ, hidden=True)
    sp.pin("SpawnTransform", "struct", sub=XFORM)
    sp.pin("CollisionHandlingOverride", "byte", sub=EN("/Script/Engine.ESpawnActorCollisionHandlingMethod"),
           extra='DefaultValue="AlwaysSpawn",')
    sp.pin("TransformScaleMethod", "byte", sub=EN("/Script/Engine.ESpawnActorScaleMethod"), adv=True,
           extra='DefaultValue="MultiplyWithRoot",')
    sp.pin("Owner", "object", sub=ACTOR, adv=True)
    g.link(self_get("ItemXf", "struct", x - 200, y + 300, sub=XFORM), sp["SpawnTransform"])
    comp_cls = SMC if actor_cls == SMA else SKC
    comp = other_get(actor_cls, comp_var, "object", x + 250, y + 300, sp["ReturnValue"], sub=comp_cls)
    mob = member_call(SC_, "SetMobility", x + 350, y, comp, "movable",
                      [("NewMobility", "byte", dict(sub=EN("/Script/Engine.EComponentMobility"), extra='DefaultValue="Movable",'))])
    if actor_cls == SMA:
        setm = member_call(SMC, "SetStaticMesh", x + 650, y, comp, "the item's mesh",
                           [("NewMesh", "object", dict(sub=SM)), RB])
        g.link(self_get("ItemMesh", "object", x + 450, y + 300, sub=SM), setm["NewMesh"])
    else:
        setm = member_call(SKC, "SetSkeletalMeshAsset", x + 650, y, comp, "the item's mesh",
                           [("NewMesh", "object", dict(sub=SKMESH))])
        g.link(self_get("ItemSkel", "object", x + 450, y + 300, sub=SKMESH), setm["NewMesh"])
    col = member_call(PRIM, "SetCollisionEnabled", x + 950, y, comp, "no collision",
                      [("NewType", "byte", dict(sub=EN("/Script/Engine.ECollisionEnabled"), extra='DefaultValue="NoCollision",'))])
    sf = set_from("Fly", "object", x + 1250, y, sp["ReturnValue"], "the flying copy", sub=ACTOR)
    nf = inc("NFly", x + 1550, y, "count copies")
    chain(sp, mob, setm, col, sf, nf)
    return sp


sp_sm = spawn_copy(FX + 1500, FY - 100, SMA, "StaticMeshComponent", "copy of a static-mesh item")
g.link(bsm["then"], sp_sm["execute"])
bsk = branch(FX + 1500, FY + 500, "skeletal mesh item?", is_valid(FX + 1350, FY + 700, self_get("ItemSkel", "object", FX + 1150, FY + 700, sub=SKMESH)))
g.link(bsm["else"], bsk["execute"])
sp_sk = spawn_copy(FX + 1800, FY + 500, SKA, "SkeletalMeshComponent", "copy of a skeletal-mesh item")
g.link(bsk["then"], sp_sk["execute"])

# ---- 2: track the loose item under the crosshair ----
X2, Y2 = 1200, 4000
g.box("EdGraphNode_Comment_903", X2 - 80, Y2 - 200, 3600, 1300, "Track the loose item we are looking at (its mesh and where it is)")
tgt = member_pure(PC, "GetInteractionTarget", X2 - 400, Y2 + 200, as_pc, [("ReturnValue", "object", dict(sub=ICOMP, out=True))])["ReturnValue"]
bt = branch(X2, Y2, "looking at something interactable?", is_valid(X2 - 150, Y2 + 200, tgt))
g.link(sq["then_2"], bt["execute"])
own = member_pure(ACOMP, "GetOwner", X2 - 150, Y2 + 320, tgt, [("ReturnValue", "object", dict(sub=ACTOR, out=True))])["ReturnValue"]
c2 = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), X2 + 300, Y2, "a loose item?",
                    [f"TargetType=\"/Script/CoreUObject.Class'{IIC}'\""]))
c2.pin("CastFailed", "exec", out=True)
c2.pin("Object", "object", sub=OBJ)
c2.pin("AsInteractable Item Container", "object", sub=cls(IIC), out=True)
c2.pin("bSuccess", "bool", out=True)
g.link(own, c2["Object"])
g.link(bt["then"], c2["execute"])
the_item = c2["AsInteractable Item Container"]
sq2 = sequence(X2 + 650, Y2, "track steps", 2)
g.link(c2["then"], sq2["execute"])
neq = kml("NotEqual_ObjectObject", X2 + 650, Y2 + 300, [("A", "object", dict(sub=OBJ)), ("B", "object", dict(sub=OBJ)), RB])
g.link(the_item, neq["A"])
g.link(item(X2 + 450, Y2 + 380), neq["B"])
bn = branch(X2 + 950, Y2 - 100, "a different item than before?", neq["ReturnValue"])
g.link(sq2["then_0"], bn["execute"])
si = set_from("Item", "object", X2 + 1250, Y2 - 100, the_item, "remember it", sub=ACTOR)
smc = comp_of(X2 + 1250, Y2 + 200, the_item, SMC)
skc = comp_of(X2 + 1250, Y2 + 320, the_item, SKC)
sim = set_from("ItemMesh", "object", X2 + 1550, Y2 - 100,
               other_get(SMC, "StaticMesh", "object", X2 + 1500, Y2 + 200, smc, sub=SM), "its static mesh (if any)", sub=SM)
sis = set_from("ItemSkel", "object", X2 + 1850, Y2 - 100,
               member_pure(SKC, "GetSkeletalMeshAsset", X2 + 1500, Y2 + 320, skc,
                           [("ReturnValue", "object", dict(sub=SKMESH, out=True))])["ReturnValue"],
               "its skeletal mesh (if any)", sub=SKMESH)
chain(si, sim, sis)
g.link(bn["then"], si["execute"])
bc = branch(X2 + 2150, Y2 - 100, "static mesh component?", is_valid(X2 + 2000, Y2 + 200, smc))
g.link(sis["then"], bc["execute"])
g.link(bc["then"], set_from("ItemComp", "object", X2 + 2450, Y2 - 200, smc, "its mesh component", sub=SC_)["execute"])
g.link(bc["else"], set_from("ItemComp", "object", X2 + 2450, Y2 + 100, skc, "its mesh component", sub=SC_)["execute"])
sseen = set_from("ItemSeen", "real", X2 + 950, Y2 + 600, now(X2 + 800, Y2 + 800), "seen now", subcat="double")
g.link(sq2["then_1"], sseen["execute"])
sarm = self_set("ItemArmed", "bool", X2 + 1250, Y2 + 600, "", default="true")
xf = member_pure(SC_, "K2_GetComponentToWorld", X2 + 1350, Y2 + 850, icomp(X2 + 1150, Y2 + 850),
                 [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
sxf = set_from("ItemXf", "struct", X2 + 1550, Y2 + 600, xf, "where it is", sub=XFORM)
chain(sseen, sarm, sxf)

# ---- 3: fly the copy into the left hand ----
X3, Y3 = 1200, 5800
g.box("EdGraphNode_Comment_904", X3 - 80, Y3 - 200, 3400, 1300, "Fly the copy into the left hand, hold it, pocket it")
fly = lambda x, y: self_get("Fly", "object", x, y, sub=ACTOR)
bf = branch(X3, Y3, "a copy is flying?", is_valid(X3 - 150, Y3 + 200, fly(X3 - 350, Y3 + 200)))
g.link(sq["then_3"], bf["execute"])
el = d_op("Subtract_DoubleDouble", X3 - 300, Y3 + 500, now(X3 - 500, Y3 + 500), self_get("FlyStart", "real", X3 - 500, Y3 + 580, subcat="double"))
alpha_raw = d_op("Divide_DoubleDouble", X3 - 100, Y3 + 500, el, self_get("FlyDur", "real", X3 - 300, Y3 + 620, subcat="double"))
cl = kml("FClamp", X3 + 100, Y3 + 500, [D("Value"), D("Min", "0.0"), D("Max", "1.0"), RD])
g.link(alpha_raw, cl["Value"])
alpha = cl["ReturnValue"]
hand = member_pure(SKC, "GetSocketLocation", X3 + 100, Y3 + 650, mesh,
                   [("InSocketName", "name", dict(extra=f'DefaultValue="{HAND}",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
sq3 = sequence(X3 + 300, Y3, "fly steps", 2)
g.link(bf["then"], sq3["execute"])
ba = branch(X3 + 600, Y3 - 100, "still on the way?", d_op("Less_DoubleDouble", X3 + 400, Y3 + 150, alpha, b_const="1.0", ret=RB))
g.link(sq3["then_0"], ba["execute"])
ve = kml("VEase", X3 + 650, Y3 + 300, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)),
                                       ("Alpha", "real", dict(subcat="float", extra='DefaultValue="0.0",')),
                                       ("EasingFunc", "byte", dict(sub=EN("/Script/Engine.EEasingFunc"), extra='DefaultValue="EaseIn",')),
                                       ("BlendExp", "real", dict(subcat="float", extra='DefaultValue="2.000000",')),
                                       ("Steps", "int", dict(extra='DefaultValue="2",')),
                                       ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(self_get("FlyFrom", "struct", X3 + 450, Y3 + 300, sub=VEC), ve["A"])
g.link(hand, ve["B"])
g.link(alpha, ve["Alpha"])
sl = member_call(ACTOR, "K2_SetActorLocation", X3 + 950, Y3 - 100, fly(X3 + 800, Y3 + 100), "toward the hand", [
    ("NewLocation", "struct", dict(sub=VEC)), B("bSweep"),
    ("SweepHitResult", "struct", dict(sub=HIT, out=True)), B("bTeleport", "true"), RB])
g.link(ve["ReturnValue"], sl["NewLocation"])
g.link(ba["then"], sl["execute"])
bat = branch(X3 + 950, Y3 + 200, "arrived, not attached yet?", b_not(X3 + 800, Y3 + 400, self_get("FlyAttached", "bool", X3 + 600, Y3 + 400)))
g.link(ba["else"], bat["execute"])
RULE = EN("/Script/Engine.EAttachmentRule")
att = member_call(ACTOR, "K2_AttachToComponent", X3 + 1250, Y3 + 200, fly(X3 + 1100, Y3 + 450), "into the left hand", [
    ("Parent", "object", dict(sub=SC_)), ("SocketName", "name", dict(extra=f'DefaultValue="{HAND}",')),
    ("LocationRule", "byte", dict(sub=RULE, extra='DefaultValue="SnapToTarget",')),
    ("RotationRule", "byte", dict(sub=RULE, extra='DefaultValue="KeepWorld",')),
    ("ScaleRule", "byte", dict(sub=RULE, extra='DefaultValue="KeepWorld",')),
    B("bWeldSimulatedBodies"), RB])
g.link(mesh, att["Parent"])
g.link(bat["then"], att["execute"])
satt = self_set("FlyAttached", "bool", X3 + 1600, Y3 + 200, "", default="true")
g.link(att["then"], satt["execute"])
pocket = b_and(X3 + 900, Y3 + 800, d_op("GreaterEqual_DoubleDouble", X3 + 700, Y3 + 750, alpha, b_const="1.0", ret=RB),
               d_op("GreaterEqual_DoubleDouble", X3 + 700, Y3 + 850, montage_time_since_reach(X3 + 500, Y3 + 850),
                    self_get("PocketTime", "real", X3 + 500, Y3 + 1000, subcat="double"), ret=RB))
stale = d_op("Greater_DoubleDouble", X3 + 700, Y3 + 1050, el, b_const="3.0", ret=RB)
bp = branch(X3 + 1250, Y3 + 600, "pocketed? (or stuck for 3 s)", b_or(X3 + 1050, Y3 + 900, pocket, stale))
g.link(sq3["then_1"], bp["execute"])
fdx = member_call(ACTOR, "K2_DestroyActor", X3 + 1550, Y3 + 600, fly(X3 + 1400, Y3 + 800), "gone into the pocket")
g.link(bp["then"], fdx["execute"])

# ---- 4: recover the left hand if our montage was cut ----
X4, Y4 = 1200, 7600
g.box("EdGraphNode_Comment_905", X4 - 80, Y4 - 200, 2600, 1100, "Reach cut short? Put the left hand back on the weapon")
br4 = branch(X4, Y4, "our reach ended?", b_and(X4 - 100, Y4 + 250, self_get("Reaching", "bool", X4 - 300, Y4 + 200),
                                                b_not(X4 - 300, Y4 + 300, montage_active(X4 - 500, Y4 + 300, anim, GRAB))))
g.link(sq["then_4"], br4["execute"])
sr4 = self_set("Reaching", "bool", X4 + 300, Y4, "", default="false")
g.link(br4["then"], sr4["execute"])
cut = d_op("Less_DoubleDouble", X4 + 300, Y4 + 400, montage_time_since_reach(X4 + 100, Y4 + 400),
           self_get("IKOnTime", "real", X4 + 100, Y4 + 550, subcat="double"), ret=RB)
br4b = branch(X4 + 600, Y4, "cut before the hand-on-grip notify, weapon held, no other left-hand montage?",
              b_and(X4 + 500, Y4 + 300, cut, obj_q("HasItemInMainHand", X4 + 300, Y4 + 650, as_pc),
                    b_not(X4 + 300, Y4 + 750, slot_active(X4 + 100, Y4 + 750, anim, "LeftHand"))))
g.link(sr4["then"], br4b["execute"])
mr = montage_play(X4 + 950, Y4, anim, RETURN, None, "hand back on the grip")
g.link(br4b["then"], mr["execute"])
nrc = inc("NRecover", X4 + 1300, Y4, "count recoveries")
g.link(mr["then"], nrc["execute"])

write(sys.argv[1], g.text())
print("ok", len(g.nodes), "nodes")
