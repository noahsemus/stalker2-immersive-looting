"""Generates the whole BP_ImmLootActor event graph (select all in the graph, delete, paste this, compile, save).

What it does (PLAN.md):
  Event Tick -> player -> Sequence
    0 Once: load IMC_Inventory (game path). (Changing the tick group here stopped the tick: build 2.)
    1 Picked up?  The loose item we were looking at (cached by step 4, seen < SeenWindow s ago) is gone:
                  destroyed, its mesh hidden, or moved away. -> NPickups += 1, PendingReach + PendingCopy.
    2 Loot window (corpse / stash; the backpack, corpses and stashes share W_Inventory and IMC_Inventory):
                  opened (IMC_Inventory applied) -> classify the target cached the tick before (DeadBody = corpse,
                  InteractableItemContainer owner = stash), find the two CurrentWeightText widgets and the view;
                  while open, the first 0.3 s set the baseline, then "took" = player weight up, loot weight down
                  or more money; closed (context gone 0.25 s and the view hidden, or 3 s) and took -> PendingReach
                  without a copy.
    3 Pending reach: skip (sprint, aim, MainActionSlot action, another left-hand montage, dialogue, cutscene,
                  detector or binoculars in hand, Enabled off) -> NSkips += 1, SkipBits = why
                  else -> the grab montage (AM_ImmLoot_Grab, LeftHand slot) unless one is already before its
                  pocketing frame, and (PendingCopy) a copy of the item (StaticMeshActor / SkeletalMeshActor)
                  spawned where the item was.
    4 Track:      PC.GetInteractionTarget -> owner -> InteractableItemContainer: remember the actor, its
                  mesh component and mesh asset (when the target changes) and its world transform (every tick).
    5 Fly:        the copy eases to the left-hand bone jnt_l_weapon, arriving at the grab frame; then it is
                  attached to the hand and destroyed at the pocketing frame.
    6 Recover:    our montage stopped before its "hand back on the grip" notify (interrupted) while a weapon
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
GRAB = "/ImmersiveLooting/Runtime/AM_ImmLoot_Grab.AM_ImmLoot_Grab"   # build 1-3 montage (unused since build 4)
GRAB_SEQ = "/ImmersiveLooting/Runtime/AS_ImmLoot_Grab.AS_ImmLoot_Grab"   # build 4: hand raised into view (make_grab_seq)
ANIMSEQB = cls("/Script/Engine.AnimSequenceBase")
PCM = cls("/Script/Engine.PlayerCameraManager")
KMATL = cls("/Script/Engine.KismetMaterialLibrary")
MPC_CLS = cls("/Script/Engine.MaterialParameterCollection")
MPC_FOV = "/Game/_Stalker_2/Materials/MPC/MPC_FOV.MPC_FOV"
RETURN = ("/Game/_STALKER2/Animations/Player/AnimSequences/ar/common/showhide/lefthand/"
          "MG_fp_return_left_hand_on_item.MG_fp_return_left_hand_on_item")
HAND = "jnt_l_weapon"
IMC_CLS = cls("/Script/EnhancedInput.InputMappingContext")
EILPS = cls("/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem")
EISI = cls("/Script/EnhancedInput.EnhancedInputSubsystemInterface")
SOP = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.SoftObjectPath'\""
IMC_DIR = "/Game/_Stalker_2/data/input/InputMappingContexts/"
UW = cls("/Script/UMG.UserWidget")
WBL = cls("/Script/UMG.WidgetBlueprintLibrary")
TEXTW = cls("/Script/Stalker2.TextWidget")
KTXT = cls("/Script/Engine.KismetTextLibrary")
KSTR = cls("/Script/Engine.KismetStringLibrary")
WTEXT_PATH = "/Game/GameLite/FPS_Game/UIRemaster/CommonWidgets/W_Text.W_Text_C"
WINV_PATH = "/Game/GameLite/FPS_Game/UIRemaster/Inventory/W_Inventory.W_Inventory_C"
WTEXT = "\"/Script/UMG.WidgetBlueprintGeneratedClass'%s'\"" % WTEXT_PATH
WINV = "\"/Script/UMG.WidgetBlueprintGeneratedClass'%s'\"" % WINV_PATH
FOREACH = ("MacroGraphReference=(MacroGraph=\"/Script/Engine.EdGraph'/Engine/EditorBlueprintResources/StandardMacros."
           "StandardMacros:ForEachLoop'\",GraphBlueprint=\"/Script/Engine.Blueprint'/Engine/EditorBlueprintResources/"
           "StandardMacros.StandardMacros'\",GraphGuid=99DBFD5540A796041F72A5A9DA655026)")
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


def d_op(member, x, y, a, b=None, b_const="0.0", ret=RD, a_const="0.0"):
    n = kml(member, x, y, [D("A", a_const), D("B", b_const), ret])
    if a is not None:
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


def lib_call(lib, member, x, y, comment, pins, default_obj):
    n = exec_pins(Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), x, y, comment,
                       [f"FunctionReference=(MemberParent={lib},MemberName=\"{member}\")"]))
    n.pin("self", "object", sub=lib, hidden=True, extra=f'DefaultObject="{default_obj}",')
    return add_pins(n, pins)


def for_each(x, y, comment, elem_cls):
    """StandardMacros ForEachLoop (GraphGuid read from the kit's Engine/Content/EditorBlueprintResources/StandardMacros)."""
    n = Node(g, BG + "K2Node_MacroInstance", nm("K2Node_MacroInstance"), x, y, comment,
             [FOREACH, f"ResolvedWildcardType=(PinCategory=\"object\",PinSubCategoryObject={elem_cls})"])
    n.pin("Exec", "exec")
    n.pin("Array", "object", sub=elem_cls)
    n.pins["Array"].container = "Array"
    n.pin("LoopBody", "exec", out=True)
    n.pin("Array Element", "object", sub=elem_cls, out=True)
    n.pin("Array Index", "int", out=True)
    n.pin("Completed", "exec", out=True)
    return n


def kml_int_gt(x, y, a, b_const):
    n = kml("Greater_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')),
                                     ("B", "int", dict(extra=f'DefaultValue="{b_const}",')), RB])
    g.link(a, n["A"])
    return n["ReturnValue"]


def load_imc(x, y, name, prev_then, comment):
    mk = lib_pure(KSL, "KismetSystemLibrary", "MakeSoftObjectPath", x, y + 250,
                  [("PathString", "string", dict(extra=f'DefaultValue="{IMC_DIR}{name}.{name}",')),
                   ("ReturnValue", "struct", dict(sub=SOP, out=True))])
    cv = lib_pure(KSL, "KismetSystemLibrary", "Conv_SoftObjPathToSoftObjRef", x + 250, y + 250,
                  [("SoftObjectPath", "struct", dict(sub=SOP)), ("ReturnValue", "softobject", dict(sub=OBJ, out=True))])
    cv.pins["SoftObjectPath"].ref = True
    cv.pins["SoftObjectPath"].const = True
    g.link(mk["ReturnValue"], cv["SoftObjectPath"])
    ld = lib_call(KSL, "LoadAsset_Blocking", x + 150, y, comment, [("Asset", "softobject", dict(sub=OBJ)),
                                                                  ("ReturnValue", "object", dict(sub=OBJ, out=True))],
                  "/Script/Engine.Default__KismetSystemLibrary")
    g.link(cv["ReturnValue"], ld["Asset"])
    g.link(prev_then, ld["execute"])
    c = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), x + 450, y, f"{name} loaded",
                       [f"TargetType={IMC_CLS}"]))
    c.pin("CastFailed", "exec", out=True)
    c.pin("Object", "object", sub=OBJ)
    c.pin("AsInput Mapping Context", "object", sub=IMC_CLS, out=True)
    c.pin("bSuccess", "bool", out=True)
    g.link(ld["ReturnValue"], c["Object"])
    g.link(ld["then"], c["execute"])
    return c


def looked_at(x, y):
    """The actor under the crosshair: PC.GetInteractedActor, else the owner of PC.GetInteractionTarget (build 1
    read only the latter and never saw a loose item)."""
    ia = member_pure(PC, "GetInteractedActor", x, y, as_pc, [("ReturnValue", "object", dict(sub=ACTOR, out=True))])["ReturnValue"]
    it = member_pure(PC, "GetInteractionTarget", x, y + 100, as_pc, [("ReturnValue", "object", dict(sub=ICOMP, out=True))])["ReturnValue"]
    ow = member_pure(ACOMP, "GetOwner", x + 200, y + 100, it, [("ReturnValue", "object", dict(sub=ACTOR, out=True))])["ReturnValue"]
    sel = kml("SelectObject", x + 400, y, [("A", "object", dict(sub=OBJ)), ("B", "object", dict(sub=OBJ)),
                                           B("bSelectA"), ("ReturnValue", "object", dict(sub=OBJ, out=True))])
    g.link(ia, sel["A"])
    g.link(ow, sel["B"])
    g.link(is_valid(x + 200, y - 100, ia), sel["bSelectA"])
    return sel["ReturnValue"]


def grab_active(x, y):
    """Our grab montage (a dynamic montage since build 4) is active. A None montage would ask about ANY montage."""
    gm = self_get("GrabMontage", "object", x - 200, y, sub=MONT)
    n = member_pure(ANIMI, "Montage_IsActive", x, y + 80, anim, [("Montage", "object", dict(sub=MONT)), RB])
    n.pins["Montage"].const = True
    g.link(self_get("GrabMontage", "object", x - 200, y + 80, sub=MONT), n["Montage"])
    return b_and(x + 200, y, is_valid(x, y - 80, gm), n["ReturnValue"])


def vop(member, x, y, a, b, ret_sub=VEC, b_cat="struct", b_sub=VEC, b_subcat=""):
    pins = [("A", "struct", dict(sub=VEC)), ("B", b_cat, dict(sub=b_sub, subcat=b_subcat)),
            ("ReturnValue", "struct" if ret_sub == VEC else "real", dict(sub=ret_sub if ret_sub == VEC else "None",
                                                                          subcat="" if ret_sub == VEC else "double", out=True))]
    n = kml(member, x, y, pins)
    g.link(a, n["A"])
    g.link(b, n["B"])
    return n["ReturnValue"]


def cam_basis(x, y):
    """Camera location, forward, right, up (the player camera manager)."""
    cm = lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", x, y,
                  [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                   ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"]
    loc = member_pure(PCM, "GetCameraLocation", x + 250, y, cm, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
    rot = member_pure(PCM, "GetCameraRotation", x + 250, y + 100, cm, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
    fov = member_pure(PCM, "GetFOVAngle", x + 250, y + 200, cm, [("ReturnValue", "real", dict(subcat="float", out=True))])["ReturnValue"]
    axes = []
    for k, fn in enumerate(("GetForwardVector", "GetRightVector", "GetUpVector")):
        n = kml(fn, x + 500, y + 100 * k, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
        g.link(rot, n["InRot"])
        axes.append(n["ReturnValue"])
    return loc, axes[0], axes[1], axes[2], fov


def mpc_scalar_call(x, y, name, comment):
    """KismetMaterialLibrary.GetScalarParameterValue is impure (a pure-looking paste gets pruned): an exec node."""
    return lib_call(KMATL, "GetScalarParameterValue", x, y, comment,
                    [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                     ("Collection", "object", dict(sub=MPC_CLS, extra=f'DefaultObject="{MPC_FOV}",')),
                     ("ParameterName", "name", dict(extra=f'DefaultValue="{name}",')),
                     ("ReturnValue", "real", dict(subcat="float", out=True))],
                    "/Script/Engine.Default__KismetMaterialLibrary")


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
sq = sequence(700, 0, "tick steps", 7)
g.link(cast["then"], sq["execute"])
mesh = other_get(CHAR, "Mesh", "object", 700, 300, as_pc, sub=SKC)
anim = member_pure(SKC, "GetAnimInstance", 950, 300, mesh, [("ReturnValue", "object", dict(sub=ANIMI, out=True))])["ReturnValue"]

# ---- 0: once: tick after the animation update ----
X0, Y0 = 1200, -600
g.box("EdGraphNode_Comment_901", X0 - 80, Y0 - 120, 1200, 360, "Once: load the inventory input context")
br0 = branch(X0, Y0, "first tick?", b_not(X0 - 160, Y0 + 160, self_get("Init", "bool", X0 - 340, Y0 + 160)))
ntk = inc("NTicks", X0 - 300, Y0 - 300, "tick counter (probe)")
g.link(sq["then_0"], ntk["execute"])
g.link(ntk["then"], br0["execute"])
stg = self_call("SetTickGroup", X0 + 300, Y0, "tick after anim update", [
    ("NewTickGroup", "byte", dict(sub=EN("/Script/Engine.ETickingGroup"), extra='DefaultValue="TG_PostUpdateWork",'))])
si0 = self_set("Init", "bool", X0 + 650, Y0, "", default="true")
g.link(br0["then"], stg["execute"])
g.link(stg["then"], si0["execute"])
imc_c = load_imc(X0 + 950, Y0, "IMC_Inventory", si0["then"], "inventory / loot input context (game path)")
sim0 = set_from("InvIMC", "object", X0 + 1700, Y0, imc_c["AsInput Mapping Context"], "remember it", sub=IMC_CLS)
g.link(imc_c["then"], sim0["execute"])

# ---- 1: picked up? -> pending reach with a copy ----
X1, Y1 = 1200, 1000
g.box("EdGraphNode_Comment_902", X1 - 80, Y1 - 200, 6200, 2600, "Picked up? (marks a pending reach; step 3 runs it: skip, or left-hand grab + a copy of the item flying into the hand)")
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
sp1 = self_set("PendingReach", "bool", X1 + 900, Y1 - 300, "reach pending", default="true")
sc1 = self_set("PendingCopy", "bool", X1 + 1200, Y1 - 300, "with a flying copy", default="true")
chain(np1, sp1, sc1)

# ---- 3: run a pending reach (from a pickup or a closed loot window): skip, or montage (+ flying copy) ----
X3R, Y3R = X1 + 300, Y1 + 2700
br3 = branch(X3R, Y3R, "a reach is pending?", self_get("PendingReach", "bool", X3R - 200, Y3R + 150))
g.link(sq["then_3"], br3["execute"])
spr = self_set("PendingReach", "bool", X3R + 300, Y3R, "taken", default="false")
g.link(br3["then"], spr["execute"])

# skip conditions (each also a bit in SkipBits for the probe)
SX, SY = X1 + 400, Y1 + 600
conds = [
    ("sprint", obj_q("IsSprinting", SX, SY, as_pc)),
    ("aim", obj_q("IsAiming", SX, SY + 80, as_pc)),
    ("action", slot_active(SX, SY + 160, anim, "MainActionSlot")),
    ("lefthand", b_and(SX + 240, SY + 240, slot_active(SX, SY + 240, anim, "LeftHand"),
                       b_not(SX + 200, SY + 320, grab_active(SX, SY + 320)))),
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
g.link(spr["then"], sbits["execute"])
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
inreach = b_and(X1 + 2050, Y1 + 420, grab_active(X1 + 1850, Y1 + 400), early)
bm = branch(X1 + 2150, Y1 + 150, "a reach already before its pocketing frame? (then the new item joins it)", inreach)
g.link(sqr["then_1"], bm["execute"])
GRAB_SEQ_BH = "/ImmersiveLooting/Runtime/AS_ImmLoot_GrabBH.AS_ImmLoot_GrabBH"
GRAB_SEQ_AR = "/ImmersiveLooting/Runtime/AS_ImmLoot_GrabAR.AS_ImmLoot_GrabAR"   # v0.2: same table, weapon in hand (corpse / stash touch)
IA_TOUCH = "/ImmersiveLooting/Input/IA_ImmLootInteract.IA_ImmLootInteract"
IMC_TOUCH = "/ImmersiveLooting/Input/IMC_ImmLoot.IMC_ImmLoot"
IA_INTERACT = "/Game/_Stalker_2/data/input/InputActions/Delayable/IA_Interact.IA_Interact"   # build 8: empty hands (make_grab_seq)


def play_grab(x, y, asset, comment):
    n = member_call(ANIMI, "PlaySlotAnimationAsDynamicMontage", x, y, anim, comment, [
        ("Asset", "object", dict(sub=ANIMSEQB, extra=f'DefaultObject="{asset}",')),
        ("SlotNodeName", "name", dict(extra='DefaultValue="LeftHand",')),
        ("BlendInTime", "real", dict(subcat="float", extra='DefaultValue="0.200000",')),
        ("BlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.700000",')),
        ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",')),
        ("LoopCount", "int", dict(extra='DefaultValue="1",')),
        ("BlendOutTriggerTime", "real", dict(subcat="float", extra='DefaultValue="-1.000000",')),
        ("InTimeToStartMontageAt", "real", dict(subcat="float", extra='DefaultValue="0.000000",')),
        ("ReturnValue", "object", dict(sub=MONT, out=True))])
    g.link(self_get("PlayRate", "real", x - 200, y + 200, subcat="double"), n["InPlayRate"])
    return n


armed = obj_q("HasItemInMainHand", X1 + 2250, Y1 + 100, as_pc)
bst = branch(X1 + 2450, Y1 + 150, "something in the main hand? (rifle-stance grab) else empty hands", armed)
g.link(bm["else"], bst["execute"])
mp = play_grab(X1 + 2750, Y1 - 50, GRAB_SEQ, "left-hand grab, armed")
mpb = play_grab(X1 + 2750, Y1 + 350, GRAB_SEQ_BH, "left-hand grab, empty hands (segment for the view pitch)")
# build 9: AS_ImmLoot_GrabBH is a table of 2 s segments, one per view pitch -75..+30 in 15 deg steps (the arm bones do
# not follow the view pitch); start at the nearest one
# build 12: AS_ImmLoot_GrabBH is a table of 1.5 s segments, one per (elevation, distance) of the item seen from the
# eye in the body frame (the arm bones do not follow the view pitch): elevation -80..+30 in 10 deg steps, distance
# 25..65 cm in 10 cm steps (65 = arm fully out toward it). Segment = ie * 5 + id, start = segment * 1.5 s.
XFT = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Transform'\""
_mx = member_pure(SC_, "K2_GetComponentToWorld", X1 + 1500, Y1 + 700, mesh, [("ReturnValue", "struct", dict(sub=XFT, out=True))])["ReturnValue"]
_cb = member_pure(SKC, "GetSocketLocation", X1 + 1500, Y1 + 800, mesh,
                  [("InSocketName", "name", dict(extra='DefaultValue="jnt_camera",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]


def _itl(x, y, loc):
    n = kml("InverseTransformLocation", x, y, [("T", "struct", dict(sub=XFT)), ("Location", "struct", dict(sub=VEC)),
                                               ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_mx, n["T"])
    g.link(loc, n["Location"])
    return n["ReturnValue"]


_rel = vop("Subtract_VectorVector", X1 + 1900, Y1 + 750, _itl(X1 + 1700, Y1 + 700, self_get("ItemCenter", "struct", X1 + 1500, Y1 + 900, sub=VEC)),
           _itl(X1 + 1700, Y1 + 800, _cb))
_bv = kml("BreakVector", X1 + 2100, Y1 + 750, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                              ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(_rel, _bv["InVec"])
_el = kml("DegAtan2", X1 + 2300, Y1 + 700, [D("Y"), D("X"), RD])
g.link(_bv["Z"], _el["Y"])
g.link(_bv["X"], _el["X"])
_dist = kml("VSize", X1 + 2300, Y1 + 850, [("A", "struct", dict(sub=VEC)), RD])
g.link(_rel, _dist["A"])


def _bin(x, y, val, offset, step, top):
    cl_ = kml("FClamp", x + 200, y, [D("Value"), D("Min", "0.0"), D("Max", f"{top}.0"), RD])
    g.link(d_op("Divide_DoubleDouble", x, y + 80, d_op("Add_DoubleDouble", x - 200, y + 80, val, b_const=offset), b_const=step), cl_["Value"])
    rd = kml("Round", x + 400, y, [D("A"), ("ReturnValue", "int", dict(out=True))])
    g.link(cl_["ReturnValue"], rd["A"])
    return rd["ReturnValue"]


# build 13: + azimuth (body frame, + = right): elevation -80..+25 step 15 (8), distance 30/45/60 (3), azimuth
# -45..+15 step 15 (5); segment = (ie * 3 + id) * 5 + ia
_az = kml("DegAtan2", X1 + 2300, Y1 + 1000, [D("Y"), D("X"), RD])
g.link(_bv["Y"], _az["Y"])
g.link(_bv["X"], _az["X"])
_ie = _bin(X1 + 2500, Y1 + 700, _el["ReturnValue"], "80.0", "15.0", 7)
_id = _bin(X1 + 2500, Y1 + 850, _dist["ReturnValue"], "-30.0", "15.0", 2)
_ia = _bin(X1 + 2500, Y1 + 1000, _az["ReturnValue"], "45.0", "15.0", 4)


def _imad(x, y, a, mul_const, b):
    m = kml("Multiply_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{mul_const}",')),
                                      ("ReturnValue", "int", dict(out=True))])
    g.link(a, m["A"])
    ad = kml("Add_IntInt", x + 150, y + 50, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="0",')),
                                            ("ReturnValue", "int", dict(out=True))])
    g.link(m["ReturnValue"], ad["A"])
    g.link(b, ad["B"])
    return ad["ReturnValue"]


_sum = {"ReturnValue": _imad(X1 + 3100, Y1 + 800, _imad(X1 + 2950, Y1 + 700, _ie, 3, _id), 5, _ia)}
_cv = kml("Conv_IntToDouble", X1 + 3250, Y1 + 750, [("InInt", "int"), RD])
g.link(_sum["ReturnValue"], _cv["InInt"])
seg_start = d_op("Multiply_DoubleDouble", X1 + 3400, Y1 + 750, _cv["ReturnValue"], b_const="1.5")
g.link(seg_start, mpb["InTimeToStartMontageAt"])
sss0 = set_from("SegStart", "real", X1 + 3700, Y1 + 350, seg_start, "segment start (montage s)", subcat="double")
_pv = [set_from(v, "real", X1 + 4000 + 300 * k, Y1 + 350, src_pin, "item seen from the eye, body frame (probe)" if k == 0 else "", subcat="double")
       for k, (v, src_pin) in enumerate((("ItemElev", _el["ReturnValue"]), ("ItemDist", _dist["ReturnValue"]), ("ItemAzim", _az["ReturnValue"])))]
chain(sss0, *_pv)
sss = {"execute": sss0["execute"], "then": _pv[-1]["then"]}
blr = branch(X1 + 2600, Y1 - 300, "a corpse / stash touch? (rifle-stance reach table) else the item grab", self_get("LootReach", "bool", X1 + 2400, Y1 - 200))
g.link(bst["then"], blr["execute"])
g.link(blr["else"], mp["execute"])
mpa = play_grab(X1 + 2750, Y1 - 450, GRAB_SEQ_AR, "left-hand touch, armed (segment for the target)")
g.link(seg_start, mpa["InTimeToStartMontageAt"])
g.link(blr["then"], mpa["execute"])
sgm_c = set_from("GrabMontage", "object", X1 + 3100, Y1 - 450, mpa["ReturnValue"], "our montage", sub=MONT)
ses_c = self_set("GrabBH", "bool", X1 + 3400, Y1 - 450, "", default="false")
ses_c2 = set_from("SegStart", "real", X1 + 3700, Y1 - 450, seg_start, "segment start", subcat="double")
chain(mpa, sgm_c, ses_c, ses_c2)
g.link(bst["else"], mpb["execute"])
sgm_a = set_from("GrabMontage", "object", X1 + 3100, Y1 - 50, mp["ReturnValue"], "our montage", sub=MONT)
sgm_b = set_from("GrabMontage", "object", X1 + 3100, Y1 + 350, mpb["ReturnValue"], "our montage", sub=MONT)
ses_a = self_set("GrabBH", "bool", X1 + 3400, Y1 - 50, "", default="false")
ses_a2 = self_set("SegStart", "real", X1 + 3700, Y1 - 50, "", default="0.0", subcat="double")
ses_b = self_set("GrabBH", "bool", X1 + 3400, Y1 + 350, "", default="true")
chain(mp, sgm_a, ses_a, ses_a2)
chain(mpb, sgm_b, ses_b, sss)
srs = set_from("ReachStart", "real", X1 + 2800, Y1 + 250, now(X1 + 2650, Y1 + 450), "reach started", subcat="double")
srg = self_set("Reaching", "bool", X1 + 3100, Y1 + 250, "", default="true")
nr = inc("NReaches", X1 + 3400, Y1 + 250, "count reaches")
g.link(ses_a2["then"], srs["execute"])
g.link(ses_c2["then"], srs["execute"])
g.link(sss["then"], srs["execute"])
chain(srs, srg, nr)
#   c) the flying copy
FX, FY = X1 + 1850, Y1 + 900
sfs = set_from("FlyStart", "real", FX, FY, now(FX - 150, FY + 200), "flight starts", subcat="double")
bpc = branch(FX - 300, FY, "with a flying copy? (not after a loot window)", self_get("PendingCopy", "bool", FX - 450, FY + 150))
g.link(sqr["then_2"], bpc["execute"])
g.link(bpc["then"], sfs["execute"])
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

# =====================================================================
# 2: corpse / stash loot window: after it closes, if something was taken, a reach (no copy)
#    open  = IMC_Inventory applied (backpack, corpse and stash share the W_Inventory view; traders use IMC_Trade)
#    taken = player weight text up, loot weight text down, or more money, compared with the first 0.3 s
# =====================================================================
X5, Y5 = 1200, 11000
g.box("EdGraphNode_Comment_906", X5 - 80, Y5 - 300, 7000, 4700,
      "Loot window (corpse / stash): opened? sample weights and money; closed after taking something? -> reach")
gpc = lib_pure(GS, "GameplayStatics", "GetPlayerController", X5 - 900, Y5 + 300,
               [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                ("PlayerIndex", "int", dict(extra='DefaultValue="0",')),
                ("ReturnValue", "object", dict(sub=cls("/Script/Engine.PlayerController"), out=True))])
subn = Node(g, BG + "K2Node_GetSubsystemFromPC", nm("K2Node_GetSubsystemFromPC"), X5 - 650, Y5 + 300, "", [f"CustomClass={EILPS}"])
subn.pin("PlayerController", "object", sub=cls("/Script/Engine.PlayerController"))
subn.pin("ReturnValue", "object", sub=EILPS, out=True)
g.link(gpc["ReturnValue"], subn["PlayerController"])
hmc = member_pure(EISI, "HasMappingContext", X5 - 400, Y5 + 300, subn["ReturnValue"],
                  [("MappingContext", "object", dict(sub=IMC_CLS)), ("OutFoundPriority", "int", dict(out=True)), RB])
hmc.pins["self"].cat = "interface"
hmc.pins["MappingContext"].const = True
g.link(self_get("InvIMC", "object", X5 - 600, Y5 + 420, sub=IMC_CLS), hmc["MappingContext"])
inv = b_and(X5 - 150, Y5 + 300, is_valid(X5 - 400, Y5 + 450, self_get("InvIMC", "object", X5 - 600, Y5 + 500, sub=IMC_CLS)),
            hmc["ReturnValue"])
inv_open = lambda x, y: self_get("InvOpen", "bool", x, y)
sq5 = sequence(X5, Y5, "loot window steps", 5)
g.link(sq["then_2"], sq5["execute"])

#   L0: while closed, remember what we look at (the corpse / stash the window will open for)
b50 = branch(X5 + 300, Y5 - 200, "window closed (and not opening this tick)?", b_and(X5 + 200, Y5 - 50, b_not(X5 + 50, Y5 - 50, inv_open(X5 - 100, Y5 - 50)), b_not(X5 + 50, Y5 + 50, inv)))
g.link(sq5["then_0"], b50["execute"])
slt = set_from("LootObj", "object", X5 + 600, Y5 - 200, looked_at(X5 + 100, Y5 - 100), "what we look at", sub=OBJ)
slc = set_from("LootComp", "object", X5 + 900, Y5 - 200,
               member_pure(PC, "GetInteractedComponent", X5 + 700, Y5 - 50, as_pc, [("ReturnValue", "object", dict(sub=PRIM, out=True))])["ReturnValue"],
               "the part we look at", sub=PRIM)
g.link(b50["then"], slt["execute"])
g.link(slt["then"], slc["execute"])

#   L1: opened -> classify (corpse 1, stash / container 2, else 0), find the weight texts and the view
b51 = branch(X5 + 300, Y5 + 300, "window just opened?", b_and(X5 + 150, Y5 + 450, inv, b_not(X5, Y5 + 500, inv_open(X5 - 150, Y5 + 500))))
g.link(sq5["then_1"], b51["execute"])
o1 = self_set("InvOpen", "bool", X5 + 600, Y5 + 300, "open", default="true")
o2 = set_from("OpenAt", "real", X5 + 900, Y5 + 300, now(X5 + 750, Y5 + 500), "when", subcat="double")
o3 = self_set("Took", "bool", X5 + 1200, Y5 + 300, "nothing taken yet", default="false")
o4 = self_set("LootKind", "int", X5 + 1500, Y5 + 300, "unknown", default="0")
o5 = self_set("PWText", "object", X5 + 1800, Y5 + 300, "forget old widgets", sub=WTEXT)
o6 = self_set("LWText", "object", X5 + 2100, Y5 + 300, "", sub=WTEXT)
o7 = self_set("InvView", "object", X5 + 2400, Y5 + 300, "", sub=UW)
o8 = inc("NLootOpen", X5 + 2700, Y5 + 300, "count windows")
chain(o1, o2, o3, o4, o5, o6, o7, o8)
g.link(b51["then"], o1["execute"])
lt = self_get("LootObj", "object", X5 + 2800, Y5 + 700, sub=OBJ)
cdb = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), X5 + 3000, Y5 + 300, "a corpse? (an NPC)",
                     ["TargetType=" + OBJC]))
cdb.pin("CastFailed", "exec", out=True)
cdb.pin("Object", "object", sub=OBJ)
cdb.pin("AsObj", "object", sub=OBJC, out=True)
cdb.pin("bSuccess", "bool", out=True)
g.link(lt, cdb["Object"])
g.link(o8["then"], cdb["execute"])
k1 = self_set("LootKind", "int", X5 + 3350, Y5 + 200, "corpse", default="1")
g.link(cdb["then"], k1["execute"])
cst = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), X5 + 3350, Y5 + 500, "a stash / container?",
                     [f"TargetType=\"/Script/CoreUObject.Class'{IIC}'\""]))
cst.pin("CastFailed", "exec", out=True)
cst.pin("Object", "object", sub=OBJ)
cst.pin("AsInteractable Item Container", "object", sub=cls(IIC), out=True)
cst.pin("bSuccess", "bool", out=True)
g.link(self_get("LootObj", "object", X5 + 3100, Y5 + 800, sub=OBJ), cst["Object"])
g.link(cdb["CastFailed"], cst["execute"])
k2 = self_set("LootKind", "int", X5 + 3700, Y5 + 500, "stash / container", default="2")
g.link(cst["then"], k2["execute"])
#     the weight texts: every W_Text widget once, keep the two "CurrentWeightText" of this view
gaw = lib_call(WBL, "GetAllWidgetsOfClass", X5 + 4000, Y5 + 300, "all text widgets (once per window)", [
    ("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
    ("FoundWidgets", "object", dict(sub=WTEXT, out=True)),
    ("WidgetClass", "class", dict(sub=UW, extra=f'DefaultObject="{WTEXT_PATH}",')),
    B("TopLevelOnly", "false")], "/Script/UMG.Default__WidgetBlueprintLibrary")
gaw.pins["FoundWidgets"].container = "Array"
g.link(k1["then"], gaw["execute"])
g.link(k2["then"], gaw["execute"])

fe = for_each(X5 + 4400, Y5 + 300, "each text widget", WTEXT)
g.link(gaw["then"], fe["Exec"])
g.link(gaw["FoundWidgets"], fe["Array"])
pathn = lib_pure(KSL, "KismetSystemLibrary", "GetPathName", X5 + 4600, Y5 + 700,
                 [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
g.link(fe["Array Element"], pathn["Object"])
path = pathn["ReturnValue"]


def has(x, y, sub_):
    n = lib_pure(KSTR, "KismetStringLibrary", "Contains", x, y,
                 [("SearchIn", "string"), ("Substring", "string", dict(extra=f'DefaultValue="{sub_}",')),
                  B("bUseCase"), B("bSearchFromEnd"), RB])
    g.link(path, n["SearchIn"])
    return n["ReturnValue"]


is_cw = b_and(X5 + 5000, Y5 + 800, has(X5 + 4800, Y5 + 800, "W_Inventory_C"), has(X5 + 4800, Y5 + 900, "WeightBar.WidgetTree.CurrentWeightText"))
sqe = sequence(X5 + 4800, Y5 + 300, "per text widget", 2)
g.link(fe["LoopBody"], sqe["execute"])
bpw = branch(X5 + 5100, Y5 + 200, "the player's weight?", b_and(X5 + 5000, Y5 + 1000, is_cw, has(X5 + 4800, Y5 + 1000, "InventoryWidget")))
g.link(sqe["then_0"], bpw["execute"])
g.link(bpw["then"], set_from("PWText", "object", X5 + 5400, Y5 + 200, fe["Array Element"], "player weight text", sub=WTEXT)["execute"])
blw = branch(X5 + 5100, Y5 + 500, "the corpse / stash weight?", b_and(X5 + 5000, Y5 + 1100, is_cw, has(X5 + 4800, Y5 + 1100, "LootGridWidget")))
g.link(sqe["then_1"], blw["execute"])
g.link(blw["then"], set_from("LWText", "object", X5 + 5400, Y5 + 500, fe["Array Element"], "loot weight text", sub=WTEXT)["execute"])
#     the view itself (to tell a real close from a popup)
gav = lib_call(WBL, "GetAllWidgetsOfClass", X5 + 4400, Y5 + 1400, "the inventory view", [
    ("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
    ("FoundWidgets", "object", dict(sub=WINV, out=True)),
    ("WidgetClass", "class", dict(sub=UW, extra=f'DefaultObject="{WINV_PATH}",')),
    B("TopLevelOnly", "true")], "/Script/UMG.Default__WidgetBlueprintLibrary")
gav.pins["FoundWidgets"].container = "Array"
g.link(fe["Completed"], gav["execute"])
fe2 = for_each(X5 + 4800, Y5 + 1400, "each view (one expected)", WINV)
g.link(gav["then"], fe2["Exec"])
g.link(gav["FoundWidgets"], fe2["Array"])
g.link(fe2["LoopBody"], set_from("InvView", "object", X5 + 5200, Y5 + 1400, fe2["Array Element"], "the view", sub=UW)["execute"])


def weight(x, y, var):
    t = member_pure(TEXTW, "GetText", x, y, self_get(var, "object", x - 200, y, sub=WTEXT), [("ReturnValue", "text", dict(out=True))])
    s_ = lib_pure(KTXT, "KismetTextLibrary", "Conv_TextToString", x + 200, y, [("InText", "text"), ("ReturnValue", "string", dict(out=True))])
    g.link(t["ReturnValue"], s_["InText"])
    r = lib_pure(KSTR, "KismetStringLibrary", "Replace", x + 400, y,
                 [("SourceString", "string"), ("From", "string", dict(extra='DefaultValue=",",')),
                  ("To", "string", dict(extra='DefaultValue=".",')),
                  ("SearchCase", "byte", dict(sub=EN("/Script/CoreUObject.ESearchCase"), extra='DefaultValue="IgnoreCase",')),
                  ("ReturnValue", "string", dict(out=True))])
    g.link(s_["ReturnValue"], r["SourceString"])
    d = lib_pure(KSTR, "KismetStringLibrary", "Conv_StringToDouble", x + 600, y, [("InString", "string"), RD])
    g.link(r["ReturnValue"], d["InString"])
    return d["ReturnValue"]


#   L2: open: sample (the first 0.3 s set the baseline)
b52 = branch(X5 + 300, Y5 + 1900, "window open?", b_and(X5 + 150, Y5 + 2050, inv, inv_open(X5, Y5 + 2100)))
g.link(sq5["then_2"], b52["execute"])
sg = self_set("InvGoneAt", "real", X5 + 600, Y5 + 1900, "not gone", default="-1.0", subcat="double")
g.link(b52["then"], sg["execute"])
b52k = branch(X5 + 900, Y5 + 1900, "a corpse / stash?", kml_int_gt(X5 + 750, Y5 + 2100, self_get("LootKind", "int", X5 + 550, Y5 + 2100), 0))
g.link(sg["then"], b52k["execute"])
sq52 = sequence(X5 + 1200, Y5 + 1900, "sample steps", 2)
g.link(b52k["then"], sq52["execute"])
cpw = set_from("CurPW", "real", X5 + 1500, Y5 + 1800, weight(X5 + 1300, Y5 + 2300, "PWText"), "player weight", subcat="double")
clw = set_from("CurLW", "real", X5 + 1800, Y5 + 1800, weight(X5 + 1300, Y5 + 2400, "LWText"), "loot weight", subcat="double")
cmo = set_from("CurMoney", "real", X5 + 2100, Y5 + 1800,
               member_pure(OBJC, "GetMoney", X5 + 1900, Y5 + 2300, as_pc, [("ReturnValue", "real", dict(subcat="float", out=True))])["ReturnValue"],
               "money", subcat="double")
chain(cpw, clw, cmo)
g.link(sq52["then_0"], cpw["execute"])
since_open = d_op("Subtract_DoubleDouble", X5 + 2200, Y5 + 2100, now(X5 + 2000, Y5 + 2100), self_get("OpenAt", "real", X5 + 2000, Y5 + 2200, subcat="double"))
bb = branch(X5 + 2400, Y5 + 1800, "settling (first 0.3 s)? then it is the baseline",
            d_op("Less_DoubleDouble", X5 + 2400, Y5 + 2100, since_open, b_const="0.3", ret=RB))
g.link(cmo["then"], bb["execute"])
b1_ = set_from("StartPW", "real", X5 + 2700, Y5 + 1700, self_get("CurPW", "real", X5 + 2550, Y5 + 1600, subcat="double"), "baseline", subcat="double")
b2_ = set_from("StartLW", "real", X5 + 3000, Y5 + 1700, self_get("CurLW", "real", X5 + 2850, Y5 + 1600, subcat="double"), "", subcat="double")
b3_ = set_from("StartMoney", "real", X5 + 3300, Y5 + 1700, self_get("CurMoney", "real", X5 + 3150, Y5 + 1600, subcat="double"), "", subcat="double")
chain(b1_, b2_, b3_)
g.link(bb["then"], b1_["execute"])
cur = lambda v, x, y: self_get(v, "real", x, y, subcat="double")
pw_up = b_and(X5 + 3000, Y5 + 2200, is_valid(X5 + 2800, Y5 + 2150, self_get("PWText", "object", X5 + 2600, Y5 + 2150, sub=WTEXT)),
              d_op("Greater_DoubleDouble", X5 + 2800, Y5 + 2250, cur("CurPW", X5 + 2600, Y5 + 2250),
                   d_op("Add_DoubleDouble", X5 + 2600, Y5 + 2350, cur("StartPW", X5 + 2400, Y5 + 2350), b_const="0.04"), ret=RB))
lw_dn = b_and(X5 + 3000, Y5 + 2450, is_valid(X5 + 2800, Y5 + 2400, self_get("LWText", "object", X5 + 2600, Y5 + 2400, sub=WTEXT)),
              d_op("Less_DoubleDouble", X5 + 2800, Y5 + 2500, cur("CurLW", X5 + 2600, Y5 + 2500),
                   d_op("Subtract_DoubleDouble", X5 + 2600, Y5 + 2600, cur("StartLW", X5 + 2400, Y5 + 2600), b_const="0.04"), ret=RB))
mo_up = d_op("Greater_DoubleDouble", X5 + 2800, Y5 + 2700, cur("CurMoney", X5 + 2600, Y5 + 2700),
             d_op("Add_DoubleDouble", X5 + 2600, Y5 + 2800, cur("StartMoney", X5 + 2400, Y5 + 2800), b_const="0.5"), ret=RB)
stk = set_from("Took", "bool", X5 + 2700, Y5 + 2000,
               b_or(X5 + 3200, Y5 + 2300, self_get("Took", "bool", X5 + 3000, Y5 + 2100), pw_up, lw_dn, mo_up),
               "took something? (player heavier, loot lighter or more money)")
g.link(bb["else"], stk["execute"])
bbp = branch(X5 + 1500, Y5 + 2700, "actually the backpack (I key)?",
             member_pure(PC, "IsUsingBackpack", X5 + 1300, Y5 + 2850, as_pc, [RB])["ReturnValue"])
g.link(sq52["then_1"], bbp["execute"])
g.link(bbp["then"], self_set("LootKind", "int", X5 + 1800, Y5 + 2700, "not loot", default="0")["execute"])

#   L3: gone -> after 0.25 s, and the view hidden (a popup keeps it shown; 3 s fail-safe): closed
b53 = branch(X5 + 300, Y5 + 3300, "window context gone?", b_and(X5 + 150, Y5 + 3450, b_not(X5, Y5 + 3450, inv), inv_open(X5, Y5 + 3550)))
g.link(sq5["then_3"], b53["execute"])
gone_at = lambda x, y: self_get("InvGoneAt", "real", x, y, subcat="double")
b53a = branch(X5 + 600, Y5 + 3300, "just now?", d_op("Less_DoubleDouble", X5 + 450, Y5 + 3500, gone_at(X5 + 250, Y5 + 3600), b_const="0.0", ret=RB))
g.link(b53["then"], b53a["execute"])
g.link(b53a["then"], set_from("InvGoneAt", "real", X5 + 900, Y5 + 3200, now(X5 + 750, Y5 + 3100), "gone since", subcat="double")["execute"])
gone_for = d_op("Subtract_DoubleDouble", X5 + 700, Y5 + 3700, now(X5 + 500, Y5 + 3700), gone_at(X5 + 500, Y5 + 3800))
view = lambda x, y: self_get("InvView", "object", x, y, sub=UW)
shown = b_and(X5 + 900, Y5 + 3900, is_valid(X5 + 700, Y5 + 3900, view(X5 + 500, Y5 + 3900)),
              member_pure(UW, "IsInViewport", X5 + 700, Y5 + 4000, view(X5 + 500, Y5 + 4000), [RB])["ReturnValue"],
              member_pure(cls("/Script/UMG.Widget"), "IsVisible", X5 + 700, Y5 + 4100, view(X5 + 500, Y5 + 4100), [RB])["ReturnValue"])
closed = b_and(X5 + 1100, Y5 + 3700, d_op("GreaterEqual_DoubleDouble", X5 + 900, Y5 + 3700, gone_for, b_const="0.25", ret=RB),
               b_or(X5 + 1100, Y5 + 3900, b_not(X5 + 1000, Y5 + 3900, shown),
                    d_op("GreaterEqual_DoubleDouble", X5 + 900, Y5 + 4200, gone_for, b_const="3.0", ret=RB)))
b53b = branch(X5 + 900, Y5 + 3400, "closed for good?", closed)
g.link(b53a["else"], b53b["execute"])
sc0 = self_set("InvOpen", "bool", X5 + 1200, Y5 + 3400, "closed", default="false")
g.link(b53b["then"], sc0["execute"])
b53c = branch(X5 + 1500, Y5 + 3400, "a corpse / stash, and something taken?",
              b_and(X5 + 1400, Y5 + 3600, kml_int_gt(X5 + 1200, Y5 + 3600, self_get("LootKind", "int", X5 + 1000, Y5 + 3600), 0),
                    self_get("Took", "bool", X5 + 1200, Y5 + 3700)))
sq53 = sequence(X5 + 1350, Y5 + 3600, "after closing", 2)
g.link(sc0["then"], sq53["execute"])
g.link(sq53["then_0"], b53c["execute"])
lp3 = inc("NLootTook", X5 + 2400, Y5 + 3400, "count windows something was taken from")
# v0.2: after closing, no extra grab (the hand already touched the body / stash); only count "took"
g.link(b53c["then"], lp3["execute"])
brv = branch(X5 + 1500, Y5 + 3900, "our hand is out at the corpse / stash? bring it back",
             b_and(X5 + 1400, Y5 + 4100, self_get("LootReach", "bool", X5 + 1200, Y5 + 4100),
                   is_valid(X5 + 1200, Y5 + 4200, self_get("GrabMontage", "object", X5 + 1000, Y5 + 4200, sub=MONT))))
g.link(sq53["then_1"], brv["execute"])
gm = lambda x, y: self_get("GrabMontage", "object", x, y, sub=MONT)
mres = member_call(ANIMI, "Montage_Resume", X5 + 1800, Y5 + 3900, anim, "go on", [("Montage", "object", dict(sub=MONT))])
mres.pins["Montage"].const = True
g.link(gm(X5 + 1600, Y5 + 4300), mres["Montage"])
mrate = member_call(ANIMI, "Montage_SetPlayRate", X5 + 2100, Y5 + 3900, anim, "backwards: the hand returns along its path", [
    ("Montage", "object", dict(sub=MONT)), ("NewPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",'))])
mrate.pins["Montage"].const = True
g.link(gm(X5 + 1900, Y5 + 4300), mrate["Montage"])
g.link(d_op("Multiply_DoubleDouble", X5 + 1900, Y5 + 4400, self_get("PlayRate", "real", X5 + 1700, Y5 + 4400, subcat="double"), b_const="-1.0"),
       mrate["NewPlayRate"])
rv1 = self_set("LootPaused", "bool", X5 + 2400, Y5 + 3900, "", default="false")
rv2 = self_set("LootReverse", "bool", X5 + 2700, Y5 + 3900, "returning", default="true")
chain(mres, mrate, rv1, rv2)
g.link(brv["then"], mres["execute"])
g.link(brv["else"], self_set("LootReach", "bool", X5 + 1800, Y5 + 4200, "nothing out", default="false")["execute"])


# =====================================================================
# v0.2 corpse / stash touch (tester: "the touch should happen before the window opens; when it closes the hand returns")
# The game freezes the world while the loot window is open (probe: 0 ticks/s), so the reach must play before it opens:
#   - looking at a corpse (an Obj that is not alive and has a DeadBody component) or a stash (an item container that is
#     not a loose item): our input context IMC_ImmLoot (priority 1000) maps the player's interact keys to our
#     IA_ImmLootInteract (consumes them), so the game's interact does not fire;
#   - our action pressed: the hand reaches toward the corpse / stash (PendingReach, LootReach); at the touch frame the
#     montage pauses (touch steps), our context is removed and IA_Interact is injected: the game opens the window as if
#     the key had just been pressed (a still-held key reaches the game directly, so holding to carry a body still works);
#   - window closed: the hand plays back to the start (after-closing steps) and, with a weapon, returns to the grip.
# TouchState: 0 idle, 2 reaching, 3 window requested / open.
# =====================================================================
XT, YT = 1200, 16500
g.box("EdGraphNode_Comment_907", XT - 300, YT - 400, 7200, 3400, "Corpse / stash: catch the interact key, reach out, then open the loot window")
gpc_t = lib_pure(GS, "GameplayStatics", "GetPlayerController", XT - 900, YT + 1500,
                 [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                  ("PlayerIndex", "int", dict(extra='DefaultValue="0",')),
                  ("ReturnValue", "object", dict(sub=cls("/Script/Engine.PlayerController"), out=True))])
subt = Node(g, BG + "K2Node_GetSubsystemFromPC", nm("K2Node_GetSubsystemFromPC"), XT - 650, YT + 1500, "", [f"CustomClass={EILPS}"])
subt.pin("PlayerController", "object", sub=cls("/Script/Engine.PlayerController"))
subt.pin("ReturnValue", "object", sub=EILPS, out=True)
g.link(gpc_t["ReturnValue"], subt["PlayerController"])
IA_CLS = cls("/Script/EnhancedInput.InputAction")
MCO = "\"/Script/CoreUObject.ScriptStruct'/Script/EnhancedInput.ModifyContextOptions'\""
KEY = "\"/Script/CoreUObject.ScriptStruct'/Script/InputCore.Key'\""
EAKM = "\"/Script/CoreUObject.ScriptStruct'/Script/EnhancedInput.EnhancedActionKeyMapping'\""
IAV = "\"/Script/CoreUObject.ScriptStruct'/Script/EnhancedInput.InputActionValue'\""
EIL = cls("/Script/EnhancedInput.EnhancedInputLibrary")
tstate = lambda x, y: self_get("TouchState", "int", x, y)
tadded = lambda x, y: self_get("TouchAdded", "bool", x, y)


def int_eq(x, y, a, c):
    n = kml("EqualEqual_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{c}",')), RB])
    g.link(a, n["A"])
    return n["ReturnValue"]


def ctx_call(x, y, member, comment, add):
    pins = [("MappingContext", "object", dict(sub=IMC_CLS, extra=f'DefaultObject="{IMC_TOUCH}",'))]
    if add:
        pins.append(("Priority", "int", dict(extra='DefaultValue="1000",')))
    pins.append(("Options", "struct", dict(sub=MCO)))
    n = member_call(EISI, member, x, y, subt["ReturnValue"], comment, pins)
    n.pins["self"].cat = "interface"
    n.pins["MappingContext"].const = True
    n.pins["Options"].ref = True
    n.pins["Options"].const = True
    return n


def inject_interact(x, y, comment):
    mkv = lib_pure(EIL, "EnhancedInputLibrary", "MakeInputActionValueOfType", x - 300, y + 250,
                   [D("X", "1.0"), D("Y", "0.0"), D("Z", "0.0"),
                    ("ValueType", "byte", dict(sub=EN("/Script/EnhancedInput.EInputActionValueType"), extra='DefaultValue="Boolean",')),
                    ("ReturnValue", "struct", dict(sub=IAV, out=True))])
    mkv.pins["self"].extra = 'DefaultObject="/Script/EnhancedInput.Default__EnhancedInputLibrary",'
    inj = member_call(EISI, "InjectInputForAction", x, y, subt["ReturnValue"], comment, [
        ("Action", "object", dict(sub=IA_CLS, extra=f'DefaultObject="{IA_INTERACT}",')),
        ("RawValue", "struct", dict(sub=IAV)),
        ("Modifiers", "object", dict(sub=cls("/Script/EnhancedInput.InputModifier"))),
        ("Triggers", "object", dict(sub=cls("/Script/EnhancedInput.InputTrigger")))])
    inj.pins["Action"].const = True
    inj.pins["self"].cat = "interface"
    for an in ("Modifiers", "Triggers"):
        inj.pins[an].container = "Array"
        inj.pins[an].ref = True
        inj.pins[an].const = True
    g.link(mkv["ReturnValue"], inj["RawValue"])
    return inj


sqt = sequence(XT, YT, "touch steps", 5)
g.link(sq5["then_4"], sqt["execute"])

#   T0: idle and window closed: is what we look at a corpse / stash? (re-evaluated every tick)
bt0 = branch(XT + 300, YT - 200, "idle, window closed?", b_and(XT + 150, YT, int_eq(XT, YT, tstate(XT - 200, YT), 0),
                                                              b_not(XT, YT + 100, self_get("InvOpen", "bool", XT - 200, YT + 100))))
g.link(sqt["then_0"], bt0["execute"])
lo = lambda x, y: self_get("LootObj", "object", x, y, sub=OBJ)
cob = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), XT + 600, YT - 200, "a character?", ["TargetType=" + OBJC]))
cob.pin("CastFailed", "exec", out=True)
cob.pin("Object", "object", sub=OBJ)
cob.pin("AsObj", "object", sub=OBJC, out=True)
cob.pin("bSuccess", "bool", out=True)
g.link(lo(XT + 400, YT), cob["Object"])
g.link(bt0["then"], cob["execute"])
alive = obj_q("IsAlive", XT + 800, YT + 100, cob["AsObj"])
dbc = member_pure(ACTOR, "GetComponentByClass", XT + 800, YT + 200, cob["AsObj"], [
    ("ComponentClass", "class", dict(sub=ACOMP, extra='DefaultObject="/Script/Stalker2.DeadBody",')),
    ("ReturnValue", "object", dict(sub=ACOMP, out=True))])["ReturnValue"]
corpse = b_and(XT + 1050, YT + 100, b_not(XT + 950, YT + 50, alive), is_valid(XT + 1000, YT + 200, dbc))
sl_c = set_from("Lootable", "bool", XT + 1100, YT - 300, corpse, "a corpse?")
g.link(cob["then"], sl_c["execute"])
cic = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), XT + 900, YT + 400, "an item container?",
                     [f"TargetType=\"/Script/CoreUObject.Class'{IIC}'\""]))
cic.pin("CastFailed", "exec", out=True)
cic.pin("Object", "object", sub=OBJ)
cic.pin("AsInteractable Item Container", "object", sub=cls(IIC), out=True)
cic.pin("bSuccess", "bool", out=True)
g.link(lo(XT + 700, YT + 600), cic["Object"])
g.link(cob["CastFailed"], cic["execute"])
# the instance name starts with its class name (BP_StaticItemContainer_C_...); a class pin cannot feed GetObjectName
_cn = lib_pure(KSL, "KismetSystemLibrary", "GetObjectName", XT + 1300, YT + 650, [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
g.link(cic["AsInteractable Item Container"], _cn["Object"])


def str_starts(x, y, a, lit):
    n = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "StartsWith", x, y,
                 [("SourceString", "string"), ("InPrefix", "string", dict(extra=f'DefaultValue="{lit}",')),
                  ("SearchCase", "byte", dict(sub=EN("/Script/CoreUObject.ESearchCase"), extra='DefaultValue="IgnoreCase",')), RB])
    g.link(a, n["SourceString"])
    return n["ReturnValue"]


stash = b_not(XT + 1700, YT + 700, b_or(XT + 1600, YT + 700, str_starts(XT + 1500, YT + 650, _cn["ReturnValue"], "BP_StaticItemContainer_C"),
                                        str_starts(XT + 1500, YT + 750, _cn["ReturnValue"], "BP_SkeletalItemContainer_C")))
sl_s = set_from("Lootable", "bool", XT + 1300, YT + 400, stash, "a stash (not a loose item)?")
g.link(cic["then"], sl_s["execute"])
sl_n = self_set("Lootable", "bool", XT + 1300, YT + 900, "something else", default="false")
g.link(cic["CastFailed"], sl_n["execute"])
#     add / remove our context to match
sqa = sequence(XT + 2000, YT - 200, "context steps", 2)
for n_ in (sl_c, sl_s, sl_n):
    g.link(n_["then"], sqa["execute"])
lootable = lambda x, y: self_get("Lootable", "bool", x, y)
badd = branch(XT + 2300, YT - 300, "corpse / stash in sight, our keys not on yet?", b_and(XT + 2200, YT - 100, lootable(XT + 2000, YT - 100),
                                                                                       b_not(XT + 2000, YT, tadded(XT + 1800, YT))))
g.link(sqa["then_0"], badd["execute"])
#       once per world: copy the player's interact keys (rebinds, gamepad) into our context
bks = branch(XT + 2600, YT - 300, "player's interact keys not copied yet?", b_not(XT + 2500, YT - 100, self_get("KeysSynced", "bool", XT + 2300, YT - 100)))
g.link(badd["then"], bks["execute"])
qk = member_pure(EISI, "QueryKeysMappedToAction", XT + 2600, YT + 200, subt["ReturnValue"], [
    ("Action", "object", dict(sub=IA_CLS, extra=f'DefaultObject="{IA_INTERACT}",')), ("ReturnValue", "struct", dict(sub=KEY, out=True))])
qk.pins["self"].cat = "interface"
qk.pins["Action"].const = True
qk.pins["ReturnValue"].container = "Array"
fek = Node(g, BG + "K2Node_MacroInstance", nm("K2Node_MacroInstance"), XT + 2900, YT - 300, "each interact key",
           [FOREACH, f"ResolvedWildcardType=(PinCategory=\"struct\",PinSubCategoryObject={KEY})"])
fek.pin("Exec", "exec")
fek.pin("Array", "struct", sub=KEY)
fek.pins["Array"].container = "Array"
fek.pin("LoopBody", "exec", out=True)
fek.pin("Array Element", "struct", sub=KEY, out=True)
fek.pin("Array Index", "int", out=True)
fek.pin("Completed", "exec", out=True)
g.link(qk["ReturnValue"], fek["Array"])
g.link(bks["then"], fek["Exec"])
mk = exec_pins(Node(g, BG + "K2Node_CallFunction", nm("K2Node_CallFunction"), XT + 3200, YT - 300, "map it to our action",
                    [f"FunctionReference=(MemberParent={IMC_CLS},MemberName=\"MapKey\")"]))
mk.pin("self", "object", sub=IMC_CLS, extra=f'{TGT}DefaultObject="{IMC_TOUCH}",')
mk.pin("Action", "object", sub=IA_CLS, extra=f'DefaultObject="{IA_TOUCH}",')
mk.pin("ToKey", "struct", sub=KEY)
mk.pin("ReturnValue", "struct", sub=EAKM, out=True)
mk.pins["ReturnValue"].ref = True
g.link(fek["Array Element"], mk["ToKey"])
g.link(fek["LoopBody"], mk["execute"])
kss = self_set("KeysSynced", "bool", XT + 3200, YT, "keys copied", default="true")
g.link(fek["Completed"], kss["execute"])
addc = ctx_call(XT + 3600, YT - 200, "AddMappingContext", "our keys on (they swallow the game's interact)", True)
g.link(kss["then"], addc["execute"])
g.link(bks["else"], addc["execute"])
g.link(addc["then"], self_set("TouchAdded", "bool", XT + 3950, YT - 200, "", default="true")["execute"])
brm = branch(XT + 2300, YT + 1100, "nothing lootable in sight, our keys on? take them off",
             b_and(XT + 2200, YT + 1300, b_not(XT + 2000, YT + 1300, lootable(XT + 1800, YT + 1300)), tadded(XT + 2000, YT + 1400)))
g.link(sqa["then_1"], brm["execute"])
rmc = ctx_call(XT + 2600, YT + 1100, "RemoveMappingContext", "our keys off", False)
g.link(brm["then"], rmc["execute"])
g.link(rmc["then"], self_set("TouchAdded", "bool", XT + 2950, YT + 1100, "", default="false")["execute"])

#   T1: reaching: at the touch frame (montage paused there) or after 0.8 s: give the key back and open the window
tp = lambda x, y: self_get("TouchPressAt", "real", x, y, subcat="double")
late = d_op("Greater_DoubleDouble", XT + 200, YT + 2000, d_op("Subtract_DoubleDouble", XT, YT + 2000, now(XT - 200, YT + 2000), tp(XT - 200, YT + 2100)),
            b_const="2.0", ret=RB)
held = b_and(XT + 200, YT + 2350, self_get("LootPaused", "bool", XT, YT + 2300),
             d_op("GreaterEqual_DoubleDouble", XT + 200, YT + 2450,
                  d_op("Subtract_DoubleDouble", XT, YT + 2450, now(XT - 200, YT + 2450), self_get("PausedAt", "real", XT - 200, YT + 2550, subcat="double")),
                  self_get("TouchHoldBeforeOpen", "real", XT, YT + 2600, subcat="double"), ret=RB))
bt1 = branch(XT + 400, YT + 1800, "reached (or 0.8 s)? open the window now",
             b_and(XT + 300, YT + 2100, int_eq(XT + 100, YT + 2200, tstate(XT - 100, YT + 2200), 2),
                   b_or(XT + 300, YT + 2300, held, late)))
g.link(sqt["then_1"], bt1["execute"])
rmc2 = ctx_call(XT + 700, YT + 1800, "RemoveMappingContext", "our keys off", False)
ta2 = self_set("TouchAdded", "bool", XT + 1050, YT + 1800, "", default="false")
inj = inject_interact(XT + 1400, YT + 1800, "press the game's interact: opens the loot window")
ts3 = self_set("TouchState", "int", XT + 1750, YT + 1800, "window requested", default="3")
toa = set_from("TouchOpenAt", "real", XT + 2050, YT + 1800, now(XT + 1900, YT + 2000), "", subcat="double")
nto = inc("NTouch", XT + 2350, YT + 1800, "count touches")
chain(rmc2, ta2, inj, ts3, toa, nto)
g.link(bt1["then"], rmc2["execute"])

#   T2: window requested but never opened (e.g. the game started carrying the body): bring the hand back anyway
bt2 = branch(XT + 400, YT + 2700, "no window 1 s after the press? hand back",
             b_and(XT + 300, YT + 2900, int_eq(XT + 100, YT + 3000, tstate(XT - 100, YT + 3000), 3),
                   b_not(XT + 100, YT + 3100, self_get("InvOpen", "bool", XT - 100, YT + 3100)),
                   d_op("Greater_DoubleDouble", XT + 200, YT + 3200,
                        d_op("Subtract_DoubleDouble", XT, YT + 3200, now(XT - 200, YT + 3200),
                             self_get("TouchOpenAt", "real", XT - 200, YT + 3300, subcat="double")), b_const="1.0", ret=RB)))
g.link(sqt["then_2"], bt2["execute"])
bt2b = branch(XT + 700, YT + 2700, "our montage still out?", b_and(XT + 650, YT + 2900, self_get("LootReach", "bool", XT + 450, YT + 2900),
                                                                    is_valid(XT + 450, YT + 3000, self_get("GrabMontage", "object", XT + 250, YT + 3000, sub=MONT))))
g.link(bt2["then"], bt2b["execute"])
gm2 = lambda x, y: self_get("GrabMontage", "object", x, y, sub=MONT)
mres2 = member_call(ANIMI, "Montage_Resume", XT + 1000, YT + 2700, anim, "go on", [("Montage", "object", dict(sub=MONT))])
mres2.pins["Montage"].const = True
g.link(gm2(XT + 800, YT + 3000), mres2["Montage"])
mrate2 = member_call(ANIMI, "Montage_SetPlayRate", XT + 1300, YT + 2700, anim, "backwards", [
    ("Montage", "object", dict(sub=MONT)), ("NewPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",'))])
mrate2.pins["Montage"].const = True
g.link(gm2(XT + 1100, YT + 3000), mrate2["Montage"])
g.link(d_op("Multiply_DoubleDouble", XT + 1100, YT + 3100, self_get("PlayRate", "real", XT + 900, YT + 3100, subcat="double"), b_const="-1.0"),
       mrate2["NewPlayRate"])
rv1b = self_set("LootPaused", "bool", XT + 1600, YT + 2700, "", default="false")
rv2b = self_set("LootReverse", "bool", XT + 1900, YT + 2700, "returning", default="true")
ts4 = self_set("TouchState", "int", XT + 2200, YT + 2700, "", default="0")
chain(mres2, mrate2, rv1b, rv2b, ts4)
g.link(bt2b["then"], mres2["execute"])
g.link(bt2b["else"], ts4["execute"])

#   our interact action pressed (only arrives while our context is on = looking at a corpse / stash)
ev = Node(g, "/Script/InputBlueprintNodes.K2Node_EnhancedInputAction", nm("K2Node_EnhancedInputAction"), XT - 200, YT + 3700, "",
          [f"InputAction=\"/Script/EnhancedInput.InputAction'{IA_TOUCH}'\""])
for e in ("Triggered", "Started", "Ongoing", "Canceled", "Completed"):
    ev.pin(e, "exec", out=True)
ev.pin("ActionValue", "bool", out=True)
ev.pin("ElapsedSeconds", "real", subcat="double", out=True, adv=True)
ev.pin("TriggeredSeconds", "real", subcat="double", out=True, adv=True)
ev.pin("InputAction", "object", sub=IA_CLS, out=True)
lcomp = lambda x, y: self_get("LootComp", "object", x, y, sub=PRIM)
bpress = branch(XT + 200, YT + 3700, "idle and the corpse / stash part known? reach for it",
                b_and(XT + 100, YT + 3900, int_eq(XT - 100, YT + 3900, tstate(XT - 300, YT + 3900), 0), is_valid(XT - 100, YT + 4000, lcomp(XT - 300, YT + 4000))))
g.link(ev["Started"], bpress["execute"])
_tgb = lib_pure(KSL, "KismetSystemLibrary", "GetComponentBounds", XT + 300, YT + 4200,
                [("Component", "object", dict(sub=SC_)), ("Origin", "struct", dict(sub=VEC, out=True)),
                 ("BoxExtent", "struct", dict(sub=VEC, out=True)), ("SphereRadius", "real", dict(subcat="float", out=True))])
_tgb.pins["Component"].const = True
g.link(lcomp(XT + 100, YT + 4200), _tgb["Component"])
tr = [set_from("ItemCenter", "struct", XT + 500, YT + 3700, _tgb["Origin"], "reach target = its centre", sub=VEC),
      self_set("PendingReach", "bool", XT + 800, YT + 3700, "reach", default="true"),
      self_set("PendingCopy", "bool", XT + 1100, YT + 3700, "no copy", default="false"),
      self_set("LootReach", "bool", XT + 1400, YT + 3700, "touch: hold at the touch frame", default="true"),
      self_set("LootPaused", "bool", XT + 1700, YT + 3700, "", default="false"),
      self_set("LootReverse", "bool", XT + 2000, YT + 3700, "", default="false"),
      set_from("TouchPressAt", "real", XT + 2300, YT + 3700, now(XT + 2150, YT + 3900), "pressed", subcat="double"),
      self_set("TouchState", "int", XT + 2600, YT + 3700, "reaching", default="2")]
chain(*tr)
g.link(bpress["then"], tr[0]["execute"])

#     not idle or nothing to reach for: just pass the press on to the game
rmc3 = ctx_call(XT + 500, YT + 4500, "RemoveMappingContext", "our keys off", False)
ta3 = self_set("TouchAdded", "bool", XT + 850, YT + 4500, "", default="false")
inj3 = inject_interact(XT + 1200, YT + 4500, "pass the press on")
chain(rmc3, ta3, inj3)
bpass = branch(XT + 250, YT + 4400, "idle? (else ignore: a touch is running)", int_eq(XT + 100, YT + 4600, tstate(XT - 100, YT + 4600), 0))
g.link(bpress["else"], bpass["execute"])
g.link(bpass["then"], rmc3["execute"])

#   T3: the grip report after the "hand back on the item" animation (armed)
bgp = branch(XT + 4400, YT + 1800, "report: left hand back on the weapon",
             b_and(XT + 4300, YT + 2000, self_get("GripPending", "bool", XT + 4100, YT + 2000),
                   d_op("GreaterEqual_DoubleDouble", XT + 4100, YT + 2100, now(XT + 3900, YT + 2100),
                        self_get("GripAt", "real", XT + 3900, YT + 2200, subcat="double"), ret=RB)))
g.link(sqt["then_3"], bgp["execute"])
rgp = member_call(PC, "ReturnLeftHandOnItemEnded", XT + 4700, YT + 1800, as_pc, "left hand on the weapon (game state)")
g.link(bgp["then"], rgp["execute"])
g.link(rgp["then"], self_set("GripPending", "bool", XT + 5050, YT + 1800, "", default="false")["execute"])
#   T4: probe: left hand busy (game), left-hand slot active, our montage position in the segment
_pp = member_pure(ANIMI, "Montage_GetPosition", XT + 4100, YT + 2700, anim, [("Montage", "object", dict(sub=MONT)), ("ReturnValue", "real", dict(subcat="float", out=True))])
_pp.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", XT + 3900, YT + 2700, sub=MONT), _pp["Montage"])
tpr = [set_from("TrBusy", "bool", XT + 4400, YT + 2500, obj_q("IsLeftHandBusy", XT + 4200, YT + 2600, as_pc), "probe"),
       set_from("TrLH", "bool", XT + 4700, YT + 2500, slot_active(XT + 4500, YT + 2600, anim, "LeftHand"), ""),
       set_from("TrPos", "real", XT + 5000, YT + 2500, d_op("Subtract_DoubleDouble", XT + 4800, YT + 2700, _pp["ReturnValue"],
                                                              self_get("SegStart", "real", XT + 4600, YT + 2800, subcat="double")), "", subcat="double")]
_cm4 = lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", XT + 3600, YT + 3100,
                [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                 ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"]
_cl4 = member_pure(PCM, "GetCameraLocation", XT + 3800, YT + 3100, _cm4, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_cr4 = member_pure(PCM, "GetCameraRotation", XT + 3800, YT + 3200, _cm4, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_hb4 = member_pure(SKC, "GetSocketLocation", XT + 3800, YT + 3300, mesh,
                   [("InSocketName", "name", dict(extra=f'DefaultValue="{HAND}",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_hr4 = vop("Subtract_VectorVector", XT + 4000, YT + 3300, _hb4, _cl4)
for k, (var, fn) in enumerate((("TouchHX", "GetForwardVector"), ("TouchHY", "GetRightVector"), ("TouchHZ", "GetUpVector"))):
    ax = kml(fn, XT + 4000, YT + 3400 + 100 * k, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_cr4, ax["InRot"])
    tpr.append(set_from(var, "real", XT + 5300 + 300 * k, YT + 2500, vop("Dot_VectorVector", XT + 4200, YT + 3400 + 100 * k, _hr4, ax["ReturnValue"], ret_sub="real"),
                        "hand in view axes (probe)" if k == 0 else "", subcat="double"))
chain(*tpr)
g.link(sqt["then_4"], tpr[0]["execute"])


# ---- 4: track the loose item under the crosshair ----
X2, Y2 = 1200, 4000
g.box("EdGraphNode_Comment_903", X2 - 80, Y2 - 200, 3600, 1300, "Track the loose item we are looking at (its mesh and where it is)")
tgt = looked_at(X2 - 800, Y2 + 200)
bt = branch(X2, Y2, "looking at something interactable?", is_valid(X2 - 150, Y2 + 200, tgt))
g.link(sq["then_4"], bt["execute"])
own = tgt
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
_gb = lib_pure(KSL, "KismetSystemLibrary", "GetComponentBounds", X2 + 1600, Y2 + 1000,
               [("Component", "object", dict(sub=SC_)), ("Origin", "struct", dict(sub=VEC, out=True)),
                ("BoxExtent", "struct", dict(sub=VEC, out=True)), ("SphereRadius", "real", dict(subcat="float", out=True))])
_gb.pins["Component"].const = True
g.link(icomp(X2 + 1400, Y2 + 1000), _gb["Component"])
sctr = set_from("ItemCenter", "struct", X2 + 1850, Y2 + 600, _gb["Origin"], "its centre", sub=VEC)
chain(sseen, sarm, sxf, sctr)

# ---- 5: the copy waits where the item was; the hand takes it at the grab frame and carries it to the pocket ----
# build 9 (tester: "it should look like the hand grabs the item and takes it, not the item floating into the hand"):
# - until the grab frame (GrabTime) the copy stays where the item lay;
# - then, in 0.12 s, it is pulled into the hand at its real size (the hand is at the crosshair, the item behind it on
#   the same line, so it reads as snatched) and PARENTED to the left-hand item bone jnt_l_weapon (tester, build 9: "make
#   it actually get parented to the hand"; build 9's depth-ratio shrink would have put a doll-sized bottle in the hand);
# - it rides with the hand to the pocket and is removed at PocketTime.
# Where the hand is seen: the arm bones are where they are drawn, except the arms' materials spread the sideways part
# (relative to the camera) by s = tan(view FOV/2) / MPC_FOV.TanFOV (MF_Foreground_FOVCorrection; depth scaling keeps
# the screen position). Builds 5-8 assumed the arms follow the view pitch; they do not (build 7 trace, empty hands).
X3, Y3 = 1200, 5800
g.box("EdGraphNode_Comment_904", X3 - 1600, Y3 - 500, 5200, 2400, "The hand takes the copy at the grab frame and carries it to the pocket")
fly = lambda x, y: self_get("Fly", "object", x, y, sub=ACTOR)
bf = branch(X3, Y3, "a copy is out?", is_valid(X3 - 150, Y3 + 200, fly(X3 - 350, Y3 + 200)))
g.link(sq["then_5"], bf["execute"])
el = d_op("Subtract_DoubleDouble", X3 - 300, Y3 + 500, now(X3 - 500, Y3 + 500), self_get("FlyStart", "real", X3 - 500, Y3 + 580, subcat="double"))
#   u: 0 before the grab frame, 0 -> 1 over 0.12 s after it
grab_at = d_op("Add_DoubleDouble", X3 - 300, Y3 + 650, self_get("ReachStart", "real", X3 - 500, Y3 + 650, subcat="double"),
               d_op("Divide_DoubleDouble", X3 - 500, Y3 + 720, self_get("GrabTime", "real", X3 - 700, Y3 + 720, subcat="double"),
                    self_get("PlayRate", "real", X3 - 700, Y3 + 800, subcat="double")))
since_grab = d_op("Subtract_DoubleDouble", X3 - 100, Y3 + 650, now(X3 - 300, Y3 + 750), grab_at)
cl = kml("FClamp", X3 + 100, Y3 + 650, [D("Value"), D("Min", "0.0"), D("Max", "1.0"), RD])
g.link(d_op("Divide_DoubleDouble", X3 - 100, Y3 + 750, since_grab, b_const="0.12"), cl["Value"])
alpha = cl["ReturnValue"]
bone = member_pure(SKC, "GetSocketLocation", X3 - 900, Y3 + 900, mesh,
                   [("InSocketName", "name", dict(extra=f'DefaultValue="{HAND}",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
cl_, cf_, cr_, cu_, cfov = cam_basis(X3 - 1500, Y3 + 1100)
tan_v = kml("DegTan", X3 - 700, Y3 + 1300, [D("A"), RD])
g.link(d_op("Multiply_DoubleDouble", X3 - 900, Y3 + 1300, cfov, b_const="0.5"), tan_v["A"])
tan_f = self_get("TanFOVv", "real", X3 - 900, Y3 + 1400, subcat="double")
fov_on = self_get("FovOn", "real", X3 - 900, Y3 + 1500, subcat="double")
lerp_s = kml("Lerp", X3 - 300, Y3 + 1350, [D("A", "1.0"), D("B"), D("Alpha"), RD])
g.link(d_op("Divide_DoubleDouble", X3 - 500, Y3 + 1350, tan_v["ReturnValue"], tan_f), lerp_s["B"])
g.link(fov_on, lerp_s["Alpha"])
s_eff = lerp_s["ReturnValue"]
rel = vop("Subtract_VectorVector", X3 - 600, Y3 + 900, bone, cl_)
axial = vop("Multiply_VectorFloat", X3 - 200, Y3 + 950, cf_, vop("Dot_VectorVector", X3 - 400, Y3 + 1000, cf_, rel, ret_sub="real"),
            b_cat="real", b_sub="None", b_subcat="double")
side = vop("Multiply_VectorFloat", X3, Y3 + 1050, vop("Subtract_VectorVector", X3 - 200, Y3 + 1050, rel, axial), s_eff,
           b_cat="real", b_sub="None", b_subcat="double")
hand = vop("Add_VectorVector", X3 + 250, Y3 + 950, cl_, vop("Add_VectorVector", X3 + 100, Y3 + 1000, axial, side))
#   the copy: from where the item lay to the hand as seen, scaled by the depth ratio (same size on screen)
ffrom = lambda x, y: self_get("FlyFrom", "struct", x, y, sub=VEC)
ve = kml("VLerp", X3 + 650, Y3 + 300, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)),
                                       ("Alpha", "real", dict(subcat="float", extra='DefaultValue="0.0",')),
                                       ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(ffrom(X3 + 450, Y3 + 300), ve["A"])
g.link(bone, ve["B"])
g.link(alpha, ve["Alpha"])
pos = ve["ReturnValue"]


sq3 = sequence(X3 + 300, Y3, "copy steps", 3)
m1 = mpc_scalar_call(X3 - 600, Y3 - 400, "TanFOV", "arms' FOV (MPC_FOV)")
m1s = set_from("TanFOVv", "real", X3 - 300, Y3 - 400, m1["ReturnValue"], "", subcat="double")
m2 = mpc_scalar_call(X3, Y3 - 400, "IsFOVEnabled", "")
m2s = set_from("FovOn", "real", X3 + 300, Y3 - 400, m2["ReturnValue"], "", subcat="double")
chain(m1, m1s, m2, m2s)
g.link(bf["then"], m1["execute"])
g.link(m2s["then"], sq3["execute"])
attached = lambda x, y: self_get("FlyAttached", "bool", x, y)
bna = branch(X3 + 650, Y3 - 100, "not in the hand yet?", b_not(X3 + 500, Y3 + 50, attached(X3 + 300, Y3 + 50)))
g.link(sq3["then_0"], bna["execute"])
sl = member_call(ACTOR, "K2_SetActorLocation", X3 + 950, Y3 - 100, fly(X3 + 800, Y3 + 100), "where the item lay, then pulled to the hand", [
    ("NewLocation", "struct", dict(sub=VEC)), B("bSweep"),
    ("SweepHitResult", "struct", dict(sub=HIT, out=True)), B("bTeleport", "true"), RB])
g.link(pos, sl["NewLocation"])
g.link(bna["then"], sl["execute"])
#   probe: the hand bone relative to the camera (camera axes) every tick
hrel_b = vop("Subtract_VectorVector", X3 + 1300, Y3 + 700, bone, cl_)
trs = [set_from(v, "real", X3 + 1550 + 300 * k, Y3 - 100, vop("Dot_VectorVector", X3 + 1500, Y3 + 800 + 100 * k, hrel_b, axis, ret_sub="real"),
                "hand bone in camera axes (probe)" if k == 0 else "", subcat="double")
       for k, (v, axis) in enumerate((("TraceX", cf_), ("TraceY", cr_), ("TraceZ", cu_)))]
wpn_b = member_pure(SKC, "GetSocketLocation", X3 + 1300, Y3 + 1500, mesh,
                    [("InSocketName", "name", dict(extra='DefaultValue="jnt_weapon",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
wrel = vop("Subtract_VectorVector", X3 + 1500, Y3 + 1500, wpn_b, cl_)
trw = [set_from(v, "real", X3 + 2450 + 300 * k, Y3 - 100, vop("Dot_VectorVector", X3 + 1700, Y3 + 1500 + 100 * k, wrel, axis, ret_sub="real"),
                "grip point (jnt_weapon) in camera axes (probe)" if k == 0 else "", subcat="double")
       for k, (v, axis) in enumerate((("WeapX", cf_), ("WeapY", cr_), ("WeapZ", cu_)))]
_cbr = kml("BreakRotator", X3 + 1300, Y3 + 1800, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                 ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(member_pure(PCM, "GetCameraRotation", X3 + 1100, Y3 + 1800,
                   lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", X3 + 900, Y3 + 1800,
                            [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)), ("PlayerIndex", "int", dict(extra='DefaultValue="0",')),
                             ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"],
                   [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"], _cbr["InRot"])
scp = set_from("CamPitch", "real", X3 + 3350, Y3 - 100, _cbr["Pitch"], "view pitch (probe)", subcat="double")
chain(sl, *trs, *trw, scp)
#   at the hand: parent it to the hand's item bone (keeps its size and its rotation at that moment)
bat = branch(X3 + 1300, Y3 + 250, "reached the hand, not parented yet?",
             b_and(X3 + 1150, Y3 + 450, d_op("GreaterEqual_DoubleDouble", X3 + 950, Y3 + 450, alpha, b_const="1.0", ret=RB),
                   b_not(X3 + 950, Y3 + 550, attached(X3 + 750, Y3 + 550))))
g.link(sq3["then_1"], bat["execute"])
RULE = EN("/Script/Engine.EAttachmentRule")
att = member_call(ACTOR, "K2_AttachToComponent", X3 + 1600, Y3 + 250, fly(X3 + 1450, Y3 + 450), "parent to the left hand", [
    ("Parent", "object", dict(sub=SC_)), ("SocketName", "name", dict(extra=f'DefaultValue="{HAND}",')),
    ("LocationRule", "byte", dict(sub=RULE, extra='DefaultValue="SnapToTarget",')),
    ("RotationRule", "byte", dict(sub=RULE, extra='DefaultValue="KeepWorld",')),
    ("ScaleRule", "byte", dict(sub=RULE, extra='DefaultValue="KeepWorld",')),
    B("bWeldSimulatedBodies"), RB])
g.link(mesh, att["Parent"])
g.link(bat["then"], att["execute"])
hrel = vop("Subtract_VectorVector", X3 + 1300, Y3 + 1100, hand, cl_)
pr = []
for k, (var, axis) in enumerate((("GrabFwd", cf_), ("GrabRight", cr_), ("GrabUp", cu_))):
    pr.append(set_from(var, "real", X3 + 1900 + 300 * k, Y3 + 250, vop("Dot_VectorVector", X3 + 1500, Y3 + 1200 + 100 * k, hrel, axis, ret_sub="real"),
                       "hand as seen, camera axes" if k == 0 else "", subcat="double"))
pr.append(set_from("FovS", "real", X3 + 2800, Y3 + 250, s_eff, "squeeze", subcat="double"))
# build 15 probe: where the arm's joints really are at the hand-over (camera axes), to find which joint differs from
# the model in make_grab_seq
for j, (bn, pre) in enumerate((("jnt_spine_03", "Sp"), ("jnt_l_arm", "Sh"), ("jnt_l_fore_arm", "El"))):
    jl = member_pure(SKC, "GetSocketLocation", X3 + 1300, Y3 + 2000 + 300 * j, mesh,
                     [("InSocketName", "name", dict(extra=f'DefaultValue="{bn}",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
    jr = vop("Subtract_VectorVector", X3 + 1500, Y3 + 2000 + 300 * j, jl, cl_)
    for k, (ax, axis) in enumerate((("X", cf_), ("Y", cr_), ("Z", cu_))):
        pr.append(set_from(pre + ax, "real", X3 + 3100 + 300 * len(pr), Y3 + 250,
                           vop("Dot_VectorVector", X3 + 1700, Y3 + 2000 + 300 * j + 100 * k, jr, axis, ret_sub="real"),
                           f"{bn} (probe)" if k == 0 else "", subcat="double"))
pr.append(self_set("FlyAttached", "bool", X3 + 3100, Y3 + 250, "", default="true"))
chain(att, *pr)
pocket = d_op("GreaterEqual_DoubleDouble", X3 + 700, Y3 + 850, montage_time_since_reach(X3 + 500, Y3 + 850),
              self_get("PocketTime", "real", X3 + 500, Y3 + 1000, subcat="double"), ret=RB)
stale = d_op("Greater_DoubleDouble", X3 + 700, Y3 + 1050, el, b_const="3.0", ret=RB)
bp = branch(X3 + 1250, Y3 + 600, "pocketed? (or stuck for 3 s)", b_or(X3 + 1050, Y3 + 900, pocket, stale))
g.link(sq3["then_2"], bp["execute"])
fdx = member_call(ACTOR, "K2_DestroyActor", X3 + 1550, Y3 + 600, fly(X3 + 1400, Y3 + 800), "gone into the pocket")
g.link(bp["then"], fdx["execute"])

# ---- 6: recover the left hand if our montage was cut ----
X4, Y4 = 1200, 7600
g.box("EdGraphNode_Comment_905", X4 - 80, Y4 - 200, 2600, 1100, "Reach cut short? Put the left hand back on the weapon")
br4 = branch(X4, Y4, "our reach ended?", b_and(X4 - 100, Y4 + 250, self_get("Reaching", "bool", X4 - 300, Y4 + 200),
                                                b_not(X4 - 300, Y4 + 300, grab_active(X4 - 500, Y4 + 300))))
sq6 = sequence(X4 - 400, Y4 - 400, "end steps", 3)
g.link(sq["then_6"], sq6["execute"])
g.link(sq6["then_1"], br4["execute"])
_pos = member_pure(ANIMI, "Montage_GetPosition", X4 - 300, Y4 - 600, anim, [("Montage", "object", dict(sub=MONT)), ("ReturnValue", "real", dict(subcat="float", out=True))])
_pos.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 - 500, Y4 - 600, sub=MONT), _pos["Montage"])
seg_done = d_op("GreaterEqual_DoubleDouble", X4 - 100, Y4 - 600, _pos["ReturnValue"],
                d_op("Add_DoubleDouble", X4 - 300, Y4 - 500, self_get("SegStart", "real", X4 - 500, Y4 - 500, subcat="double"), b_const="1.35"), ret=RB)
bstop = branch(X4, Y4 - 700, "empty-hands segment over? stop the table there",
               b_and(X4 - 100, Y4 - 800, self_get("GrabBH", "bool", X4 - 300, Y4 - 850), grab_active(X4 - 300, Y4 - 950), seg_done,
                     b_not(X4 - 300, Y4 - 1050, self_get("LootReach", "bool", X4 - 500, Y4 - 1050))))
g.link(sq6["then_0"], bstop["execute"])
mst = member_call(ANIMI, "Montage_Stop", X4 + 300, Y4 - 700, anim, "blend out", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.300000",')), ("Montage", "object", dict(sub=MONT))])
mst.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 100, Y4 - 550, sub=MONT), mst["Montage"])
g.link(bstop["then"], mst["execute"])
# v0.2: corpse / stash touch: pause at the touch frame (0.5 s montage time) while the window is open; when the hand,
# playing backwards after the window closed, is back at the segment start, stop the montage
sqh = sequence(X4 + 700, Y4 - 1400, "touch steps", 2)
g.link(sq6["then_2"], sqh["execute"])
_pos2 = member_pure(ANIMI, "Montage_GetPosition", X4 + 500, Y4 - 1700, anim, [("Montage", "object", dict(sub=MONT)), ("ReturnValue", "real", dict(subcat="float", out=True))])
_pos2.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 300, Y4 - 1700, sub=MONT), _pos2["Montage"])
seg0 = lambda x, y: self_get("SegStart", "real", x, y, subcat="double")
at_touch = d_op("GreaterEqual_DoubleDouble", X4 + 900, Y4 - 1700, _pos2["ReturnValue"],
                d_op("Add_DoubleDouble", X4 + 700, Y4 - 1600, seg0(X4 + 500, Y4 - 1600), b_const="0.6"), ret=RB)
bhold = branch(X4 + 1100, Y4 - 1500, "touching the corpse / stash? hold there",
               b_and(X4 + 1000, Y4 - 1300, self_get("LootReach", "bool", X4 + 800, Y4 - 1300),
                     b_not(X4 + 800, Y4 - 1200, self_get("LootPaused", "bool", X4 + 600, Y4 - 1200)),
                     b_not(X4 + 800, Y4 - 1100, self_get("LootReverse", "bool", X4 + 600, Y4 - 1100)),
                     grab_active(X4 + 600, Y4 - 1000), at_touch))
g.link(sqh["then_0"], bhold["execute"])
mpa = member_call(ANIMI, "Montage_Pause", X4 + 1400, Y4 - 1500, anim, "hold", [("Montage", "object", dict(sub=MONT))])
mpa.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 1200, Y4 - 1350, sub=MONT), mpa["Montage"])
g.link(bhold["then"], mpa["execute"])
_lp = self_set("LootPaused", "bool", X4 + 1700, Y4 - 1500, "", default="true")
g.link(mpa["then"], _lp["execute"])
g.link(_lp["then"], set_from("PausedAt", "real", X4 + 2000, Y4 - 1500, now(X4 + 1850, Y4 - 1300), "hand out since", subcat="double")["execute"])
back = d_op("LessEqual_DoubleDouble", X4 + 900, Y4 - 800, _pos2["ReturnValue"],
            d_op("Add_DoubleDouble", X4 + 700, Y4 - 700, seg0(X4 + 500, Y4 - 700), b_const="0.0"), ret=RB)
bback = branch(X4 + 1100, Y4 - 900, "hand back? (or our montage gone)",
               b_and(X4 + 1000, Y4 - 750, self_get("LootReverse", "bool", X4 + 800, Y4 - 750),
                     b_or(X4 + 1000, Y4 - 650, back, b_not(X4 + 800, Y4 - 600, grab_active(X4 + 600, Y4 - 600)))))
g.link(sqh["then_1"], bback["execute"])
mst2 = member_call(ANIMI, "Montage_Stop", X4 + 1400, Y4 - 900, anim, "done", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.200000",')), ("Montage", "object", dict(sub=MONT))])
mst2.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 1200, Y4 - 750, sub=MONT), mst2["Montage"])
bk1 = self_set("LootReverse", "bool", X4 + 1700, Y4 - 900, "", default="false")
bk2 = self_set("LootReach", "bool", X4 + 2000, Y4 - 900, "", default="false")
bk3 = self_set("TouchState", "int", X4 + 2300, Y4 - 900, "idle", default="0")
chain(mst2, bk1, bk2, bk3)
# (the extra "hand back on the item" animation is no longer played: the touch itself ends on the grip)

bmst = branch(X4 + 1250, Y4 - 1000, "still ours to stop?", grab_active(X4 + 1050, Y4 - 1050))
g.link(bback["then"], bmst["execute"])
g.link(bmst["then"], mst2["execute"])
g.link(bmst["else"], bk1["execute"])
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

g.layout()
write(sys.argv[1], g.text())
print("ok", len(g.nodes), "nodes")
