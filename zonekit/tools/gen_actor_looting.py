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
mp = member_call(ANIMI, "PlaySlotAnimationAsDynamicMontage", X1 + 2450, Y1 + 250, anim, "left-hand grab, hand raised (LeftHand slot)", [
    ("Asset", "object", dict(sub=ANIMSEQB, extra=f'DefaultObject="{GRAB_SEQ}",')),
    ("SlotNodeName", "name", dict(extra='DefaultValue="LeftHand",')),
    ("BlendInTime", "real", dict(subcat="float", extra='DefaultValue="0.200000",')),
    ("BlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.700000",')),
    ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",')),
    ("LoopCount", "int", dict(extra='DefaultValue="1",')),
    ("BlendOutTriggerTime", "real", dict(subcat="float", extra='DefaultValue="-1.000000",')),
    ("InTimeToStartMontageAt", "real", dict(subcat="float", extra='DefaultValue="0.000000",')),
    ("ReturnValue", "object", dict(sub=MONT, out=True))])
g.link(self_get("PlayRate", "real", X1 + 2250, Y1 + 450, subcat="double"), mp["InPlayRate"])
g.link(bm["else"], mp["execute"])
sgm = set_from("GrabMontage", "object", X1 + 2450, Y1 + 600, mp["ReturnValue"], "our montage", sub=MONT)
srs = set_from("ReachStart", "real", X1 + 2800, Y1 + 250, now(X1 + 2650, Y1 + 450), "reach started", subcat="double")
srg = self_set("Reaching", "bool", X1 + 3100, Y1 + 250, "", default="true")
nr = inc("NReaches", X1 + 3400, Y1 + 250, "count reaches")
chain(mp, sgm, srs, srg, nr)
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
sq5 = sequence(X5, Y5, "loot window steps", 4)
g.link(sq["then_2"], sq5["execute"])

#   L0: while closed, remember what we look at (the corpse / stash the window will open for)
b50 = branch(X5 + 300, Y5 - 200, "window closed (and not opening this tick)?", b_and(X5 + 200, Y5 - 50, b_not(X5 + 50, Y5 - 50, inv_open(X5 - 100, Y5 - 50)), b_not(X5 + 50, Y5 + 50, inv)))
g.link(sq5["then_0"], b50["execute"])
slt = set_from("LootObj", "object", X5 + 600, Y5 - 200, looked_at(X5 + 100, Y5 - 100), "what we look at", sub=OBJ)
g.link(b50["then"], slt["execute"])

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
g.link(sc0["then"], b53c["execute"])
lp1 = self_set("PendingReach", "bool", X5 + 1800, Y5 + 3400, "reach pending", default="true")
lp2 = self_set("PendingCopy", "bool", X5 + 2100, Y5 + 3400, "no copy (nothing in the world)", default="false")
lp3 = inc("NLootTook", X5 + 2400, Y5 + 3400, "count loot reaches")
chain(lp1, lp2, lp3)
g.link(b53c["then"], lp1["execute"])

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
chain(sseen, sarm, sxf)

# ---- 5: fly the copy into the left hand ----
X3, Y3 = 1200, 5800
g.box("EdGraphNode_Comment_904", X3 - 1600, Y3 - 200, 5000, 2000, "Fly the copy to the left hand as seen (first-person FOV squeeze), hold it, pocket it")
fly = lambda x, y: self_get("Fly", "object", x, y, sub=ACTOR)
bf = branch(X3, Y3, "a copy is flying?", is_valid(X3 - 150, Y3 + 200, fly(X3 - 350, Y3 + 200)))
g.link(sq["then_5"], bf["execute"])
el = d_op("Subtract_DoubleDouble", X3 - 300, Y3 + 500, now(X3 - 500, Y3 + 500), self_get("FlyStart", "real", X3 - 500, Y3 + 580, subcat="double"))
alpha_raw = d_op("Divide_DoubleDouble", X3 - 100, Y3 + 500, el, self_get("FlyDur", "real", X3 - 300, Y3 + 620, subcat="double"))
cl = kml("FClamp", X3 + 100, Y3 + 500, [D("Value"), D("Min", "0.0"), D("Max", "1.0"), RD])
g.link(alpha_raw, cl["Value"])
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
m1 = mpc_scalar_call(X3 - 600, Y3 - 400, "TanFOV", "arms' FOV (MPC_FOV)")
m1s = set_from("TanFOVv", "real", X3 - 300, Y3 - 400, m1["ReturnValue"], "", subcat="double")
m2 = mpc_scalar_call(X3, Y3 - 400, "IsFOVEnabled", "")
m2s = set_from("FovOn", "real", X3 + 300, Y3 - 400, m2["ReturnValue"], "", subcat="double")
chain(m1, m1s, m2, m2s)
g.link(bf["then"], m1["execute"])
sq3 = sequence(X3 + 300, Y3, "fly steps", 3)
g.link(m2s["then"], sq3["execute"])
ba = branch(X3 + 600, Y3 - 100, "still on the way?", d_op("Less_DoubleDouble", X3 + 400, Y3 + 150, alpha, b_const="1.0", ret=RB))
g.link(sq3["then_0"], ba["execute"])
# ease-in (alpha^2) by hand: KismetMathLibrary's Ease / VEase are BlueprintInternalUseOnly (only the K2Node_EaseFunction
# node may call them; a pasted CallFunction to VEase is dropped)
a2 = d_op("Multiply_DoubleDouble", X3 + 450, Y3 + 450, alpha, alpha)
ve = kml("VLerp", X3 + 650, Y3 + 300, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)),
                                       ("Alpha", "real", dict(subcat="float", extra='DefaultValue="0.0",')),
                                       ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(self_get("FlyFrom", "struct", X3 + 450, Y3 + 300, sub=VEC), ve["A"])
g.link(hand, ve["B"])
g.link(a2, ve["Alpha"])
sl = member_call(ACTOR, "K2_SetActorLocation", X3 + 950, Y3 - 100, fly(X3 + 800, Y3 + 100), "toward the hand as seen", [
    ("NewLocation", "struct", dict(sub=VEC)), B("bSweep"),
    ("SweepHitResult", "struct", dict(sub=HIT, out=True)), B("bTeleport", "true"), RB])
g.link(ve["ReturnValue"], sl["NewLocation"])
g.link(ba["then"], sl["execute"])
sl2 = member_call(ACTOR, "K2_SetActorLocation", X3 + 950, Y3 + 250, fly(X3 + 800, Y3 + 450), "in the hand (follow it)", [
    ("NewLocation", "struct", dict(sub=VEC)), B("bSweep"),
    ("SweepHitResult", "struct", dict(sub=HIT, out=True)), B("bTeleport", "true"), RB])
g.link(hand, sl2["NewLocation"])
g.link(ba["else"], sl2["execute"])
#   shrink with the arms' sideways squeeze, so it sits in the hand at the right size
bxs = kml("BreakTransform", X3 + 300, Y3 + 1500, [("InTransform", "struct", dict(sub=XFORM)),
                                                 ("Location", "struct", dict(sub=VEC, out=True)),
                                                 ("Rotation", "struct", dict(sub=ROT, out=True)),
                                                 ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(self_get("ItemXf", "struct", X3 + 100, Y3 + 1500, sub=XFORM), bxs["InTransform"])
lerp_k = kml("Lerp", X3 + 300, Y3 + 1700, [D("A", "1.0"), D("B"), D("Alpha"), RD])
g.link(s_eff, lerp_k["B"])
g.link(alpha, lerp_k["Alpha"])
ssc = member_call(ACTOR, "SetActorScale3D", X3 + 700, Y3 + 1400, fly(X3 + 550, Y3 + 1600), "scale as seen",
                  [("NewScale3D", "struct", dict(sub=VEC))])
g.link(vop("Multiply_VectorFloat", X3 + 500, Y3 + 1600, bxs["Scale"], lerp_k["ReturnValue"], b_cat="real", b_sub="None", b_subcat="double"),
       ssc["NewScale3D"])
g.link(sq3["then_1"], ssc["execute"])
#   probe: where the item meets the hand, in camera space, and the squeeze factor (once per item)
bat = branch(X3 + 1300, Y3 + 250, "first frame in the hand? (probe values)", b_not(X3 + 1150, Y3 + 450, self_get("FlyAttached", "bool", X3 + 950, Y3 + 450)))
g.link(sl2["then"], bat["execute"])
hrel = vop("Subtract_VectorVector", X3 + 1300, Y3 + 700, hand, cl_)
pr = []
for k, (var, axis) in enumerate((("GrabFwd", cf_), ("GrabRight", cr_), ("GrabUp", cu_))):
    pr.append(set_from(var, "real", X3 + 1600 + 300 * k, Y3 + 250, vop("Dot_VectorVector", X3 + 1500, Y3 + 800 + 100 * k, hrel, axis, ret_sub="real"),
                       "camera space" if k == 0 else "", subcat="double"))
pr.append(set_from("FovS", "real", X3 + 2500, Y3 + 250, s_eff, "squeeze", subcat="double"))
pr.append(self_set("FlyAttached", "bool", X3 + 3100, Y3 + 250, "", default="true"))
chain(*pr)
g.link(bat["then"], pr[0]["execute"])
pocket = b_and(X3 + 900, Y3 + 800, d_op("GreaterEqual_DoubleDouble", X3 + 700, Y3 + 750, alpha, b_const="1.0", ret=RB),
               d_op("GreaterEqual_DoubleDouble", X3 + 700, Y3 + 850, montage_time_since_reach(X3 + 500, Y3 + 850),
                    self_get("PocketTime", "real", X3 + 500, Y3 + 1000, subcat="double"), ret=RB))
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
g.link(sq["then_6"], br4["execute"])
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
