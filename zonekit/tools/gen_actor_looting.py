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
                  or more money; closed (context gone 0.25 s and the view hidden, or 3 s). v0.2+: the touch BEFORE the
                  window (our IMC_ImmLoot swallows the interact while a corpse / stash is in sight; the press reaches,
                  holds at 0.6 s, then the game's interact is injected); on close the hand comes back (BUILD.md).
    3 Pending reach: skip (sprint, aim, MainActionSlot action, another left-hand montage, dialogue, cutscene,
                  detector or binoculars in hand, Enabled off) -> NSkips += 1, SkipBits = why
                  else -> the grab in the LeftHand slot (weapon: AS_ImmLoot_Grab, or the touch asset picked at the
                  press; empty hands: the AS_ImmLoot_GrabBH segment for the item's direction) unless one is already
                  before its pocketing frame, and (PendingCopy) a copy of the item (StaticMeshActor /
                  SkeletalMeshActor) spawned where the item was.
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
HOLDC = cls("/Script/Stalker2.HoldComponent")
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
g.untangle_limit = 0   # 2026-10-11: the editor ran out of memory deleting the 4100-node graph (cloned shared trees)
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


def pick_bh(x, y):
    """v1.1.1: the empty-hands PICKUP (GrabBH and not a hold-to-use reach). Builds 26-48 gated their pickup-only item
    copy changes on GrabBH alone, which the use reach also sets: the use's copy stopped following the hand (v1.1.0:
    hold F looked vanilla). The use keeps the checkpoint-holduse behaviour."""
    return b_and(x + 100, y, self_get("GrabBH", "bool", x - 100, y), b_not(x, y + 70, self_get("UseMode", "bool", x - 200, y + 70)))


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


def is_valid_class(x, y, cls_pin):
    n = lib_pure(KSL, "KismetSystemLibrary", "IsValidClass", x, y, [("Class", "class", dict(sub=OBJ)), RB])
    g.link(cls_pin, n["Class"])
    return n["ReturnValue"]


def self_ref(x, y):
    n = Node(g, BG + "K2Node_Self", nm("K2Node_Self"), x, y, "")
    n.pin("self", "object", sub=SELF, out=True)
    return n["self"]


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
    """The actor under the crosshair: the game's own interaction target first (PC.GetInteractedActor, else the owner of
    PC.GetInteractionTarget), else our sphere trace (LookActor). Nexus (Jerbo400, +1): "looted ~15 items, 6-7 had no
    animation": 1.0.1 used only the trace (10 cm, visibility), which misses small / cluttered items, so the pickup was
    never seen; 1.0.0 used only the game's target."""
    ia = member_pure(PC, "GetInteractedActor", x, y, as_pc, [("ReturnValue", "object", dict(sub=ACTOR, out=True))])["ReturnValue"]
    it = member_pure(PC, "GetInteractionTarget", x, y + 100, as_pc, [("ReturnValue", "object", dict(sub=ICOMP, out=True))])["ReturnValue"]
    ow = member_pure(ACOMP, "GetOwner", x + 200, y + 100, it, [("ReturnValue", "object", dict(sub=ACTOR, out=True))])["ReturnValue"]
    s1 = kml("SelectObject", x + 400, y + 100, [("A", "object", dict(sub=OBJ)), ("B", "object", dict(sub=OBJ)),
                                                 B("bSelectA"), ("ReturnValue", "object", dict(sub=OBJ, out=True))])
    g.link(ow, s1["A"])
    g.link(self_get("LookActor", "object", x + 200, y + 200, sub=ACTOR), s1["B"])
    g.link(is_valid(x + 300, y + 250, ow), s1["bSelectA"])
    sel = kml("SelectObject", x + 600, y, [("A", "object", dict(sub=OBJ)), ("B", "object", dict(sub=OBJ)),
                                           B("bSelectA"), ("ReturnValue", "object", dict(sub=OBJ, out=True))])
    g.link(ia, sel["A"])
    g.link(s1["ReturnValue"], sel["B"])
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
g.box("EdGraphNode_Comment_900", -80, -160, 2600, 1500, "Tick: player, mesh, anim instance, what the crosshair is on")
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
# the player goes into a variable once per tick; every use reads it locally (no wires fanning out from the cast)
spl = set_from("Player", "object", 500, 0, cast["AsPC"], "remember the player", sub=PC)
g.link(cast["then"], spl["execute"])
as_pc = self_get("Player", "object", 650, 300, sub=PC)
sq = sequence(700, 0, "tick steps", 8)
# 1.0.1e: what the crosshair is on, by our own sphere trace from the camera (10 cm, 3.5 m, visibility, the player
# ignored); LookActor / LookComp replace PC.GetInteractedActor / GetInteractionTarget / GetInteractedComponent
_cmt = lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", 300, 900,
                [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                 ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"]
_clt = member_pure(PCM, "GetCameraLocation", 500, 900, _cmt, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_crt = member_pure(PCM, "GetCameraRotation", 500, 1000, _cmt, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_cft = kml("GetForwardVector", 700, 1000, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_crt, _cft["InRot"])
_cfr = kml("Multiply_VectorFloat", 900, 1000, [("A", "struct", dict(sub=VEC)), ("B", "real", dict(subcat="double", extra='DefaultValue="350.0",')),
                                               ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_cft["ReturnValue"], _cfr["A"])
_cen = kml("Add_VectorVector", 1100, 950, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_clt, _cen["A"])
g.link(_cfr["ReturnValue"], _cen["B"])
_mka = Node(g, BG + "K2Node_MakeArray", nm("K2Node_MakeArray"), 900, 1200, "", ["NumInputs=1"])
_mka.pin("[0]", "object", sub=ACTOR)
_mka.pin("Array", "object", sub=ACTOR, out=True)
_mka.pins["Array"].container = "Array"
g.link(as_pc, _mka["[0]"])
trc = lib_call(KSL, "SphereTraceSingle", 1300, 800, "what the crosshair is on (our own trace: no calls into the game's interaction system)", [
    ("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
    ("Start", "struct", dict(sub=VEC)), ("End", "struct", dict(sub=VEC)),
    ("Radius", "real", dict(subcat="float", extra='DefaultValue="10.000000",')),
    ("TraceChannel", "byte", dict(sub=EN("/Script/Engine.ETraceTypeQuery"), extra='DefaultValue="TraceTypeQuery1",')),
    ("bTraceComplex", "bool", dict(extra='DefaultValue="false",')),
    ("ActorsToIgnore", "object", dict(sub=ACTOR)),
    ("DrawDebugType", "byte", dict(sub=EN("/Script/Engine.EDrawDebugTrace"), extra='DefaultValue="None",')),
    ("OutHit", "struct", dict(sub=HIT, out=True)),
    ("bIgnoreSelf", "bool", dict(extra='DefaultValue="true",')),
    ("ReturnValue", "bool", dict(out=True))], "/Script/Engine.Default__KismetSystemLibrary")
trc.pins["ActorsToIgnore"].container = "Array"
trc.pins["ActorsToIgnore"].ref = True
trc.pins["ActorsToIgnore"].const = True
g.link(_clt, trc["Start"])
g.link(_cen["ReturnValue"], trc["End"])
g.link(_mka["Array"], trc["ActorsToIgnore"])
bhr = lib_pure(GS, "GameplayStatics", "BreakHitResult", 1700, 1000, [("Hit", "struct", dict(sub=HIT)),
                                                                     ("HitActor", "object", dict(sub=ACTOR, out=True)),
                                                                     ("HitComponent", "object", dict(sub=PRIM, out=True)),
                                                                     ("Location", "struct", dict(sub=VEC, out=True))])
bhr.pins["Hit"].ref = True
bhr.pins["Hit"].const = True
g.link(trc["OutHit"], bhr["Hit"])
sla = set_from("LookActor", "object", 1900, 800, bhr["HitActor"], "under the crosshair", sub=ACTOR)
slk = set_from("LookComp", "object", 2200, 800, bhr["HitComponent"], "", sub=PRIM)
g.link(spl["then"], trc["execute"])
slp = set_from("LookPoint", "struct", 2500, 800, bhr["Location"], "the point it hit (doors)", sub=VEC)
chain(trc, sla, slk, slp)
g.link(slp["then"], sq["execute"])
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
# 1.0.1i: an early touch build (2026-10-10, patch_touch3) called PC.RemoveLeftHandFromItemEnded at every touch and
# never the matching ReturnLeftHandOnItemEnded: the player's "left hand off the item" state stayed set, and
# IsLeftHandBusy has read true at rest ever since (probe). The body carry is a left-hand action: its prompt stayed a
# dot through every build, even with this actor not ticking. Once per world: tell the game the left hand is back.
rlh = member_call(PC, "ReturnLeftHandOnItemEnded", X0 + 650, Y0 + 250, as_pc, "left hand back on the item (clears a state an early build left set)")
g.link(si0["then"], rlh["execute"])
# 1.0.1k added PC.EnableInteractions after it: the carry died again (1.0.1i, the reset alone, carried): removed.
imc_c = load_imc(X0 + 950, Y0, "IMC_Inventory", rlh["then"], "inventory / loot input context (game path)")
sim0 = set_from("InvIMC", "object", X0 + 1700, Y0, imc_c["AsInput Mapping Context"], "remember it", sub=IMC_CLS)
# 1.1: the MCM settings provider (BP_ImmLootMCM), loaded by name so this actor never imports MCM: without MCM installed
# that class fails to load, nothing is spawned, the mod works with its defaults
SCPS = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.SoftClassPath'\""
_mkc = lib_pure(KSL, "KismetSystemLibrary", "MakeSoftClassPath", X0 + 1900, Y0 + 400,
                [("PathString", "string", dict(extra='DefaultValue="/ImmersiveLooting/Runtime/BP_ImmLootMCM.BP_ImmLootMCM_C",')),
                 ("ReturnValue", "struct", dict(sub=SCPS, out=True))])
_cvc = lib_pure(KSL, "KismetSystemLibrary", "Conv_SoftClassPathToSoftClassRef", X0 + 2150, Y0 + 400,
                [("SoftClassPath", "struct", dict(sub=SCPS)), ("ReturnValue", "softclass", dict(sub=OBJ, out=True))])
_cvc.pins["SoftClassPath"].ref = True
_cvc.pins["SoftClassPath"].const = True
g.link(_mkc["ReturnValue"], _cvc["SoftClassPath"])
_ldc = lib_call(KSL, "LoadClassAsset_Blocking", X0 + 2050, Y0, "MCM provider class (only loads with MCM installed)",
                [("AssetClass", "softclass", dict(sub=OBJ)), ("ReturnValue", "class", dict(sub=OBJ, out=True))],
                "/Script/Engine.Default__KismetSystemLibrary")
g.link(_cvc["ReturnValue"], _ldc["AssetClass"])
g.link(sim0["then"], _ldc["execute"])
_bvc = branch(X0 + 2400, Y0, "MCM there (the class loaded)?", is_valid_class(X0 + 2300, Y0 + 200, _ldc["ReturnValue"]))
g.link(_ldc["then"], _bvc["execute"])
_spm = exec_pins(Node(g, BG + "K2Node_SpawnActorFromClass", nm("K2Node_SpawnActorFromClass"), X0 + 2700, Y0, "spawn the MCM provider"))
_spm.pin("Class", "class", sub=ACTOR)
_spm.pin("ReturnValue", "object", sub=ACTOR, out=True)
_spm.pin("WorldContextObject", "object", sub=OBJ, hidden=True)
_spm.pin("SpawnTransform", "struct", sub=XFORM)
_spm.pin("CollisionHandlingOverride", "byte", sub=EN("/Script/Engine.ESpawnActorCollisionHandlingMethod"), extra='DefaultValue="AlwaysSpawn",')
_spm.pin("TransformScaleMethod", "byte", sub=EN("/Script/Engine.ESpawnActorScaleMethod"), adv=True, extra='DefaultValue="MultiplyWithRoot",')
_spm.pin("Owner", "object", sub=ACTOR, adv=True)
# (compile, build 15: "Actor Class Reference is not compatible with Object Class Reference": the loaded class is cast)
_ccast = exec_pins(Node(g, BG + "K2Node_ClassDynamicCast", nm("K2Node_ClassDynamicCast"), X0 + 2550, Y0 - 150, "an actor class",
                        ["TargetType=" + ACTOR]))
_ccast.pin("CastFailed", "exec", out=True)
_ccast.pin("Class", "class", sub=OBJ)
_ccast.pin("AsActor", "class", sub=ACTOR, out=True)
_ccast.pin("bSuccess", "bool", out=True)
g.link(_ldc["ReturnValue"], _ccast["Class"])
g.link(_ccast["AsActor"], _spm["Class"])
g.link(member_pure(ACTOR, "GetTransform", X0 + 2500, Y0 + 400, self_ref(X0 + 2300, Y0 + 450), [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"], _spm["SpawnTransform"])
g.link(_bvc["then"], _ccast["execute"])
g.link(_ccast["then"], _spm["execute"])
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
# 1.3.1 MCM "Hide items in the hand" (Nexus, Farsot: "it looks like you're force pulling items"; off by default): no copy
# n2j (tester: "the item disappears right as I tap F, before the hand gets there; it should disappear and appear in
# the hand instantly once the reach is done"): the copy always waits where the item lay; HideItem only makes the
# hand take it at once at the grab frame (no pull into the hand, step 5)
sc1 = self_set("PendingCopy", "bool", X1 + 1200, Y1 - 300, "with a copy (HideItem: taken at once, step 5)", default="true")
chain(np1, sp1, sc1)

# ---- 3: run a pending reach (from a pickup or a closed loot window): skip, or montage (+ flying copy) ----
X3R, Y3R = X1 + 300, Y1 + 2700
br3 = branch(X3R, Y3R, "a reach is pending?", self_get("PendingReach", "bool", X3R - 200, Y3R + 150))
g.link(sq["then_3"], br3["execute"])
spr = self_set("PendingReach", "bool", X3R + 300, Y3R, "taken", default="false")
g.link(br3["then"], spr["execute"])

# skip conditions (each also a bit in SkipBits for the probe)
SX, SY = X1 + 400, Y1 + 600


def _ieq(x, y, var, val):
    n = kml("EqualEqual_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{val}",')), RB])
    g.link(self_get(var, "int", x - 200, y), n["A"])
    return n["ReturnValue"]


#   n2f (tester, bag on bodies, looting fast: "sometimes the backpack doesn't appear"; probe: the press came during the
#   last bag's weapon draw, i.e. our replay of the game's equip, and was skipped as "action"; the skipped touch then left a
#   1 s "wait for an item's use" that stopped the next bag): our own equip replay is no reason to skip a bag or a pat
#   (both hide the weapon and replay the draw after; the replay is stopped when they start)
_tib = lambda x, y: self_get("TouchIsBody", "bool", x, y)
_hides = b_or(SX - 200, SY + 1200,
              b_and(SX - 300, SY + 1200, _tib(SX - 500, SY + 1200), b_or(SX - 400, SY + 1260, _ieq(SX - 500, SY + 1260, "BodyMode", 1), _ieq(SX - 500, SY + 1330, "BodyMode", 2))),
              b_and(SX - 300, SY + 1400, b_not(SX - 400, SY + 1400, _tib(SX - 600, SY + 1400)), _ieq(SX - 500, SY + 1470, "StashMode", 1)))
_replay_ours = lambda x, y: d_op("GreaterEqual_DoubleDouble", x, y, self_get("EquipReplayAt", "real", x - 200, y, subcat="double"),
                                 self_get("GameMontageAt", "real", x - 200, y + 70, subcat="double"), ret=RB)
_ours = b_and(SX, SY + 1200, self_get("LootReach", "bool", SX - 200, SY + 1130), b_not(SX - 100, SY + 1620, self_get("DoorTouch", "bool", SX - 300, SY + 1620)),
              _hides, _replay_ours(SX - 100, SY + 1550))
conds = [
    ("sprint", obj_q("IsSprinting", SX, SY, as_pc)),
    ("aim", obj_q("IsAiming", SX, SY + 80, as_pc)),
    # 1.1.2: neither for our use reach over a use we hold (a use from the loot window: held longer than 0.3 s, our touch
    # still blending out in LeftHand)
    ("action", b_and(SX + 240, SY + 160, slot_active(SX, SY + 160, anim, "MainActionSlot"),
                     b_not(SX + 200, SY + 200, d_op("Less_DoubleDouble", SX + 100, SY + 200,
                                                    d_op("Subtract_DoubleDouble", SX - 100, SY + 200, now(SX - 300, SY + 200),
                                                         self_get("GameMontageAt", "real", SX - 300, SY + 260, subcat="double")),
                                                    b_const="0.3", ret=RB)),
                     b_not(SX + 200, SY + 130, self_get("UseMode", "bool", SX, SY + 130)),
                     b_not(SX + 200, SY + 1100, _ours))),   # n2f
    ("lefthand", b_and(SX + 240, SY + 240, slot_active(SX, SY + 240, anim, "LeftHand"),
                       b_not(SX + 200, SY + 320, grab_active(SX, SY + 320)),
                       b_not(SX + 200, SY + 290, self_get("UseMode", "bool", SX, SY + 290)))),
    ("dialog", obj_q("IsInStaticDialog", SX, SY + 400, as_pc, owner=PC)),
    ("cinematic", obj_q("IsInCinematic", SX, SY + 480, as_pc)),
    ("detector", obj_q("IsDetectorInHands", SX, SY + 560, as_pc)),
    ("binoculars", obj_q("IsBinocularsInHands", SX, SY + 640, as_pc)),
    ("disabled", b_not(SX + 200, SY + 720, self_get("Enabled", "bool", SX, SY + 720))),
    ("use", b_and(SX + 240, SY + 880, self_get("KeyHeld", "bool", SX, SY + 860),
                  b_not(SX + 100, SY + 900, self_get("PreReach", "bool", SX - 100, SY + 900)),
                  b_not(SX + 100, SY + 960, self_get("UseMode", "bool", SX - 100, SY + 960)),
                  b_not(SX + 100, SY + 1020, self_get("LHOff", "bool", SX - 100, SY + 1020)),
                  d_op("GreaterEqual_DoubleDouble", SX + 100, SY + 940,
                       d_op("Subtract_DoubleDouble", SX - 100, SY + 940, now(SX - 300, SY + 940),
                            self_get("InteractPressAt", "real", SX - 300, SY + 1000, subcat="double")), b_const="0.3", ret=RB))),
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
# build 17: skipped as a hold to use (F still held 0.3 s after the press): wait for the game's use animation
_buw = branch(X1 + 1850, Y1 - 700, "a hold to use? wait for the game's use animation (our reach then plays over it)", conds[-1][1])
g.link(ns["then"], _buw["execute"])
_suw = self_set("UseWait", "bool", X1 + 2150, Y1 - 700, "waiting for the use animation", default="true")
g.link(_buw["then"], _suw["execute"])
_suwa = set_from("UseWaitAt", "real", X1 + 2450, Y1 - 700, now(X1 + 2300, Y1 - 500), "", subcat="double")
chain(_suw, _suwa)

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
TOUCH_SEQS = [f"/ImmersiveLooting/Runtime/AS_ImmLoot_TouchAr{i}.AS_ImmLoot_TouchAr{i}" for i in range(25)]   # corpse / stash, long guns (build x)   # 2026-10-10: corpse / stash
# touch, weapon in hand (make_grab_seq build_touch): the hand reaches toward the body's / stash's centre. With a weapon the
# arm rig follows the view (build d trace), so the centre's direction in VIEW axes picks the asset: elevation -45..+15 x
# azimuth -30..+30, 15 deg bins, index ie * 5 + ia, stored in TouchAsset at the press
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
bdt3 = branch(X1 + 2300, Y1 - 600, "a door touch? its own asset (also with empty hands)", self_get("DoorTouch", "bool", X1 + 2100, Y1 - 500))
_bu3 = branch(X1 + 2150, Y1 - 1300, "build 17: the game's use animation paused for us? our use reach over it (FullBody, additive)",
              self_get("UseMode", "bool", X1 + 1950, Y1 - 1200))
g.link(bm["else"], _bu3["execute"])
g.link(_bu3["else"], bdt3["execute"])
mp = play_grab(X1 + 2750, Y1 - 50, GRAB_SEQ, "left-hand grab, armed")
# build 38 (tester: "when picking something up while crouched there is no animation", reported many times; probe: crouched,
# the hand bone stayed 77 cm below the view = the LeftHand slot's reach is covered in the crouch pose): the empty-hands
# pickup plays in FullBody (after every arm layer, like the eat/drink grab), an additive on the left arm
mpb = play_grab(X1 + 2750, Y1 + 350, "/ImmersiveLooting/Runtime/AS_ImmLoot_GrabBHAdd.AS_ImmLoot_GrabBHAdd",
                "grab, empty hands: FullBody additive (nothing covers it, crouched or not)")
mpb.pins["SlotNodeName"].extra = 'DefaultValue="FullBody",'
# build 41: crouched, the same grab on the crouch table
mpbc = play_grab(X1 + 2750, Y1 + 650, "/ImmersiveLooting/Runtime/AS_ImmLoot_GrabBHAddCrouch.AS_ImmLoot_GrabBHAddCrouch", "grab, empty hands, crouched: FullBody additive")
mpbc.pins["SlotNodeName"].extra = 'DefaultValue="FullBody",'
mpbc.pins["BlendInTime"].extra = 'DefaultValue="0.050000",'
mpbc.pins["BlendOutTime"].extra = 'DefaultValue="0.250000",'
mpb.pins["BlendInTime"].extra = 'DefaultValue="0.050000",'
mpb.pins["BlendOutTime"].extra = 'DefaultValue="0.250000",'
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
_vl, _vf, _vr, _vu, _vfov = cam_basis(X1 + 1500, Y1 + 1200)
_vrel = vop("Subtract_VectorVector", X1 + 1900, Y1 + 1250, self_get("ItemCenter", "struct", X1 + 1700, Y1 + 1300, sub=VEC), _vl)
_vx = vop("Dot_VectorVector", X1 + 2050, Y1 + 1250, _vrel, _vf, ret_sub="real")
_vy = vop("Dot_VectorVector", X1 + 2050, Y1 + 1320, _vrel, _vr, ret_sub="real")
_vz = vop("Dot_VectorVector", X1 + 2050, Y1 + 1390, _vrel, _vu, ret_sub="real")
_vel = kml("DegAtan2", X1 + 2200, Y1 + 1250, [D("Y"), D("X"), RD])
g.link(_vz, _vel["Y"])
g.link(_vx, _vel["X"])
_vaz = kml("DegAtan2", X1 + 2200, Y1 + 1350, [D("Y"), D("X"), RD])
g.link(_vy, _vaz["Y"])
g.link(_vx, _vaz["X"])
_vds = kml("VSize", X1 + 2200, Y1 + 1450, [("A", "struct", dict(sub=VEC)), RD])
g.link(_vrel, _vds["A"])


_vfz = kml("BreakVector", X1 + 2050, Y1 + 1600, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                                  ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(_vf, _vfz["InVec"])
_vpitch = kml("DegAsin", X1 + 2200, Y1 + 1600, [D("A"), RD])
g.link(_vfz["Z"], _vpitch["A"])
_steep = d_op("Less_DoubleDouble", X1 + 2350, Y1 + 1600, _vpitch["ReturnValue"], b_const="-40.0", ret=RB)


# build 35 (tester on build 34: "now the hand is always way too high"; reviewed). Probe: the left arm stays in the body
# (mesh) frame whatever the view pitch (build 34's live-spine index read -0.5 at both -23 and -47: the spine pitches 1:1
# with the view, the arm chain is counter-rotated), but its root and the camera move. So the target is built from
# MEASURED positions at the reach start, all in mesh space: the hand target T on the ray from the live camera C to the
# item P, 0.9 x the reach (52.4 cm) from the live arm root A (jnt_l_arm); shifted by (A_table - A) onto the table's arm
# root A_table (-15.36, -16.62, 148.64); then the direction from the table's eye (0, 0, 160.34) of the point X on the
# ray A_table -> T' that is 60 cm from that eye = a dist-60 segment (the arm fully out toward it: the only regime the
# table has been checked in) whose arm passes through T'. Computed step by step into variables (Aim*) at the reach
# start, before the segment is picked.
A_TAB = (-29.17, -18.23, 145.3)   # build 38: the FullBody pickup table's arm root (make_grab_seq log)
EYE = (0.0, 0.0, 160.338)
W_ = tuple(a_ - e_ for a_, e_ in zip(A_TAB, EYE))
AX, AY = X1 + 1300, Y1 - 3600
g.box("EdGraphNode_Comment_934", AX - 400, AY - 300, 6400, 1100, "Build 35: pickup aim from measured positions (live camera ray, live arm root, mapped onto the table)")
_mxw = member_pure(SC_, "K2_GetComponentToWorld", AX - 300, AY + 400, mesh, [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
av = lambda n, x, y: self_get(n, "struct", x, y, sub=VEC)
ar = lambda n, x, y: self_get(n, "real", x, y, subcat="double")


def _to_mesh(x, y, world_pin):
    n = kml("InverseTransformLocation", x, y, [("T", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_mxw, n["T"])
    g.link(world_pin, n["Location"])
    return n["ReturnValue"]


def _vec(x, y, xyz):
    return kml("MakeVector", x, y, [D("X", str(xyz[0])), D("Y", str(xyz[1])), D("Z", str(xyz[2])), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]


def _dot(x, y, a_, b_):
    return vop("Dot_VectorVector", x, y, a_, b_, ret_sub="real")


def _vmul(x, y, v, f):
    return vop("Multiply_VectorFloat", x, y, v, f, b_cat="real", b_sub="None", b_subcat="double")


def _norm(x, y, v):
    n = kml("Normal", x, y, [("A", "struct", dict(sub=VEC)), D("Tolerance", "0.0001"), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(v, n["A"])
    return n["ReturnValue"]


def _size(x, y, v):
    n = kml("VSize", x, y, [("A", "struct", dict(sub=VEC)), RD])
    g.link(v, n["A"])
    return n["ReturnValue"]


def _sqrt0(x, y, v):
    n = kml("Sqrt", x, y, [D("A"), RD])
    g.link(d_op("FMax", x - 150, y, v, b_const="0.0"), n["A"])
    return n["ReturnValue"]


_steps = []


def _sv(name, pin, k, comment=""):
    n = set_from(name, "struct", AX + 300 * k, AY, pin, comment, sub=VEC)
    _steps.append(n)


def _sr(name, pin, k, comment=""):
    n = set_from(name, "real", AX + 300 * k, AY, pin, comment, subcat="double")
    _steps.append(n)


Y2_ = AY + 250
_sv("AimC", _to_mesh(AX - 100, Y2_, cam_basis(AX - 300, Y2_ + 200)[0]), 0, "build 35: the live camera, mesh space")
# build 41: crouched (camera below 130 cm, mesh space) uses the crouch table and its geometry
_acz = kml("BreakVector", AX + 50, Y2_ + 500, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                              ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(av("AimC", AX - 100, Y2_ + 500), _acz["InVec"])
_sst = set_from("AimStand", "bool", AX + 150, AY, d_op("Greater_DoubleDouble", AX + 200, Y2_ + 500, _acz["Z"], b_const="130.0", ret=RB), "standing? (else crouched)")
_steps.append(_sst)
A_CR, EYE_CR = (-31.99, -17.41, 111.02), (0.0, 0.0, 130.21)
W_CR = tuple(a_ - e_ for a_, e_ in zip(A_CR, EYE_CR))


def _selv(x, y, a3, b3):
    n = kml("SelectVector", x, y, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)), ("bPickA", "bool", dict(extra='DefaultValue="false",')),
                                   ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_vec(x - 150, y, a3), n["A"])
    g.link(_vec(x - 150, y + 70, b3), n["B"])
    g.link(self_get("AimStand", "bool", x - 150, y + 140), n["bPickA"])
    return n["ReturnValue"]


def _self(x, y, a, b):
    n = kml("SelectFloat", x, y, [D("A", f"{a}"), D("B", f"{b}"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
    g.link(self_get("AimStand", "bool", x - 150, y + 70), n["bPickA"])
    return n["ReturnValue"]


_sv("AimP", _to_mesh(AX + 200, Y2_, self_get("ItemCenter", "struct", AX + 50, Y2_ + 80, sub=VEC)), 1, "the item")
_sv("AimA", _to_mesh(AX + 500, Y2_, member_pure(SKC, "GetSocketLocation", AX + 350, Y2_ + 100, mesh,
                                                [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_arm",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]), 2, "the live arm root")
# build 37 (tester: on tables "the hand goes too close to the centre and up; it needs to be lower on the screen"): the
# hand's line from the camera is turned ~8 deg down and ~4.5 deg left of the item (it lands below-left of it)
_shx = member_pure(SKC, "GetSocketTransform", AX + 600, Y2_ + 600, mesh,
                   [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_shoulder",')),
                    ("TransformSpace", "byte", dict(sub=EN("/Script/Engine.ERelativeTransformSpace"), extra='DefaultValue="RTS_Component",')),
                    ("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]


def _sh_yaw_b(x, y, bone, axis="1.000000,0.000000,0.000000"):
    t = member_pure(SKC, "GetSocketTransform", x - 300, y, mesh,
                    [("InSocketName", "name", dict(extra=f'DefaultValue="{bone}",')),
                     ("TransformSpace", "byte", dict(sub=EN("/Script/Engine.ERelativeTransformSpace"), extra='DefaultValue="RTS_Component",')),
                     ("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
    ax = kml("TransformDirection", x - 150, y, [("T", "struct", dict(sub=XFORM)), ("Direction", "struct", dict(sub=VEC, extra=f'DefaultValue="{axis}",')),
                                               ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(t, ax["T"])
    bv = kml("BreakVector", x, y, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                   ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
    g.link(ax["ReturnValue"], bv["InVec"])
    yw = kml("DegAtan2", x + 150, y, [D("Y"), D("X"), RD])
    g.link(bv["Y"], yw["Y"])
    g.link(bv["X"], yw["X"])
    return yw["ReturnValue"]


def _sh_yaw(x, y):
    """yaw (deg, component space) of the live left shoulder's X axis"""
    t = member_pure(SKC, "GetSocketTransform", x - 300, y, mesh,
                    [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_shoulder",')),
                     ("TransformSpace", "byte", dict(sub=EN("/Script/Engine.ERelativeTransformSpace"), extra='DefaultValue="RTS_Component",')),
                     ("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
    ax = kml("TransformDirection", x - 150, y, [("T", "struct", dict(sub=XFORM)), ("Direction", "struct", dict(sub=VEC, extra='DefaultValue="1.000000,0.000000,0.000000",')),
                                               ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(t, ax["T"])
    bv = kml("BreakVector", x, y, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                   ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
    g.link(ax["ReturnValue"], bv["InVec"])
    yw = kml("DegAtan2", x + 150, y, [D("Y"), D("X"), RD])
    g.link(bv["Y"], yw["Y"])
    g.link(bv["X"], yw["X"])
    return yw["ReturnValue"]


_sr("AimShYaw0", _sh_yaw(AX + 750, Y2_ + 700), 2, "the left shoulder's yaw at the grab start (build 47)")
_sv("AimD", _norm(AX + 950, Y2_, vop("Add_VectorVector", AX + 850, Y2_, _norm(AX + 750, Y2_ - 80, vop("Subtract_VectorVector", AX + 650, Y2_, av("AimP", AX + 500, Y2_ + 80), av("AimC", AX + 500, Y2_ + 150))),
                                     _vec(AX + 700, Y2_ + 200, (0.0, -0.08, -0.14)))), 3, "camera -> item, turned a little down and left")
_sv("AimOC", vop("Subtract_VectorVector", AX + 1050, Y2_, av("AimC", AX + 900, Y2_ + 80), av("AimA", AX + 900, Y2_ + 150)), 4)
_sr("AimB", _dot(AX + 1350, Y2_, av("AimD", AX + 1200, Y2_ + 80), av("AimOC", AX + 1200, Y2_ + 150)), 5)
_disc = d_op("Subtract_DoubleDouble", AX + 1600, Y2_, d_op("Multiply_DoubleDouble", AX + 1450, Y2_, ar("AimB", AX + 1300, Y2_ + 220), ar("AimB", AX + 1300, Y2_ + 290)),
             d_op("Subtract_DoubleDouble", AX + 1450, Y2_ + 100, _dot(AX + 1300, Y2_ + 360, av("AimOC", AX + 1150, Y2_ + 360), av("AimOC", AX + 1150, Y2_ + 430)),
                  b_const=f"{(0.9 * 52.36) ** 2:.3f}"))
_troot = d_op("Add_DoubleDouble", AX + 1800, Y2_, d_op("Multiply_DoubleDouble", AX + 1650, Y2_ - 80, ar("AimB", AX + 1500, Y2_ - 80), b_const="-1.0"), _sqrt0(AX + 1700, Y2_ + 80, _disc))
_sr("AimT", d_op("FMin", AX + 1950, Y2_, _troot, _size(AX + 1800, Y2_ + 150, vop("Subtract_VectorVector", AX + 1650, Y2_ + 200, av("AimP", AX + 1500, Y2_ + 200), av("AimC", AX + 1500, Y2_ + 270)))),
    6, "along the camera ray: 0.9 x reach from the live arm root (no further than the item)")
# (build 39's mapping through the live shoulder: removed, it sent the hand 60-100 deg up; back to build 38's target)
_tp = vop("Add_VectorVector", AX + 2250, Y2_, vop("Add_VectorVector", AX + 2100, Y2_, av("AimC", AX + 1950, Y2_ + 80), _vmul(AX + 2000, Y2_ + 150, av("AimD", AX + 1850, Y2_ + 150), ar("AimT", AX + 1850, Y2_ + 220))),
          vop("Subtract_VectorVector", AX + 2100, Y2_ + 300, _selv(AX + 1950, Y2_ + 300, A_TAB, A_CR), av("AimA", AX + 1950, Y2_ + 400)))
_sv("AimTp", _tp, 7, "the target, moved onto the table's arm root")
_sv("AimU", _norm(AX + 2550, Y2_, vop("Subtract_VectorVector", AX + 2450, Y2_, av("AimTp", AX + 2300, Y2_ + 80), _selv(AX + 2300, Y2_ + 150, A_TAB, A_CR))), 8, "table arm root -> target")
_sr("AimBW", _dot(AX + 2750, Y2_, av("AimU", AX + 2600, Y2_ + 80), _selv(AX + 2600, Y2_ + 150, W_, W_CR)), 9)
_ww = sum(c * c for c in W_)
_L = d_op("Add_DoubleDouble", AX + 3150, Y2_, d_op("Multiply_DoubleDouble", AX + 3000, Y2_ - 80, ar("AimBW", AX + 2850, Y2_ - 80), b_const="-1.0"),
          _sqrt0(AX + 3050, Y2_ + 80, d_op("Subtract_DoubleDouble", AX + 2950, Y2_ + 80,
                                            d_op("Multiply_DoubleDouble", AX + 2800, Y2_ + 80, ar("AimBW", AX + 2650, Y2_ + 80), ar("AimBW", AX + 2650, Y2_ + 150)),
                                            _self(AX + 2800, Y2_ + 250, f"{_ww - 3600.0:.3f}", f"{sum(c * c for c in W_CR) - 3600.0:.3f}"))))
_sr("AimL", _L, 10)
_sv("AimXE", vop("Add_VectorVector", AX + 3450, Y2_, _selv(AX + 3300, Y2_ + 80, W_, W_CR), _vmul(AX + 3350, Y2_ + 150, av("AimU", AX + 3200, Y2_ + 150), ar("AimL", AX + 3200, Y2_ + 220))), 11,
    "the dist-60 item point, from the table's eye")
for _a, _b in zip(_steps, _steps[1:]):
    g.link(_a["then"], _b["execute"])
AIM_FIRST, AIM_LAST = _steps[0], _steps[-1]
#   the segment from it
_xe = av("AimXE", AX + 2600, AY + 700)
_xb = kml("BreakVector", AX + 2800, AY + 700, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                              ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(_xe, _xb["InVec"])
_xy = kml("VSizeXY", AX + 2800, AY + 850, [("A", "struct", dict(sub=VEC)), RD])
g.link(av("AimXE", AX + 2600, AY + 850), _xy["A"])
_sp_el = kml("DegAtan2", AX + 3000, AY + 700, [D("Y"), D("X"), RD])
g.link(_xb["Z"], _sp_el["Y"])
g.link(_xy["ReturnValue"], _sp_el["X"])
_sp_az = kml("DegAtan2", AX + 3000, AY + 800, [D("Y"), D("X"), RD])
g.link(_xb["Y"], _sp_az["Y"])
g.link(_xb["X"], _sp_az["X"])
_sp_d = {"ReturnValue": d_op("Add_DoubleDouble", AX + 3000, AY + 900, None, b_const="60.0")}   # always the dist-60 segment


def _pick_view(x, y, view_pin, body_pin, raise_steep=0.0):
    """build 34: the use reach in view axes; the empty-hands pickup from the live spine (body_pin = the spine-mapped value)."""
    n = kml("SelectFloat", x, y, [D("A"), D("B"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
    g.link(view_pin, n["A"])
    g.link(body_pin, n["B"])
    g.link(self_get("UseMode", "bool", x - 200, y + 120), n["bPickA"])
    return n["ReturnValue"]


# build 40 (tester: "huge regression" on 39; "simple fix"): build 38's aim, corrected by what build 38 measured: standing the
# hand landed 16 deg higher and 8 deg further left than aimed (crouched: at the aimed height)
_cbv = kml("BreakVector", X1 + 1850, Y1 + 1300, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                                ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(self_get("AimC", "struct", X1 + 1700, Y1 + 1300, sub=VEC), _cbv["InVec"])
_stand = d_op("Greater_DoubleDouble", X1 + 2000, Y1 + 1300, _cbv["Z"], b_const="130.0", ret=RB)   # camera above 130 cm (mesh space) = standing
# build 42: crouched the hand landed 47 deg below the view centre ("grabbing their crotch"; standing lands at -8..-13): +38
_elc = kml("SelectFloat", X1 + 2150, Y1 + 1300, [D("A", "-16.0"), D("B", "38.0"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(_stand, _elc["bPickA"])
# build 48 (tester: crouched, the stash touch "went up toward the top of the screen"; probe: crouched, the +38 correction
# fitted at floor pitches put a stash in front (pitch -32) far up). Crouched pickups land at screen = index - view pitch - 37
# (builds 41-43, pitch -50..-65), so crouched the elevation index is simply the view pitch + 27 (= 10 deg below the centre)
_el_cr = d_op("Subtract_DoubleDouble", X1 + 2250, Y1 + 1400, d_op("Add_DoubleDouble", X1 + 2100, Y1 + 1400, _vpitch["ReturnValue"], b_const="27.0"),
              d_op("Multiply_DoubleDouble", X1 + 2150, Y1 + 1470, d_op("FMax", X1 + 2100, Y1 + 1470, d_op("Add_DoubleDouble", X1 + 1950, Y1 + 1470, _vpitch["ReturnValue"], b_const="45.0"), b_const="0.0"), b_const="1.8"))   # build 49/50
_el_st = d_op("Add_DoubleDouble", X1 + 2250, Y1 + 1250, _sp_el["ReturnValue"], b_const="-16.0")
_elsel = kml("SelectFloat", X1 + 2300, Y1 + 1320, [D("A"), D("B"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(_el_st, _elsel["A"])
g.link(_el_cr, _elsel["B"])
g.link(_stand, _elsel["bPickA"])
_el_u = _pick_view(X1 + 2350, Y1 + 1250, _vel["ReturnValue"], _elsel["ReturnValue"])
_dist_u = _pick_view(X1 + 2350, Y1 + 1400, _vds["ReturnValue"], _sp_d["ReturnValue"])
# build 41: standing +4 ("slightly too far right" at +8); build 43: crouched -25 (build 42 crouched landed 23 deg right of
# the centre, standing lands 4-7 deg left)
# build 44 (tester: crouched "LEFT, it is in the centre"; build 43 crouched landed 3-4 deg left = centre): -37
_azc = kml("SelectFloat", X1 + 2100, Y1 + 1650, [D("A", "4.0"), D("B", "-37.0"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(_stand, _azc["bPickA"])
_az_u = _pick_view(X1 + 2350, Y1 + 1550, _vaz["ReturnValue"], d_op("Add_DoubleDouble", X1 + 2250, Y1 + 1550, _sp_az["ReturnValue"], _azc["ReturnValue"]))
_ie = _bin(X1 + 2500, Y1 + 700, _el_u, "80.0", "15.0", 7)
_id = _bin(X1 + 2500, Y1 + 850, _dist_u, "-30.0", "15.0", 2)
_azo = kml("SelectFloat", X1 + 2300, Y1 + 1100, [D("A", "45.0"), D("B", "15.0"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(self_get("UseMode", "bool", X1 + 2100, Y1 + 1150), _azo["bPickA"])
_ia = _bin(X1 + 2500, Y1 + 1000, d_op("Add_DoubleDouble", X1 + 2400, Y1 + 1050, _az_u, _azo["ReturnValue"]), "0.0", "15.0", 4)   # build 39: use -45..+15, pickup -15..+45


def _imad(x, y, a, mul_const, b):
    m = kml("Multiply_IntInt", x, y, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra=f'DefaultValue="{mul_const}",')),
                                      ("ReturnValue", "int", dict(out=True))])
    g.link(a, m["A"])
    ad = kml("Add_IntInt", x + 150, y + 50, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="0",')),
                                            ("ReturnValue", "int", dict(out=True))])
    g.link(m["ReturnValue"], ad["A"])
    g.link(b, ad["B"])
    return ad["ReturnValue"]


_sum_use = _imad(X1 + 3100, Y1 + 800, _imad(X1 + 2950, Y1 + 700, _ie, 3, _id), 5, _ia)


def _pick_seg(x, y, el_pin, az_pin):
    """build 47: the pickup tables: 8 elevations (15 deg) x 19 azimuths (-30..+60, 5 deg), distance 60 only."""
    return _imad(x + 300, y, _bin(x, y, el_pin, "80.0", "15.0", 7), 19, _bin(x, y + 150, az_pin, "30.0", "5.0", 18))


_sum_pick = _pick_seg(X1 + 2700, Y1 + 1300, _el_u, _az_u)
_sumsel = kml("SelectInt", X1 + 3250, Y1 + 900, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="0",')),
                                                ("bPickA", "bool", dict(extra='DefaultValue="false",')), ("ReturnValue", "int", dict(out=True))])
g.link(_sum_use, _sumsel["A"])
g.link(_sum_pick, _sumsel["B"])
g.link(self_get("UseMode", "bool", X1 + 3050, Y1 + 1000), _sumsel["bPickA"])
_sum = {"ReturnValue": _sumsel["ReturnValue"]}
_cv = kml("Conv_IntToDouble", X1 + 3250, Y1 + 750, [("InInt", "int"), RD])
g.link(_sum["ReturnValue"], _cv["InInt"])
seg_start = d_op("Multiply_DoubleDouble", X1 + 3400, Y1 + 750, _cv["ReturnValue"], b_const="1.5")
g.link(seg_start, mpb["InTimeToStartMontageAt"])
sss0 = set_from("SegStart", "real", X1 + 3700, Y1 + 350, seg_start, "segment start (montage s)", subcat="double")
_pv = [set_from(v, "real", X1 + 4000 + 300 * k, Y1 + 350, src_pin, "item seen from the eye, body frame (probe)" if k == 0 else "", subcat="double")
       for k, (v, src_pin) in enumerate((("ItemElev", _el_u), ("ItemDist", _dist_u), ("ItemAzim", _az_u)))]
chain(sss0, *_pv)
_p35 = []
for k, (v, src_var, comp) in enumerate((("AimCX", "AimC", "X"), ("AimCZ", "AimC", "Z"), ("AimAX", "AimA", "X"), ("AimAY", "AimA", "Y"), ("AimAZ", "AimA", "Z"))):
    _bk = kml("BreakVector", X1 + 5000 + 300 * k, Y1 + 600, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                                         ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
    g.link(self_get(src_var, "struct", X1 + 4800 + 300 * k, Y1 + 650, sub=VEC), _bk["InVec"])
    _p35.append(set_from(v, "real", X1 + 5000 + 300 * k, Y1 + 350, _bk[comp], "aim inputs, mesh space (probe)" if k == 0 else "", subcat="double"))
chain(_pv[-1], *_p35)
sss = {"execute": sss0["execute"], "then": _p35[-1]["then"]}
# 2026-10-10: a corpse / stash touch with a weapon plays AS_ImmLoot_Touch, the same asset form as the rifle grab (a
# short copy of the vanilla grab played from 0), which shows over a rifle where the 180 s reach table never did. The
# hand goes fully out toward the ground ahead, is held at 0.6 s while the window is open, then comes straight back.
blr = branch(X1 + 2600, Y1 - 300, "a corpse / stash touch? (hand fully out) else the item grab", self_get("LootReach", "bool", X1 + 2400, Y1 - 200))
g.link(bst["then"], blr["execute"])
# n2j (tester: armed pickup "goes a little too far right on the way back to the weapon, then recorrects; copy the stash
# return"): per weapon family, AS_ImmLoot_GrabAr / ...Pt (make_grab_seq build_grab_family: the grab to the pocket, then
# the touch's return on the family stance)
_gbt = kml("Conv_ByteToInt", X1 + 2300, Y1, [("InByte", "byte", dict(extra='DefaultValue="0",')), ("ReturnValue", "int", dict(out=True))])
_gbe = kml("EqualEqual_IntInt", X1 + 2450, Y1, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="1",')), RB])
g.link(_gbt["ReturnValue"], _gbe["A"])
_bgp = branch(X1 + 2600, Y1 - 150, "n2j: a pistol (MainHandEquipmentType 1)? the pistol grab (else the long-gun grab)", _gbe["ReturnValue"])
g.link(member_pure(OBJC, "GetMainHandEquipType", X1 + 2100, Y1, as_pc,
                   [("ReturnValue", "byte", dict(sub=EN("/Script/Stalker2.EMainHandEquipmentType"), out=True))])["ReturnValue"], _gbt["InByte"])
g.link(blr["else"], _bgp["execute"])
for _ex, _nm, _yy in ((_bgp["then"], "AS_ImmLoot_GrabPt", -250), (_bgp["else"], "AS_ImmLoot_GrabAr", -100)):
    _sa = self_set("ArmedGrab", "object", X1 + 2650, Y1 + _yy, _nm, sub=ANIMSEQB)
    _sa.pins["ArmedGrab"].extra = f'DefaultObject="/ImmersiveLooting/Runtime/{_nm}.{_nm}",'
    g.link(_ex, _sa["execute"])
    g.link(_sa["then"], mp["execute"])
mp.pins["Asset"].extra = ""
g.link(self_get("ArmedGrab", "object", X1 + 2550, Y1 + 50, sub=ANIMSEQB), mp["Asset"])
mpt = play_grab(X1 + 2750, Y1 - 450, TOUCH_SEQS[12], "left-hand touch, armed: hand out toward the body / stash (asset picked at the press)")
mpt.pins["Asset"].extra = ""
# build r (tester: "when the hand returns to the weapon it does the rotate and twist 360 thing"; Nexus, Tim0st): the 0.7 s
# blend-out started at 0.97 s, in the vanilla grab's hand-at-the-chest frames (23-34), whose left hand is 120-180 deg
# from every weapon idle's grip (local space): blending across ~180 deg flips the short way round from frame to frame,
# a near full turn. 0.35 s starts it at frame ~40 (<= 100 deg from any rifle / pistol / shotgun idle)
for _m in (mp, mpt):
    _m.pins["BlendOutTime"].extra = 'DefaultValue="0.350000",'
g.link(self_get("TouchAsset", "object", X1 + 2550, Y1 - 300, sub=ANIMSEQB), mpt["Asset"])
g.link(blr["then"], mpt["execute"])
g.link(bdt3["then"], mpt["execute"])
sgm_t = set_from("GrabMontage", "object", X1 + 3100, Y1 - 450, mpt["ReturnValue"], "our montage", sub=MONT)
ses_t = self_set("GrabBH", "bool", X1 + 3400, Y1 - 450, "", default="false")
ses_t2 = self_set("SegStart", "real", X1 + 3700, Y1 - 450, "", default="0.0", subcat="double")
chain(mpt, sgm_t, ses_t, ses_t2)
_mpk = member_call(ANIMI, "PlaySlotAnimationAsDynamicMontage", X1 + 2750, Y1 + 750, anim, "build 30: the use pose (our own: the vodka use's first frame, the player's camera)", [
    ("Asset", "object", dict(sub=ANIMSEQB, extra='DefaultObject="/ImmersiveLooting/Runtime/AS_ImmLoot_PickPose.AS_ImmLoot_PickPose",')),
    ("SlotNodeName", "name", dict(extra='DefaultValue="MainActionSlot",')),
    ("BlendInTime", "real", dict(subcat="float", extra='DefaultValue="0.150000",')),
    ("BlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.250000",')),
    ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",')),
    ("LoopCount", "int", dict(extra='DefaultValue="1",')),
    ("BlendOutTriggerTime", "real", dict(subcat="float", extra='DefaultValue="-1.000000",')),
    ("InTimeToStartMontageAt", "real", dict(subcat="float", extra='DefaultValue="0.000000",')),
    ("ReturnValue", "object", dict(sub=MONT, out=True))])
# (not paused: a paused montage may not blend in; the pose is constant for 3 s and is stopped at the end)
_bstc = branch(X1 + 2600, Y1 + 500, "build 41: standing? (else the crouch table)", self_get("AimStand", "bool", X1 + 2400, Y1 + 600))
g.link(bst["else"], _bstc["execute"])
g.link(_bstc["then"], mpb["execute"])
g.link(_bstc["else"], mpbc["execute"])   # build 32 (tester: "forget it, this approach isn't working"): back to build 26's pickup
_spm = set_from("UseMont", "object", X1 + 3350, Y1 + 750, _mpk["ReturnValue"], "the held pose", sub=MONT)
chain(_mpk, _spm, self_set("UseMode", "bool", X1 + 3650, Y1 + 750, "", default="true"), self_set("PickUse", "bool", X1 + 3950, Y1 + 750, "a pickup in the use pose", default="true"),
      self_set("UseGrabbed", "bool", X1 + 4250, Y1 + 750, "", default="false"),
      set_from("UsePausedAt", "real", X1 + 4550, Y1 + 750, now(X1 + 4400, Y1 + 950), "", subcat="double"), inc("NPickUse", X1 + 4850, Y1 + 750, "count (probe)"))
_pk_last = [n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]
sgm_a = set_from("GrabMontage", "object", X1 + 3100, Y1 - 50, mp["ReturnValue"], "our montage", sub=MONT)
sgm_b = set_from("GrabMontage", "object", X1 + 3100, Y1 + 350, mpb["ReturnValue"], "our montage", sub=MONT)
#   build 17: the table for this use animation, by name (AS_ImmLoot_<montage name>, else AS_ImmLoot_UseAny)
SOPS = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.SoftObjectPath'\""
UX, UY = X1 + 2450, Y1 - 1700


def _load_by_path(x, y, path_pin, comment):
    mk = lib_pure(KSL, "KismetSystemLibrary", "MakeSoftObjectPath", x, y + 300, [("PathString", "string"), ("ReturnValue", "struct", dict(sub=SOPS, out=True))])
    g.link(path_pin, mk["PathString"])
    cv = lib_pure(KSL, "KismetSystemLibrary", "Conv_SoftObjPathToSoftObjRef", x + 250, y + 300,
                  [("SoftObjectPath", "struct", dict(sub=SOPS)), ("ReturnValue", "softobject", dict(sub=OBJ, out=True))])
    cv.pins["SoftObjectPath"].ref = True
    cv.pins["SoftObjectPath"].const = True
    g.link(mk["ReturnValue"], cv["SoftObjectPath"])
    ld = lib_call(KSL, "LoadAsset_Blocking", x + 300, y, comment, [("Asset", "softobject", dict(sub=OBJ)), ("ReturnValue", "object", dict(sub=OBJ, out=True))],
                  "/Script/Engine.Default__KismetSystemLibrary")
    g.link(cv["ReturnValue"], ld["Asset"])
    return ld


def _concat(x, y, a, b_lit=None, b=None, a_lit=None):
    n = lib_pure(KSTR, "KismetStringLibrary", "Concat_StrStr", x, y,
                 [("A", "string", dict(extra=f'DefaultValue="{a_lit}",' if a_lit is not None else "")),
                  ("B", "string", dict(extra=f'DefaultValue="{b_lit}",' if b_lit is not None else "")), ("ReturnValue", "string", dict(out=True))])
    if a is not None:
        g.link(a, n["A"])
    if b is not None:
        g.link(b, n["B"])
    return n["ReturnValue"]


_un = lib_pure(KSL, "KismetSystemLibrary", "GetObjectName", UX - 600, UY + 450, [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
g.link(self_get("UseMont", "object", UX - 800, UY + 450, sub=MONT), _un["Object"])
_p1 = _concat(UX - 400, UY + 450, None, a_lit="/ImmersiveLooting/Runtime/Use/AS_ImmLoot_", b=_un["ReturnValue"])
_p2 = _concat(UX - 250, UY + 520, _p1, b_lit=".AS_ImmLoot_")
_p3 = _concat(UX - 100, UY + 590, _p2, b=_un["ReturnValue"])
# v1.1.1: build 28's SelectString (picking AS_ImmLoot_PickReach for its use-pose pickups) named KismetStringLibrary,
# which has no SelectString (it is in KismetMathLibrary): the paste dropped the node, the path was empty, and every hold
# to use since build 28 played AS_ImmLoot_UseAny instead of the item's own table (v1.1.0: the hand reached off screen).
# Back to the checkpoint-holduse wiring (the use-pose pickups are gone).
_ld1 = _load_by_path(UX, UY, _p3, "this use animation's table")
g.link(_bu3["then"], _ld1["execute"])
g.link(_pk_last["then"], _ld1["execute"])   # build 28: the pickup goes the use reach's way
_anyp = lib_pure(KSTR, "KismetStringLibrary", "Concat_StrStr", UX + 200, UY + 700,
                 [("A", "string", dict(extra='DefaultValue="/ImmersiveLooting/Runtime/Use/AS_ImmLoot_UseAny",')),
                  ("B", "string", dict(extra='DefaultValue=".AS_ImmLoot_UseAny",')), ("ReturnValue", "string", dict(out=True))])
_ld2 = _load_by_path(UX + 400, UY, _anyp["ReturnValue"], "the fallback table (any other use animation)")
g.link(_ld1["then"], _ld2["execute"])
_selu = kml("SelectObject", UX + 800, UY + 300, [("A", "object", dict(sub=OBJ)), ("B", "object", dict(sub=OBJ)),
                                                ("bSelectA", "bool", dict(extra='DefaultValue="false",')), ("ReturnValue", "object", dict(sub=OBJ, out=True))])
g.link(_ld1["ReturnValue"], _selu["A"])
g.link(_ld2["ReturnValue"], _selu["B"])
g.link(is_valid(UX + 600, UY + 450, _ld1["ReturnValue"]), _selu["bSelectA"])
_cu = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), UX + 1000, UY, "an animation", ["TargetType=" + ANIMSEQB]))
_cu.pin("CastFailed", "exec", out=True)
_cu.pin("Object", "object", sub=OBJ)
_cu.pin("AsAnim Sequence Base", "object", sub=ANIMSEQB, out=True)
_cu.pin("bSuccess", "bool", out=True)
g.link(_selu["ReturnValue"], _cu["Object"])
g.link(_ld2["then"], _cu["execute"])
mpu = play_grab(UX + 1350, UY, GRAB_SEQ_BH, "our use reach: FullBody (after every arm layer and IK), additive on the left arm only")
mpu.pins["Asset"].extra = ""
mpu.pins["SlotNodeName"].extra = 'DefaultValue="FullBody",'
mpu.pins["BlendInTime"].extra = 'DefaultValue="0.001000",'   # build g (was 0.05: "the arm disappears for a frame and swaps" after a loot-window use; a segment's frame 0 is no change, so a hold to use loses nothing)
mpu.pins["BlendOutTime"].extra = 'DefaultValue="0.250000",'
g.link(_cu["AsAnim Sequence Base"], mpu["Asset"])
g.link(_cu["then"], mpu["execute"])
sgm_u = set_from("GrabMontage", "object", UX + 1700, UY, mpu["ReturnValue"], "our montage", sub=MONT)
g.link(mpu["then"], sgm_u["execute"])
_cuf = inc("NUseNoTable", UX + 1350, UY + 350, "no table (probe)")
g.link(_cu["CastFailed"], _cuf["execute"])
ses_a = self_set("GrabBH", "bool", X1 + 3400, Y1 - 50, "", default="false")
ses_a2 = self_set("SegStart", "real", X1 + 3700, Y1 - 50, "", default="0.0", subcat="double")
ses_b = self_set("GrabBH", "bool", X1 + 3400, Y1 + 350, "", default="true")
chain(mp, sgm_a, ses_a, ses_a2)
chain(mpb, sgm_b, ses_b, sss)
_sgmc = set_from("GrabMontage", "object", X1 + 3100, Y1 + 650, mpbc["ReturnValue"], "our montage (crouched)", sub=MONT)
g.link(mpbc["then"], _sgmc["execute"])
g.link(_sgmc["then"], ses_b["execute"])
g.link(seg_start, mpbc["InTimeToStartMontageAt"])
g.link(sgm_u["then"], ses_b["execute"])
g.link(seg_start, mpu["InTimeToStartMontageAt"])
srs = set_from("ReachStart", "real", X1 + 2800, Y1 + 250, now(X1 + 2650, Y1 + 450), "reach started", subcat="double")
srg = self_set("Reaching", "bool", X1 + 3100, Y1 + 250, "", default="true")
nr = inc("NReaches", X1 + 3400, Y1 + 250, "count reaches")
g.link(ses_a2["then"], srs["execute"])
g.link(ses_t2["then"], srs["execute"])
g.link(sss["then"], srs["execute"])
chain(srs, srg, nr)
#   1.1.2: the use reach after an item used from the loot window starts with the hand out at the body / stash, where
#   our touch held it (tester: "the hand stays reaching out, then the use plays with no tween"): from its grab frame
_blfg = branch(X1 + 3700, Y1 + 250, "1.1.2: our use reach after a loot touch? from its grab frame (the hand is out there)", self_get("LootFromGrab", "bool", X1 + 3500, Y1 + 400))
g.link(nr["then"], _blfg["execute"])
_msfg = member_call(ANIMI, "Montage_SetPosition", X1 + 4000, Y1 + 250, anim, "at the grab frame", [
    ("Montage", "object", dict(sub=MONT)), ("NewPosition", "real", dict(subcat="float"))])
g.link(self_get("GrabMontage", "object", X1 + 3800, Y1 + 400, sub=MONT), _msfg["Montage"])
g.link(d_op("Add_DoubleDouble", X1 + 3800, Y1 + 500, self_get("SegStart", "real", X1 + 3600, Y1 + 500, subcat="double"), b_const="0.45"), _msfg["NewPosition"])
g.link(_blfg["then"], _msfg["execute"])
chain(_msfg, set_from("ReachStart", "real", X1 + 4300, Y1 + 250,
                      d_op("Subtract_DoubleDouble", X1 + 4200, Y1 + 450, now(X1 + 4000, Y1 + 450),
                           d_op("Divide_DoubleDouble", X1 + 4000, Y1 + 550, None, a_const="0.45", b=self_get("PlayRate", "real", X1 + 3800, Y1 + 600, subcat="double"))),
                      "as if started 0.45 s (montage) ago: the item is in the hand", subcat="double"),
      self_set("LootFromGrab", "bool", X1 + 4600, Y1 + 250, "", default="false"))
#   1.1.2 (tester: "an optional MCM toggle, on by default, that uses the bag animation (like opening the player's
#   inventory) when looting bodies and stashes instead of the hand going out"): the game's own inventory animation
#   (make_bag_seq: AS_ImmLoot_BagIn / BagOut = the player's MG_fp_backpack_inventory In / Out with a HandIK off / on
#   and left_hand_curve) in MainActionSlot, and the backpack mesh (SK_bpa_pla_01, a first-person "_fov" material)
#   attached at the player mesh's origin playing the bag's own In / Out (its root is keyed in the player's component
#   space). Both at rate 1, started on the same tick; the In is held at 0.6 s like the touch (the window opens), the
#   Out plays after the window. A weapon in hand goes where the animation keys jnt_weapon: behind the back.
BAG_IN = "/ImmersiveLooting/Runtime/AS_ImmLoot_BagIn.AS_ImmLoot_BagIn"
BAG_OUT = "/ImmersiveLooting/Runtime/AS_ImmLoot_BagOut.AS_ImmLoot_BagOut"
BAG_MESH = "/Game/_STALKER2/SkeletalMeshes/player/sel/sel_07/SK_bpa_pla_01.SK_bpa_pla_01"
BAG_ANIM_IN = "/Game/_STALKER2/Animations/item/bpa/AnimSequences/AS_backpack_fp_inventory_in.AS_backpack_fp_inventory_in"
BAG_ANIM_OUT = "/Game/_STALKER2/Animations/item/bpa/AnimSequences/AS_backpack_fp_inventory_out.AS_backpack_fp_inventory_out"
ANIMASSET = cls("/Script/Engine.AnimationAsset")
bag_actor = lambda x, y: self_get("BagActor", "object", x, y, sub=SKA)
bag_comp = lambda x, y: other_get(SKA, "SkeletalMeshComponent", "object", x, y, bag_actor(x - 200, y), sub=SKC)


def play_bag(x, y, asset, comment, blend_in, blend_out):
    return member_call(ANIMI, "PlaySlotAnimationAsDynamicMontage", x, y, anim, comment, [
        ("Asset", "object", dict(sub=ANIMSEQB, extra=f'DefaultObject="{asset}",')),
        ("SlotNodeName", "name", dict(extra='DefaultValue="MainActionSlot",')),
        ("BlendInTime", "real", dict(subcat="float", extra=f'DefaultValue="{blend_in:.6f}",')),
        ("BlendOutTime", "real", dict(subcat="float", extra=f'DefaultValue="{blend_out:.6f}",')),
        ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",')),
        ("LoopCount", "int", dict(extra='DefaultValue="1",')),
        ("BlendOutTriggerTime", "real", dict(subcat="float", extra='DefaultValue="-1.000000",')),
        ("InTimeToStartMontageAt", "real", dict(subcat="float", extra='DefaultValue="0.000000",')),
        ("ReturnValue", "object", dict(sub=MONT, out=True))])


def bag_anim(x, y, asset, comment):
    return member_call(SKC, "PlayAnimation", x, y, bag_comp(x - 200, y + 200), comment, [
        ("NewAnimToPlay", "object", dict(sub=ANIMASSET, extra=f'DefaultObject="{asset}",')), B("bLooping")])


BX, BY = X1 + 2300, Y1 - 2400
g.box("EdGraphNode_Comment_942", BX - 80, BY - 200, 5200, 900, "Bag looting: the inventory's bag animation instead of the hand (MCM Body / Stash looting = Backpack)")
#   1.3.1 MCM dropdowns: a body with "Body looting" = Backpack (2), a stash with "Stash looting" = Backpack (1)
_bgb = kml("EqualEqual_IntInt", BX - 500, BY + 270, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="2",')), RB])
g.link(self_get("BodyMode", "int", BX - 700, BY + 270), _bgb["A"])
_bgt = kml("EqualEqual_IntInt", BX - 500, BY + 340, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="1",')), RB])
g.link(self_get("StashMode", "int", BX - 700, BY + 340), _bgt["A"])
_bgs = {"ReturnValue": b_or(BX - 300, BY + 270, b_and(BX - 400, BY + 230, self_get("TouchIsBody", "bool", BX - 600, BY + 200), _bgb["ReturnValue"]),
                            b_and(BX - 400, BY + 330, b_not(BX - 500, BY + 400, self_get("TouchIsBody", "bool", BX - 700, BY + 400)), _bgt["ReturnValue"]))}
bbag = branch(BX, BY, "a body / stash, the bag setting on? the bag comes out (else the hand)",
              b_and(BX - 100, BY + 200, self_get("LootReach", "bool", BX - 300, BY + 200), _bgs["ReturnValue"]))
#   (n2: the both-hands branch comes first: see below)
g.link(bbag["else"], bst["execute"])
#   build k (tester: "the bag animation as a layer that only moves the arms, over Skif's own posture"; builds a-j: over
#   MainActionSlot / FullBody / the game's backpack posture: camera taken, arms wrong, a crash): the copied In / Idle /
#   Out in montage assets AM_ImmLoot_Bag* with two slot tracks, LeftHand and RightHand (left_hand_blend_mask /
#   right_hand_blend_mask: shoulder to fingers, local space), played with Montage_Play(bStopAllMontages false): the
#   arms carry the game's bag animation from Skif's own shoulders (the left hand holds the bag, the right hand goes in:
#   they move together), the camera, the look, the spine and the legs stay the game's. A weapon in hand is hidden for
#   the bag (build m; builds k-l put it away: bare-hands posture, arms not following the view) and shown again after (6d).
AM_BAG_IN = "/ImmersiveLooting/Runtime/AM_ImmLoot_BagIn.AM_ImmLoot_BagIn"
AM_BAG_IDLE = "/ImmersiveLooting/Runtime/AM_ImmLoot_BagIdle.AM_ImmLoot_BagIdle"
AM_BAG_OUT = "/ImmersiveLooting/Runtime/AM_ImmLoot_BagOut.AM_ImmLoot_BagOut"


def grab_is(x, y, asset, comment="our montage"):
    s = self_set("GrabMontage", "object", x, y, comment, sub=MONT)
    s.pins["GrabMontage"].extra = f'DefaultObject="{asset}",'
    return s


def stop_mont(x, y, asset, blend, comment):
    n = member_call(ANIMI, "Montage_Stop", x, y, anim, comment, [
        ("InBlendOutTime", "real", dict(subcat="float", extra=f'DefaultValue="{blend:.6f}",')),
        ("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{asset}",'))])
    n.pins["Montage"].const = True
    return n


_bbw = branch(BX + 150, BY - 300, "a weapon in hand? hidden for the bag (build m: it stays in the hands, so Skif keeps the weapon posture, which turns the arms with the view)", obj_q("HasItemInMainHand", BX, BY - 150, as_pc))
g.link(bbag["then"], _bbw["execute"])
_sbw1 = self_set("BagWeapon", "bool", BX + 450, BY - 300, "show it after the bag", default="true")
#   (build l probe: RemoveWeaponFromHands put Skif in the bare-hands posture: the arms did not follow the view, the right
#   hand left the bag; and EquipLastHeldItem after it left the first weapon key press dead)
_whm = member_pure(OBJC, "GetWeaponInHandsMeshComponent", BX + 100, BY - 600, as_pc, [("ReturnValue", "object", dict(sub=SKC, out=True))])["ReturnValue"]
_whd = member_call(SC_, "SetHiddenInGame", BX + 300, BY - 450, _whm, "the weapon hidden (still in the hands)", [B("NewHidden", "true"), B("bPropagateToChildren", "true")])
chain(_bbw, _whd, _sbw1)


def stop_replay(x, y, before):
    """n2f: our replay of the game's equip still playing (the press came during the last bag's / pat's draw)? it stops
    (0.1 s) and its weapon show is cancelled: the bag / pat hides the weapon and replays the draw after. Inserted in
    front of `before` (its incoming exec links move to the check)."""
    b = branch(x, y, "n2f: our equip replay is what plays? it stops", _replay_ours(x - 150, y + 200))
    for l_ in list(before["execute"].links):
        before["execute"].links.remove(l_); l_.links.remove(before["execute"])
        g.link(l_, b["execute"])
    ms = member_call(ANIMI, "Montage_Stop", x + 300, y, anim, "out (0.1 s)", [
        ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.100000",')), ("Montage", "object", dict(sub=MONT))])
    ms.pins["Montage"].const = True
    g.link(self_get("LastEquipMont", "object", x + 100, y + 200, sub=MONT), ms["Montage"])
    sw = self_set("WeaponShowTick", "int", x + 600, y, "no weapon show", default="0")
    chain(b, ms, sw)
    g.link(sw["then"], before["execute"])
    g.link(b["else"], before["execute"])


stop_replay(BX - 300, BY - 800, _bbw)
_sbw2 = self_set("BagWeapon", "bool", BX + 450, BY - 150, "empty hands", default="false")
g.link(_bbw["else"], _sbw2["execute"])
mbi = montage_play(BX + 600, BY, anim, AM_BAG_IN, None, "the bag comes out: the arms (LeftHand + RightHand)")
g.link(_sbw1["then"], mbi["execute"])
BAG_PITCH = "/ImmersiveLooting/Runtime/AS_ImmLoot_BagPitchFix.AS_ImmLoot_BagPitchFix"
#   build m, empty hands: make_bag_seq build_pitch_fix (the arms turn with the view, as the game's bag posture does),
#   FullBody, paused, its frame set every tick from the view pitch (6c)
_mpf = play_bag(BX + 600, BY - 150, BAG_PITCH, "empty hands: the arms turn with the view (pose table, FullBody)", 0.15, 0.25)
_mpf.pins["SlotNodeName"].extra = 'DefaultValue="FullBody",'
_ppf = member_call(ANIMI, "Montage_Pause", BX + 900, BY - 150, anim, "held; its frame set from the view", [("Montage", "object", dict(sub=MONT))])
g.link(_mpf["ReturnValue"], _ppf["Montage"])
chain(_sbw2, _mpf, set_from("PitchFixMont", "object", BX + 1200, BY - 150, _mpf["ReturnValue"], "the pose table", sub=MONT), _ppf)
g.link(_ppf["then"], mbi["execute"])
_bsp = exec_pins(Node(g, BG + "K2Node_SpawnActorFromClass", nm("K2Node_SpawnActorFromClass"), BX + 1500, BY, "the backpack"))
_bsp.pin("Class", "class", sub=ACTOR, extra=f'DefaultObject="{SKA.split(chr(39))[1]}",')
_bsp.pin("ReturnValue", "object", sub=SKA, out=True)
_bsp.pin("WorldContextObject", "object", sub=OBJ, hidden=True)
_bsp.pin("SpawnTransform", "struct", sub=XFORM)
_bsp.pin("CollisionHandlingOverride", "byte", sub=EN("/Script/Engine.ESpawnActorCollisionHandlingMethod"), extra='DefaultValue="AlwaysSpawn",')
_bsp.pin("TransformScaleMethod", "byte", sub=EN("/Script/Engine.ESpawnActorScaleMethod"), adv=True, extra='DefaultValue="MultiplyWithRoot",')
_bsp.pin("Owner", "object", sub=ACTOR, adv=True)
g.link(member_pure(ACTOR, "GetTransform", BX + 1300, BY + 300, self_ref(BX + 1100, BY + 350), [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"],
       _bsp["SpawnTransform"])
_bmob = member_call(SC_, "SetMobility", BX + 2100, BY, bag_comp(BX + 1900, BY + 200), "movable",
                    [("NewMobility", "byte", dict(sub=EN("/Script/Engine.EComponentMobility"), extra='DefaultValue="Movable",'))])
_bmsh = member_call(SKC, "SetSkeletalMeshAsset", BX + 2400, BY, bag_comp(BX + 2200, BY + 200), "the player's backpack",
                    [("NewMesh", "object", dict(sub=SKMESH, extra=f'DefaultObject="{BAG_MESH}",'))])
_bcol = member_call(PRIM, "SetCollisionEnabled", BX + 2700, BY, bag_comp(BX + 2500, BY + 200), "no collision",
                    [("NewType", "byte", dict(sub=EN("/Script/Engine.ECollisionEnabled"), extra='DefaultValue="NoCollision",'))])
# build b ("still no bag"; probe: the backpack sat still 61 cm ahead, 81 cm below the view): the bag animations lock
# their root to the reference pose (bForceRootLock), so the keyed root motion never applies. Their root follows the
# player's jnt_l_weapon exactly (rotated -90 deg about X = the root's own reference rotation, every frame of In / Out):
# the game holds the bag in the left hand. Attached there.
_batt = member_call(ACTOR, "K2_AttachToComponent", BX + 3000, BY, bag_actor(BX + 2800, BY + 200), "in the left hand (jnt_l_weapon)", [
    ("Parent", "object", dict(sub=SC_)), ("SocketName", "name", dict(extra='DefaultValue="jnt_l_weapon",')),
    ("LocationRule", "byte", dict(sub=EN("/Script/Engine.EAttachmentRule"), extra='DefaultValue="SnapToTarget",')),
    ("RotationRule", "byte", dict(sub=EN("/Script/Engine.EAttachmentRule"), extra='DefaultValue="SnapToTarget",')),
    ("ScaleRule", "byte", dict(sub=EN("/Script/Engine.EAttachmentRule"), extra='DefaultValue="SnapToTarget",')),
    B("bWeldSimulatedBodies"), RB])
g.link(mesh, _batt["Parent"])


def comp_set(x, y, owner_cls, var, cat, default, comment, sub="None"):
    """A property of the backpack's mesh component (VariableSet on another object)."""
    n = exec_pins(Node(g, BG + "K2Node_VariableSet", nm("K2Node_VariableSet"), x, y, comment,
                       [f'VariableReference=(MemberParent={owner_cls},MemberName="{var}")']))
    n.pin(var, cat, sub=sub, extra=f'DefaultValue="{default}",')
    n.pin("Output_Get", cat, sub=sub, out=True)
    n.pin("self", "object", sub=owner_cls, extra=TGT)
    g.link(bag_comp(x - 200, y + 200), n["self"])
    return n


# build a test ("I don't see a bag, only the hand holding nothing"): a SkeletalMeshActor ticks its pose but refreshes
# its bones only while rendered; posed at the mesh's reference pose (worn on the back, behind the camera) it was never
# rendered, so never posed: bones refreshed always, and the bounds of the player's mesh
_bvb = comp_set(BX + 2850, BY + 400, cls("/Script/Engine.SkinnedMeshComponent"), "VisibilityBasedAnimTickOption", "byte",
                "AlwaysTickPoseAndRefreshBones", "posed even when not drawn", sub=EN("/Script/Engine.EVisibilityBasedAnimTickOption"))
_bab = comp_set(BX + 3150, BY + 400, SC_, "bUseAttachParentBound", "bool", "true", "the player mesh's bounds (never culled)")
#   build o (tester: "the backpack pops for a frame or two on the left" at the open; probe: the first frame it sat 92 cm
#   left, 106 cm below the view = its reference pose before its animation and the arms' first evaluated frame): hidden
#   for its first 3 ticks (6c shows it; In starts below the view anyway)
_bhid = member_call(ACTOR, "SetActorHiddenInGame", BX + 3150, BY - 200, bag_actor(BX + 2950, BY - 100), "hidden for its first frames", [B("bNewHidden", "true")])
_bsht = kml("Add_IntInt", BX + 3300, BY - 100, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="3",')), ("ReturnValue", "int", dict(out=True))])
g.link(self_get("NTicks", "int", BX + 3100, BY - 50), _bsht["A"])
_bshs = set_from("BagShowTick", "int", BX + 3450, BY - 200, _bsht["ReturnValue"], "shown from this tick")
_bold = branch(BX + 1400, BY - 400, "1.3.1: a bag still out from the last body? it goes first", is_valid(BX + 1300, BY - 250, bag_actor(BX + 1100, BY - 250)))
_boldd = member_call(ACTOR, "K2_DestroyActor", BX + 1700, BY - 400, bag_actor(BX + 1500, BY - 250), "the old bag")
chain(mbi, grab_is(BX + 600, BY, AM_BAG_IN),
      self_set("GrabBH", "bool", BX + 900, BY, "", default="false"),
      self_set("SegStart", "real", BX + 1200, BY, "", default="0.0", subcat="double"),
      self_set("BagAdd", "bool", BX + 1350, BY, "the bag over the weapon's stance", default="false"),
      _bold)
#   1.3.1 (Nexus, MonaPona: "after looting multiple bodies very quickly the backpack glitched out and never went back
#   to normal"; picture: the bag fills the bottom of the view with the rifle on it): a bag started while the last one was
#   still on its way out replaced BagActor and the old bag stayed in the left hand for good. The old one goes first.
g.link(_bold["then"], _boldd["execute"])
g.link(_boldd["then"], _bsp["execute"])
g.link(_bold["else"], _bsp["execute"])
chain(_bsp, set_from("BagActor", "object", BX + 1800, BY, _bsp["ReturnValue"], "the backpack", sub=SKA),
      _bmob, _bmsh, _bcol, _batt, _bvb, _bab, _bhid, _bshs, bag_anim(BX + 3300, BY, BAG_ANIM_IN, "the bag's half"),
      self_set("BagMode", "bool", BX + 3600, BY, "bag looting", default="true"),
      set_from("BagAt", "real", BX + 3900, BY, now(BX + 3750, BY + 200), "", subcat="double"),
      set_from("ReachStart", "real", BX + 4200, BY, now(BX + 4050, BY + 200), "", subcat="double"),
      inc("NBag", BX + 4500, BY, "count (probe)"))

# ---- n2 (1.3.1; Nexus, Scorpius34: "loot corpses with both hands"; tester: "the right hand goes out the same way the
#      left does, as if patting down and checking the body on the ground"): MCM "Both hands on bodies" (PatLoot, off).
#      AS_ImmLoot_PatTable (make_grab_seq build_pat_table): 75 segments = family (0 rifle stance, 1 pistol, 2 empty
#      hands) x the 25 touch bins, played through AM_ImmLoot_Pat (LeftHand + RightHand slot tracks) from the segment.
#      A weapon is hidden for it (both hands are busy) and drawn again with the game's last equip after it (as the bag);
#      empty hands standing get the bag's pitch fix (the arms turn with the view). ----
AM_PAT = "/ImmersiveLooting/Runtime/AM_ImmLoot_Pat.AM_ImmLoot_Pat"
PX, PY_ = BX, BY - 1500
g.box("EdGraphNode_Comment_960", PX - 80, PY_ - 400, 5600, 1100, "Both hands on bodies (MCM Body looting = Both hands): the two-hand pat-down")
_pmb = kml("EqualEqual_IntInt", PX - 300, PY_ + 270, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="1",')), RB])
g.link(self_get("BodyMode", "int", PX - 500, PY_ + 270), _pmb["A"])
bpat = branch(PX, PY_, "n2: a body, the both-hands setting on? both hands pat it down (else the bag / the hand)",
              b_and(PX - 100, PY_ + 200, self_get("LootReach", "bool", PX - 300, PY_ + 200), _pmb["ReturnValue"],
                    self_get("TouchIsBody", "bool", PX - 300, PY_ + 340)))
g.link(bdt3["else"], bpat["execute"])
g.link(bpat["else"], bbag["execute"])
_pwq = member_pure(OBJC, "GetMainHandEquipType", PX - 300, PY_ + 500, as_pc,
                   [("ReturnValue", "byte", dict(sub=EN("/Script/Stalker2.EMainHandEquipmentType"), out=True))])["ReturnValue"]
_pwi = kml("Conv_ByteToInt", PX - 100, PY_ + 500, [("InByte", "byte", dict(extra='DefaultValue="0",')), ("ReturnValue", "int", dict(out=True))])
g.link(_pwq, _pwi["InByte"])
_parm = obj_q("HasItemInMainHand", PX - 100, PY_ + 600, as_pc)
#   family: 0 rifle stance, 1 pistol, 2 empty hands
_pfam1 = kml("SelectInt", PX + 100, PY_ + 500, [("A", "int", dict(extra='DefaultValue="1",')), ("B", "int", dict(extra='DefaultValue="0",')), B("bPickA"),
                                                ("ReturnValue", "int", dict(out=True))])
_peqi = kml("EqualEqual_IntInt", PX - 100, PY_ + 700, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="1",')), RB])
g.link(_pwi["ReturnValue"], _peqi["A"])
g.link(_peqi["ReturnValue"], _pfam1["bPickA"])
_pfam = kml("SelectInt", PX + 300, PY_ + 500, [("A", "int"), ("B", "int", dict(extra='DefaultValue="2",')), B("bPickA"), ("ReturnValue", "int", dict(out=True))])
g.link(_pfam1["ReturnValue"], _pfam["A"])
g.link(_parm, _pfam["bPickA"])
_pidx = kml("Add_IntInt", PX + 500, PY_ + 500, [("A", "int"), ("B", "int"), ("ReturnValue", "int", dict(out=True))])
_pmul = kml("Multiply_IntInt", PX + 400, PY_ + 600, [("A", "int"), ("B", "int", dict(extra='DefaultValue="25",')), ("ReturnValue", "int", dict(out=True))])
g.link(_pfam["ReturnValue"], _pmul["A"])
g.link(_pmul["ReturnValue"], _pidx["A"])
g.link(self_get("TouchBin", "int", PX + 300, PY_ + 700), _pidx["B"])
_pcv = kml("Conv_IntToDouble", PX + 600, PY_ + 600, [("InInt", "int"), RD])
g.link(_pidx["ReturnValue"], _pcv["InInt"])
_pseg = d_op("Multiply_DoubleDouble", PX + 700, PY_ + 500, _pcv["ReturnValue"], b_const="1.7")
_pbw = branch(PX + 300, PY_ - 300, "n2: a weapon in hand? hidden (both hands are busy), drawn again after", _parm)
g.link(bpat["then"], _pbw["execute"])
stop_replay(PX - 200, PY_ - 800, _pbw)
_pwm = member_pure(OBJC, "GetWeaponInHandsMeshComponent", PX + 300, PY_ - 500, as_pc, [("ReturnValue", "object", dict(sub=SKC, out=True))])["ReturnValue"]
_phd = member_call(SC_, "SetHiddenInGame", PX + 600, PY_ - 300, _pwm, "hidden (still in the hands)", [B("NewHidden", "true"), B("bPropagateToChildren", "true")])
_psw1 = self_set("BagWeapon", "bool", PX + 900, PY_ - 300, "show it after", default="true")
chain(_pbw, _phd, _psw1)
_psw2 = self_set("BagWeapon", "bool", PX + 600, PY_ - 150, "empty hands", default="false")
g.link(_pbw["else"], _psw2["execute"])
_mpf2 = play_bag(PX + 900, PY_ - 150, BAG_PITCH, "empty hands: the arms turn with the view (the bag's pitch fix)", 0.15, 0.25)
_mpf2.pins["SlotNodeName"].extra = 'DefaultValue="FullBody",'
_ppf2 = member_call(ANIMI, "Montage_Pause", PX + 1500, PY_ - 150, anim, "held; its frame from the view", [("Montage", "object", dict(sub=MONT))])
g.link(_mpf2["ReturnValue"], _ppf2["Montage"])
chain(_psw2, _mpf2, set_from("PitchFixMont", "object", PX + 1200, PY_ - 150, _mpf2["ReturnValue"], "the pose table", sub=MONT), _ppf2)
_mpp = montage_play(PX + 1800, PY_, anim, AM_PAT, None, "both hands: the segment for the family and the bin (rate 0.78: slower, eased pats)")
_mpp.pins["InPlayRate"].extra = 'DefaultValue="0.780000",'   # n2c
g.link(_pseg, _mpp["InTimeToStartMontageAt"])
g.link(_psw1["then"], _mpp["execute"])
g.link(_ppf2["then"], _mpp["execute"])
chain(_mpp, grab_is(PX + 2100, PY_, AM_PAT, "our montage"),
      self_set("GrabBH", "bool", PX + 2400, PY_, "", default="false"),
      set_from("SegStart", "real", PX + 2700, PY_, _pseg, "the segment's start", subcat="double"),
      self_set("PatMode", "bool", PX + 3000, PY_, "both hands", default="true"),
      inc("NPat", PX + 3300, PY_, "count (probe)"))
g.link([n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"], srs["execute"])
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
_sfh = self_set("FlyHeld", "bool", FX + 600, FY - 200, "", default="false")
bx2 = kml("BreakTransform", FX + 700, FY + 500, [("InTransform", "struct", dict(sub=XFORM)),
                                                ("Location", "struct", dict(sub=VEC, out=True)),
                                                ("Rotation", "struct", dict(sub=ROT, out=True)),
                                                ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(self_get("ItemXf", "struct", FX + 500, FY + 500, sub=XFORM), bx2["InTransform"])
sff = set_from("FlyFrom", "struct", FX + 900, FY, bx2["Location"], "from where the item was", sub=VEC)
chain(sfs, sfd, sfa, _sfh, sff)
bsm = branch(FX + 1200, FY, "static mesh item?", is_valid(FX + 1050, FY + 200, self_get("ItemMesh", "object", FX + 850, FY + 200, sub=SM)))
g.link(sff["then"], bsm["execute"])


def spawn_copy(x, y, actor_cls, comp_var, comment, var="Fly", count="NFly"):
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
    sf = set_from(var, "object", x + 1250, y, sp["ReturnValue"], "the flying copy" if var == "Fly" else "the stand-in copy", sub=ACTOR)
    nf = inc(count, x + 1550, y, "count copies")
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
               self_get("LookComp", "object", X5 + 700, Y5 - 50, sub=PRIM),
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
chain(mres, mrate, rv1, rv2, set_from("BackAt", "real", X5 + 3000, Y5 + 3900, now(X5 + 2850, Y5 + 4100), "on the way back since", subcat="double"))
bfw =branch(X5 + 1650, Y5 + 3700, "weapon in hand? (the rifle grab plays on: hand to the chest, back onto the grip)",
             b_not(X5 + 1550, Y5 + 3600, self_get("GrabBH", "bool", X5 + 1350, Y5 + 3600)))
g.link(bfw["else"], mres["execute"])


def reach_over(x, y, exec_in, comment="reach over"):
    """Our reach / touch / bag is over: no hold, no return, no hand-back recovery (step 6)."""
    ns = [self_set(v, "bool", x + 300 * k, y, comment if k == 0 else "", default="false")
          for k, v in enumerate(("Reaching", "LootReach", "LootPaused", "LootReverse"))]
    ns.append(self_set("TouchState", "int", x + 1200, y, "idle", default="0"))
    chain(*ns)
    g.link(exec_in, ns[0]["execute"])
    return ns[-1]


#   n2f: a skipped press (sprint, aim, a game action...) on a body / stash / door: no touch, the window is the game's
_bsk = branch(X1 + 2150, Y1 - 450, "n2f: a skipped touch? its state cleared (no window retries, no stale wait)", self_get("LootReach", "bool", X1 + 1950, Y1 - 300))
g.link(_buw["else"], _bsk["execute"])
reach_over(X1 + 2450, Y1 - 450, _bsk["then"], "touch skipped")


def bag_out(x, y, exec_in):
    """1.1.2: the bag goes back (Out), player and backpack together."""
    mbo = montage_play(x + 300, y, anim, AM_BAG_OUT, None, "the bag goes back: the arms")
    ban = bag_anim(x + 900, y, BAG_ANIM_OUT, "the bag's half")
    chain(stop_mont(x, y, AM_BAG_IDLE, 0.1, "the idle goes"), stop_mont(x + 150, y + 200, AM_BAG_IN, 0.1, "(or the In, without a window)"), mbo, grab_is(x + 600, y, AM_BAG_OUT), ban)
    g.link(exec_in, [n_ for n_ in g.nodes if n_.comment == "the idle goes"][-1]["execute"])
    chain(ban, self_set("LootPaused", "bool", x + 900, y, "", default="false"),
          self_set("LootReach", "bool", x + 1200, y, "", default="false"),
          self_set("TouchState", "int", x + 1500, y, "idle", default="0"),
          set_from("BackAt", "real", x + 1800, y, now(x + 1650, y + 200), "on the way back since", subcat="double"))


# 1.1.2 (Nexus, Tim0st; tester: "it happens when the player right clicks an item and uses it from the loot window: when
# the window closes our return animation plays, and during it the hand inverts, just before the vanilla use"): the
# game starts the item's use (MainActionSlot) as the window goes; our return (LeftHand after MainActionSlot, or the
# empty-hands FullBody additive) then posed the arm over the use. A game montage started since the window went = an
# item used from it: ours goes at once, no return, no hand-back recovery (the use animation owns the arms).
_gone = lambda x, y: self_get("InvGoneAt", "real", x, y, subcat="double")
# (game time stands still while the window is open, so a use started from it is stamped at about the window's
# opening: compared with our reach's start, not with the close)
_gis = member_pure(ANIMI, "Montage_GetIsStopped", X5 + 750, Y5 + 5100, anim, [("Montage", "object", dict(sub=MONT)), RB])
_gis.pins["Montage"].const = True
g.link(gm(X5 + 550, Y5 + 5100), _gis["Montage"])
_bagm = lambda x, y: self_get("BagMode", "bool", x, y)
#   ... and it took the arms: an action in MainActionSlot (where our bag plays too) or ours stopped by it
_took = b_or(X5 + 1150, Y5 + 5000,
             b_and(X5 + 1050, Y5 + 5000, _bagm(X5 + 850, Y5 + 5000), _gis["ReturnValue"]),
             b_and(X5 + 1050, Y5 + 5200, b_not(X5 + 950, Y5 + 5200, _bagm(X5 + 750, Y5 + 5200)),
                   b_or(X5 + 950, Y5 + 5300, slot_active(X5 + 750, Y5 + 5300, anim, "MainActionSlot"), _gis["ReturnValue"])))
bused = branch(X5 + 1450, Y5 + 4500, "an item used from the window? (held for us, or a game montage started since our reach and took the arms) ours goes",
               b_or(X5 + 1400, Y5 + 4650, self_get("LootUse", "bool", X5 + 1200, Y5 + 4600), b_and(X5 + 1350, Y5 + 4700, _took,
                     d_op("GreaterEqual_DoubleDouble", X5 + 1150, Y5 + 4700, _gone(X5 + 950, Y5 + 4700),
                          self_get("ReachStart", "real", X5 + 950, Y5 + 4770, subcat="double"), ret=RB),
                     d_op("Greater_DoubleDouble", X5 + 1150, Y5 + 4850, self_get("GameMontageAt", "real", X5 + 950, Y5 + 4850, subcat="double"),
                          self_get("ReachStart", "real", X5 + 950, Y5 + 4920, subcat="double"), ret=RB))))
g.link(brv["then"], bused["execute"])
#   (build a test: the game first lowers the hands ("unequip", ~0.4 s) as the window goes, THEN starts the use) so our
#   touch stays where it is, LootWait: a use starting within 1 s is held for our use reach (step 7, step 6c); none =
#   ours goes then, no return (6c)
chain(bused, self_set("LootWait", "bool", X5 + 1750, Y5 + 4500, "wait for the item's use (1 s)", default="true"),
      set_from("LootWaitAt", "real", X5 + 2050, Y5 + 4500, now(X5 + 1900, Y5 + 4700), "", subcat="double"))
bbo = branch(X5 + 1750, Y5 + 4900, "bag looting? the bag goes back", self_get("BagMode", "bool", X5 + 1550, Y5 + 5050))
g.link(bused["else"], bbo["execute"])
bag_out(X5 + 2050, Y5 + 4900, bbo["then"])
g.link(bbo["else"], bfw["execute"])
mresf = member_call(ANIMI, "Montage_Resume", X5 + 1950, Y5 + 3600, anim, "go on (forward)", [("Montage", "object", dict(sub=MONT))])
mresf.pins["Montage"].const = True
g.link(gm(X5 + 1750, Y5 + 3500), mresf["Montage"])
g.link(bfw["then"], mresf["execute"])
chain(mresf, self_set("LootPaused", "bool", X5 + 2250, Y5 + 3600, "", default="false"),
      self_set("LootReach", "bool", X5 + 2550, Y5 + 3600, "touch over", default="false"),
      self_set("TouchState", "int", X5 + 2850, Y5 + 3600, "idle", default="0"),
      set_from("BackAt", "real", X5 + 3150, Y5 + 3600, now(X5 + 3000, Y5 + 3800), "on the way back since", subcat="double"))
g.link(brv["else"], self_set("LootReach", "bool", X5 + 1800, Y5 + 4200, "nothing out", default="false")["execute"])


# =====================================================================
# v0.2 corpse / stash touch (tester: "the touch should happen before the window opens; when it closes the hand returns")
# The game freezes the world while the loot window is open (probe: 0 ticks/s), so the reach must play before it opens:
#   - looking at a corpse (an Obj that is not alive and has a DeadBody component) or a stash (an item container that is
#     not a loose item): remember its TAP interaction component (DeadBody / ItemContainerInteractionComponent);
#   - the player's interact keys (QueryKeysMappedToAction) are POLLED every tick (WasInputKeyJustPressed / Released):
#     no input mapping context and no input on this actor. 1.0.1a-c: any mapping of the key, consuming or not, hid the
#     game's "hold F" prompt and its carry (native HoldIPU); the game keeps its key untouched now;
#   - pressed: the tap component is switched off (SetInteractionActive false) so the game's own tap does nothing;
#     released within HoldToDrag = a tap: the hand reaches (PendingReach, LootReach), pauses at the touch frame, the
#     component is switched back on and IA_Interact injected: the window opens; held longer = the game's hold (carry a
#     body): nothing of ours, the idle step switches the component back on;
#   - window closed: the hand plays on / back (after-closing steps) and, with a weapon, returns to the grip.
# TouchState: 0 idle, 1 pressed (tap or hold?), 2 reaching, 3 window requested / open.
# =====================================================================
XT, YT = 1200, 16500
g.box("EdGraphNode_Comment_907", XT - 300, YT - 1200, 7200, 4200, "Corpse / stash: catch the interact key, reach out, then open the loot window")
g.box("EdGraphNode_Comment_908", XT - 400, YT + 3500, 7200, 3200, "Our interact key pressed on a corpse / stash: start the reach (or pass the press on)")
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


def tap_active(x, y, on, comment):
    """TapComp.SetInteractionActive(on) if TapComp is valid; returns (entry exec pin, [exit exec pins])."""
    b = branch(x, y, comment, is_valid(x - 150, y + 200, self_get("TapComp", "object", x - 350, y + 200, sub=ICOMP)))
    c = member_call(ICOMP, "SetInteractionActive", x + 300, y, self_get("TapComp", "object", x + 100, y + 200, sub=ICOMP), "",
                    [("bActive", "bool", dict(extra='DefaultValue="%s",' % ("true" if on else "false")))])
    g.link(b["then"], c["execute"])
    return b["execute"], [c["then"], b["else"]]


sqt = sequence(XT, YT, "touch steps", 11)
g.link(sq5["then_4"], sqt["execute"])

#   T0: idle and window closed: is what we look at a corpse / stash? (re-evaluated every tick)
bt0 = branch(XT + 300, YT - 200, "idle, window closed?", b_and(XT + 150, YT, int_eq(XT, YT, tstate(XT - 200, YT), 0),
                                                              b_not(XT, YT + 100, self_get("InvOpen", "bool", XT - 200, YT + 100))))
g.link(sqt["then_0"], bt0["execute"])
sq0 = sequence(XT + 450, YT - 200, "idle steps", 2)
g.link(bt0["then"], sq0["execute"])
#     a) the tap interaction we switched off at a press: back on (every exit of a touch ends here)
boff = branch(XT + 700, YT - 1000, "a tap interaction switched off? back on", self_get("TapOff", "bool", XT + 500, YT - 800))
g.link(sq0["then_0"], boff["execute"])
_e0, _x0 = tap_active(XT + 1000, YT - 1000, True, "")
g.link(boff["then"], _e0)
_so = self_set("TapOff", "bool", XT + 1700, YT - 1000, "", default="false")
for q_ in _x0:
    g.link(q_, _so["execute"])
lo = lambda x, y: self_get("LootObj", "object", x, y, sub=OBJ)
cob = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), XT + 600, YT - 200, "a character?", ["TargetType=" + OBJC]))
cob.pin("CastFailed", "exec", out=True)
cob.pin("Object", "object", sub=OBJ)
cob.pin("AsObj", "object", sub=OBJC, out=True)
cob.pin("bSuccess", "bool", out=True)
g.link(lo(XT + 400, YT), cob["Object"])
# 1.0.1f bisect (tester: no more probe-only runs; the hold on a loose item works, the body carry's prompt stays a dot):
# CORPSE_TOUCH False skips the corpse branch (IsAlive, GetComponentByClass DeadBody, TapComp, pelvis): bodies are
# "something else" = plain vanilla; stashes keep the touch. If the carry returns, the cause is in that branch.
CORPSE_TOUCH = True   # 1.0.1f/g: off made no difference (nor did the whole tick off): the corpse branch is innocent
if CORPSE_TOUCH:
    g.link(sq0["then_1"], cob["execute"])
alive = obj_q("IsAlive", XT + 800, YT + 100, cob["AsObj"])
dbc = member_pure(ACTOR, "GetComponentByClass", XT + 800, YT + 200, cob["AsObj"], [
    ("ComponentClass", "class", dict(sub=ACOMP, extra='DefaultObject="/Script/Stalker2.DeadBody",')),
    ("ReturnValue", "object", dict(sub=ACOMP, out=True))])["ReturnValue"]
_bmo = kml("NotEqual_IntInt", XT + 850, YT + 280, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="3",')), RB])
g.link(self_get("BodyMode", "int", XT + 650, YT + 280), _bmo["A"])
corpse = b_and(XT + 1050, YT + 100, b_not(XT + 950, YT + 50, alive), is_valid(XT + 1000, YT + 200, dbc),
               _bmo["ReturnValue"])   # MCM "Body looting" Off (3) = bodies stay vanilla
sl_c = set_from("Lootable", "bool", XT + 1100, YT - 300, corpse, "a corpse?")
g.link(cob["then"], sl_c["execute"])
#     its tap interaction (DeadBody = "search"; the carry is a separate DeadBodyHoldComponent we never touch)
stc = set_from("TapComp", "object", XT + 1400, YT - 300, member_pure(ACTOR, "GetComponentByClass", XT + 1200, YT - 100, cob["AsObj"], [
    ("ComponentClass", "class", dict(sub=ACOMP, extra='DefaultObject="/Script/Stalker2.DeadBody",')),
    ("ReturnValue", "object", dict(sub=ICOMP, out=True))])["ReturnValue"], "its search interaction", sub=ICOMP)
_stb = set_from("TouchIsBody", "bool", XT + 1250, YT - 450, corpse, "both hands (n2): a body?")
chain(sl_c, _stb, stc)
#     n2h: and its carry (hold) interaction (T10 resets a stale hold)
_shc = set_from("BodyHold", "object", XT + 1700, YT - 300, member_pure(ACTOR, "GetComponentByClass", XT + 1500, YT - 100, cob["AsObj"], [
    ("ComponentClass", "class", dict(sub=ACOMP, extra='DefaultObject="/Script/Stalker2.DeadBodyHoldComponent",')),
    ("ReturnValue", "object", dict(sub=HOLDC, out=True))])["ReturnValue"], "n2h: its carry interaction", sub=HOLDC)
for l_ in list(stc["then"].links):
    stc["then"].links.remove(l_); l_.links.remove(stc["then"])
    g.link(_shc["then"], l_)
g.link(stc["then"], _shc["execute"])
#     1.0.1l's per-body ReturnLeftHandOnItemEnded removed in 1.0.1m (carry still dead with it; back to 1.0.1i, which
#     carried: the reset once per world only)
cic = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), XT + 900, YT + 400, "an item container?",
                     [f"TargetType=\"/Script/CoreUObject.Class'{IIC}'\""]))
cic.pin("CastFailed", "exec", out=True)
cic.pin("Object", "object", sub=OBJ)
cic.pin("AsInteractable Item Container", "object", sub=cls(IIC), out=True)
cic.pin("bSuccess", "bool", out=True)
g.link(lo(XT + 700, YT + 600), cic["Object"])
_stb0 = self_set("TouchIsBody", "bool", XT + 700, YT + 300, "not a body", default="false")
chain(_stb0, cic)
g.link(cob["CastFailed"], _stb0["execute"])
if not CORPSE_TOUCH:
    g.link(sq0["then_1"], cic["execute"])
# the instance name starts with its class name (BP_StaticItemContainer_C_...); a class pin cannot feed GetObjectName
_cn = lib_pure(KSL, "KismetSystemLibrary", "GetObjectName", XT + 1300, YT + 650, [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
g.link(cic["AsInteractable Item Container"], _cn["Object"])


def str_starts(x, y, a, lit):
    n = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "StartsWith", x, y,
                 [("SourceString", "string"), ("InPrefix", "string", dict(extra=f'DefaultValue="{lit}",')),
                  ("SearchCase", "byte", dict(sub=EN("/Script/CoreUObject.ESearchCase"), extra='DefaultValue="IgnoreCase",')), RB])
    g.link(a, n["SourceString"])
    return n["ReturnValue"]


_smo = kml("NotEqual_IntInt", XT + 1700, YT + 820, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="2",')), RB])
g.link(self_get("StashMode", "int", XT + 1500, YT + 820), _smo["A"])
stash = b_and(XT + 1850, YT + 700, b_not(XT + 1700, YT + 700, b_or(XT + 1600, YT + 700, str_starts(XT + 1500, YT + 650, _cn["ReturnValue"], "BP_StaticItemContainer_C"),
                                        str_starts(XT + 1500, YT + 750, _cn["ReturnValue"], "BP_SkeletalItemContainer_C"))),
               _smo["ReturnValue"])   # MCM "Stash looting" Off (2) = stashes stay vanilla
sl_s = set_from("Lootable", "bool", XT + 1300, YT + 400, stash, "a stash (not a loose item)?")
g.link(cic["then"], sl_s["execute"])
sts = set_from("TapComp", "object", XT + 1600, YT + 400, member_pure(ACTOR, "GetComponentByClass", XT + 1400, YT + 600, cic["AsInteractable Item Container"], [
    ("ComponentClass", "class", dict(sub=ACOMP, extra='DefaultObject="/Script/Stalker2.ItemContainerInteractionComponent",')),
    ("ReturnValue", "object", dict(sub=ICOMP, out=True))])["ReturnValue"], "its open interaction", sub=ICOMP)
g.link(sl_s["then"], sts["execute"])
sl_n = self_set("Lootable", "bool", XT + 1300, YT + 900, "something else", default="false")
g.link(cic["CastFailed"], sl_n["execute"])
stn = self_set("TapComp", "object", XT + 1600, YT + 900, "none", sub=ICOMP)
g.link(sl_n["then"], stn["execute"])
lootable = lambda x, y: self_get("Lootable", "bool", x, y)

#   T1: reaching: at the touch frame (montage paused there) or after 0.8 s: give the key back and open the window
tp = lambda x, y: self_get("TouchPressAt", "real", x, y, subcat="double")
late = d_op("Greater_DoubleDouble", XT + 200, YT + 2000, d_op("Subtract_DoubleDouble", XT, YT + 2000, now(XT - 200, YT + 2000), tp(XT - 200, YT + 2100)),
            b_const="2.0", ret=RB)
held = b_and(XT + 200, YT + 2350, self_get("LootPaused", "bool", XT, YT + 2300),
             d_op("GreaterEqual_DoubleDouble", XT + 200, YT + 2450,
                  d_op("Subtract_DoubleDouble", XT, YT + 2450, now(XT - 200, YT + 2450), self_get("PausedAt", "real", XT - 200, YT + 2550, subcat="double")),
                  self_get("TouchHoldBeforeOpen", "real", XT, YT + 2600, subcat="double"), ret=RB))
bt1 = branch(XT + 400, YT + 1800, "reached (or 2 s) after a tap? open the window now",
             b_and(XT + 300, YT + 2100, int_eq(XT + 100, YT + 2200, tstate(XT - 100, YT + 2200), 2),
                   b_not(XT + 100, YT + 2150, self_get("DoorTouch", "bool", XT - 100, YT + 2150)),   # doors: no window
                   b_not(XT + 100, YT + 2280, self_get("InvOpen", "bool", XT - 100, YT + 2280)),
                   b_or(XT + 300, YT + 2300, held, late)))
g.link(sqt["then_1"], bt1["execute"])
bt1o = branch(XT + 400, YT + 1500, "reaching and the window opened by itself (a stash that opens on the press)?",
              b_and(XT + 300, YT + 1650, int_eq(XT + 100, YT + 1650, tstate(XT - 100, YT + 1650), 2), self_get("InvOpen", "bool", XT + 100, YT + 1730)))
g.link(bt1["else"], bt1o["execute"])
_e1, _x1 = tap_active(XT + 1200, YT + 1800, True, "its tap interaction back on")
_s1 = self_set("TapOff", "bool", XT + 1300, YT + 2100, "", default="false")
for q_ in _x1:
    g.link(q_, _s1["execute"])
inj = inject_interact(XT + 1400, YT + 1800, "press the game's interact: opens the loot window")
ts3 = self_set("TouchState", "int", XT + 1750, YT + 1800, "window requested", default="3")
toa = set_from("TouchOpenAt", "real", XT + 2050, YT + 1800, now(XT + 1900, YT + 2000), "", subcat="double")
nto = inc("NTouch", XT + 2350, YT + 1800, "count touches")
#   n2i (tester: a tap still carried the body with the backpack; probe: the window did not open at that tap's release
#   (pressed 0.24 s after the last window closed), our injected interact 3 s later found the body's carry hold
#   started and the game carried it at once): a BODY never gets an injected interact. No window by now: the touch /
#   bag waits as if requested (TouchState 3; the player's next tap opens the window, T2 brings it back after 1 s)
_bt1b = branch(XT + 700, YT + 1650, "n2i: a body? no injected interact (it can finish a carry)", self_get("TouchIsBody", "bool", XT + 500, YT + 1800))
g.link(bt1["then"], _bt1b["execute"])
g.link(_bt1b["else"], _e1)
_ts3b = self_set("TouchState", "int", XT + 1000, YT + 1550, "no window yet: as if requested", default="3")
chain(_bt1b, _ts3b, set_from("TouchOpenAt", "real", XT + 1300, YT + 1550, now(XT + 1150, YT + 1450), "", subcat="double"),
      inc("NBodyNoInject", XT + 1600, YT + 1550, "count (probe)"))
_sra = set_from("ReenableAt", "real", XT + 1700, YT + 1600, now(XT + 1550, YT + 1450), "its tap interaction is on again since", subcat="double")
_ts5 = self_set("TouchState", "int", XT + 2000, YT + 1600, "wait for the game to target it again", default="5")
chain(_s1, _sra, _ts5)
#   T10 (n2h): the body we look at has its carry hold "started" (HoldComponent.IsHoldStarted) while F has been up for
#   0.15 s and the left hand is free (not carrying)? A stale hold: the next tap would finish the carry at once. Its hold
#   interaction is switched off for one tick (reset), then on again
_hcv = lambda x, y: self_get("BodyHold", "object", x, y, sub=HOLDC)
_sq10 = sequence(XT + 300, YT + 16000, "n2h: stale carry hold", 2)
g.link(sqt["then_10"], _sq10["execute"])
_hrv = lambda x, y: self_get("HoldResetComp", "object", x, y, sub=HOLDC)
_b10a = branch(XT + 600, YT + 16000, "reset last tick? back on", is_valid(XT + 500, YT + 16150, _hrv(XT + 300, YT + 16150)))
g.link(_sq10["then_0"], _b10a["execute"])
_c10a = member_call(ICOMP, "SetInteractionActive", XT + 900, YT + 16000, _hrv(XT + 700, YT + 16150), "its hold back on",
                    [("bActive", "bool", dict(extra='DefaultValue="true",'))])
chain(_b10a, _c10a, self_set("HoldResetComp", "object", XT + 1200, YT + 16000, "done", sub=HOLDC))
_hst = member_pure(HOLDC, "IsHoldStarted", XT + 300, YT + 16500, _hcv(XT + 100, YT + 16500), [RB])["ReturnValue"]
_stale = b_and(XT + 500, YT + 16450, self_get("TouchIsBody", "bool", XT + 300, YT + 16400), is_valid(XT + 300, YT + 16430, _hcv(XT + 100, YT + 16430)), _hst,
               b_not(XT + 300, YT + 16570, self_get("KeyHeld", "bool", XT + 100, YT + 16570)),
               d_op("Greater_DoubleDouble", XT + 300, YT + 16640,
                    d_op("Subtract_DoubleDouble", XT + 100, YT + 16640, now(XT - 100, YT + 16640), self_get("KeySeenAt", "real", XT - 100, YT + 16710, subcat="double")),
                    b_const="0.15", ret=RB),
               b_not(XT + 300, YT + 16780, obj_q("IsLeftHandBusy", XT + 100, YT + 16780, as_pc)))
_sh10 = set_from("HoldStale", "bool", XT + 600, YT + 16300, _stale, "probe")
g.link(_sq10["then_1"], _sh10["execute"])
_b10 = branch(XT + 900, YT + 16300, "a stale hold on the body we look at? reset it", self_get("HoldStale", "bool", XT + 700, YT + 16450))
g.link(_sh10["then"], _b10["execute"])
_c10 = member_call(ICOMP, "SetInteractionActive", XT + 1200, YT + 16300, _hcv(XT + 1000, YT + 16450), "its hold off (one tick)",
                   [("bActive", "bool", dict(extra='DefaultValue="false",'))])
chain(_b10, _c10, set_from("HoldResetComp", "object", XT + 1500, YT + 16300, _hcv(XT + 1300, YT + 16450), "on again next tick", sub=HOLDC),
      inc("NStaleHold", XT + 1800, YT + 16300, "count (probe)"))
#   T9 (n2g): a carry started from a tap? the game's own drop (Obj.DropCorpse, with its animation) once it holds the
#   body (false until then); after 2.5 s (or F held again) given up
_b9 = branch(XT + 600, YT + 15300, "n2g: a carry from a tap waiting to be dropped?", self_get("TapCarry", "bool", XT + 400, YT + 15450))
g.link(sqt["then_9"], _b9["execute"])
_b9l = branch(XT + 900, YT + 15300, "for 2.5 s already, or F held again (another pick-up: an artifact...)? given up",
              b_or(XT + 900, YT + 15450, d_op("Greater_DoubleDouble", XT + 800, YT + 15450,
                   d_op("Subtract_DoubleDouble", XT + 600, YT + 15450, now(XT + 400, YT + 15450), self_get("TapCarryAt", "real", XT + 400, YT + 15520, subcat="double")),
                   b_const="2.5", ret=RB), self_get("KeyHeld", "bool", XT + 700, YT + 15600)))
g.link(_b9["then"], _b9l["execute"])
g.link(_b9l["then"], self_set("TapCarry", "bool", XT + 1200, YT + 15150, "given up", default="false")["execute"])
_dc9 = member_call(OBJC, "DropCorpse", XT + 1200, YT + 15300, as_pc, "the game's drop (its animation; bPlayAnimation defaults true)",
                   [("ReturnValue", "bool", dict(out=True))])
g.link(_b9l["else"], _dc9["execute"])
_b9d = branch(XT + 1500, YT + 15300, "dropped?", _dc9["ReturnValue"])
g.link(_dc9["then"], _b9d["execute"])
chain(_b9d, self_set("TapCarry", "bool", XT + 1800, YT + 15300, "done", default="false"), inc("NTapCarry", XT + 2100, YT + 15300, "count (probe)"))
#   T8: 0.12 s after the tap interaction is on again: press the game's interact (the window); no window after 0.35 s:
#   press again (twice at most)
sq8w = sequence(XT + 300, YT + 13000, "window press steps", 2)
g.link(sqt["then_8"], sq8w["execute"])
bw5 = branch(XT + 600, YT + 13000, "waited 0.12 s since its tap interaction came back? press the game's interact",
             b_and(XT + 500, YT + 13200, int_eq(XT + 300, YT + 13200, tstate(XT + 100, YT + 13200), 5),
                   d_op("GreaterEqual_DoubleDouble", XT + 300, YT + 13300,
                        d_op("Subtract_DoubleDouble", XT + 100, YT + 13300, now(XT - 100, YT + 13300),
                             self_get("ReenableAt", "real", XT - 100, YT + 13370, subcat="double")), b_const="0.12", ret=RB),
                   # 1.3.1 (tester: bag on bodies, looting fast: "no window for the body, then my inventory opens"; probe:
                   # the press came while the last bag's weapon draw was playing, the window never opened, 2 retries,
                   # then a game montage and a draw): no interact while a game action (MainActionSlot) plays
                   b_not(XT + 300, YT + 13440, slot_active(XT + 100, YT + 13440, anim, "MainActionSlot"))))
g.link(sq8w["then_0"], bw5["execute"])
g.link(bw5["then"], inj["execute"])
chain(inj, ts3, toa, nto, self_set("InjRetries", "int", XT + 2650, YT + 1800, "", default="0"))
_tsince = d_op("Subtract_DoubleDouble", XT + 100, YT + 13700, now(XT - 100, YT + 13700), self_get("TouchOpenAt", "real", XT - 100, YT + 13770, subcat="double"))
bwr = branch(XT + 600, YT + 13600, "window asked for 0.35 s ago and not open? press again (twice at most)",
             b_and(XT + 500, YT + 13800, int_eq(XT + 300, YT + 13800, tstate(XT + 100, YT + 13800), 3),
                   b_not(XT + 300, YT + 13870, self_get("InvOpen", "bool", XT + 100, YT + 13870)),
                   d_op("GreaterEqual_DoubleDouble", XT + 300, YT + 13940, _tsince, b_const="0.35", ret=RB),
                   b_not(XT + 300, YT + 14080, slot_active(XT + 100, YT + 14080, anim, "MainActionSlot")),   # 1.3.1
                   # n2f: not when a window opened since the press (the player closed it: the retry opened it again)
                   d_op("Less_DoubleDouble", XT + 300, YT + 14150, self_get("OpenAt", "real", XT + 100, YT + 14150, subcat="double"),
                        self_get("TouchPressAt", "real", XT + 100, YT + 14220, subcat="double"), ret=RB),
                   b_not(XT + 300, YT + 14290, self_get("TouchIsBody", "bool", XT + 100, YT + 14290)),   # n2i: never on a body
                   kml("Less_IntInt", XT + 300, YT + 14010, [("A", "int"), ("B", "int", dict(extra='DefaultValue="2",')), RB])["ReturnValue"]))
_lii = [n_ for n_ in g.nodes if any('MemberName="Less_IntInt"' in b_ for b_ in n_.body)][-1]
g.link(self_get("InjRetries", "int", XT + 100, YT + 14010), _lii["A"])
g.link(sq8w["then_1"], bwr["execute"])
inj2 = inject_interact(XT + 900, YT + 13600, "press the game's interact again")
g.link(bwr["then"], inj2["execute"])
chain(inj2, set_from("TouchOpenAt", "real", XT + 1250, YT + 13600, now(XT + 1100, YT + 13800), "", subcat="double"),
      inc("InjRetries", XT + 1550, YT + 13600, "retries"), inc("NInjRetry", XT + 1850, YT + 13600, "count (probe)"))
g.link(bt1o["then"], ts3["execute"])

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
bfw2 = branch(XT + 850, YT + 2500, "weapon in hand? play on forward", b_not(XT + 750, YT + 2400, self_get("GrabBH", "bool", XT + 550, YT + 2400)))
bbo2 = branch(XT + 700, YT + 2300, "bag looting? the bag goes back", self_get("BagMode", "bool", XT + 500, YT + 2450))
g.link(bt2b["then"], bbo2["execute"])
g.link(bbo2["else"], bfw2["execute"])
bag_out(XT + 1000, YT + 2200, bbo2["then"])
g.link(bfw2["else"], mres2["execute"])
mresf2 = member_call(ANIMI, "Montage_Resume", XT + 1150, YT + 2450, anim, "go on (forward)", [("Montage", "object", dict(sub=MONT))])
mresf2.pins["Montage"].const = True
g.link(gm2(XT + 950, YT + 2350), mresf2["Montage"])
g.link(bfw2["then"], mresf2["execute"])
chain(mresf2, self_set("LootPaused", "bool", XT + 1450, YT + 2450, "", default="false"),
      self_set("LootReach", "bool", XT + 1750, YT + 2450, "touch over", default="false"),
      self_set("TouchState", "int", XT + 2050, YT + 2450, "idle", default="0"))
g.link(bt2b["else"], ts4["execute"])

#   the interact key pressed (polled, T6 below) on a corpse / stash
lcomp = lambda x, y: self_get("LootComp", "object", x, y, sub=PRIM)
bpress = branch(XT + 200, YT + 3700, "idle, a corpse / stash in sight, its part known? its tap interaction off until we know tap or hold",
                b_and(XT + 100, YT + 3900, int_eq(XT - 100, YT + 3900, tstate(XT - 300, YT + 3900), 0),
                      lootable(XT - 100, YT + 3960),   # 1.0.1f: LootComp is whatever the crosshair ray hits (a wall too)
                      is_valid(XT - 100, YT + 4040, lcomp(XT - 300, YT + 4040))))
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
      self_set("LootWait", "bool", XT + 2300, YT + 3700, "n2f: no stale wait for an item's use", default="false"),
      self_set("TouchState", "int", XT + 2600, YT + 3700, "reaching", default="2")]
chain(*tr)
_ep, _xp = tap_active(XT + 500, YT + 3300, False, "its tap interaction off (the game would open the window at the release)")
#   n2h (tester: a tap picked a body up; "the body pickup should never happen in the first place"): a BODY's search
#   interaction is no longer switched off at the press. With it off the game's hold interaction was the only one left
#   for that press (the window still opened at the release, through it), and a later tap could finish a carry at once.
#   The game's own tap (window at the release) and hold (carry) now run untouched; stashes as before
_bpb = branch(XT + 300, YT + 3150, "n2h: a body? its interactions untouched (vanilla tap / hold)", self_get("TouchIsBody", "bool", XT + 100, YT + 3250))
g.link(bpress["then"], _bpb["execute"])
g.link(_bpb["else"], _ep)
_sp = self_set("TapOff", "bool", XT + 1200, YT + 3300, "", default="true")
for q_ in _xp:
    g.link(q_, _sp["execute"])
_stp = set_from("TouchPressAt", "real", XT + 1500, YT + 3300, now(XT + 1350, YT + 3500), "pressed", subcat="double")
chain(_sp, _stp, self_set("TouchState", "int", XT + 1800, YT + 3300, "pressed: tap or hold?", default="1"))
g.link(_bpb["then"], _stp["execute"])
#     a body: its pelvis bone (the mesh component's bounds stay at the standing height: build e aimed 21 deg UP at a
#     corpse), else (stash, mutant without that bone) the bounds centre set above
for q_ in list(tr[0]["then"].links):
    tr[0]["then"].links.remove(q_); q_.links.remove(tr[0]["then"])
cskm = exec_pins(Node(g, BG + "K2Node_DynamicCast", nm("K2Node_DynamicCast"), XT + 650, YT + 4100, "a body (skeletal mesh)?",
                      ["TargetType=\"/Script/CoreUObject.Class'/Script/Engine.SkeletalMeshComponent'\""]))
cskm.pin("CastFailed", "exec", out=True)
cskm.pin("Object", "object", sub=OBJ)
cskm.pin("AsSkeletal Mesh Component", "object", sub=SKC, out=True)
cskm.pin("bSuccess", "bool", out=True)
g.link(lcomp(XT + 450, YT + 4300), cskm["Object"])
g.link(tr[0]["then"], cskm["execute"])
bhip = branch(XT + 950, YT + 4100, "has a pelvis bone?",
              member_pure(SC_, "DoesSocketExist", XT + 800, YT + 4300, cskm["AsSkeletal Mesh Component"],
                          [("InSocketName", "name", dict(extra='DefaultValue="jnt_hips",')), RB])["ReturnValue"])
g.link(cskm["then"], bhip["execute"])
ship = set_from("ItemCenter", "struct", XT + 1250, YT + 4100,
                member_pure(SC_, "GetSocketLocation", XT + 1050, YT + 4300, cskm["AsSkeletal Mesh Component"],
                            [("InSocketName", "name", dict(extra='DefaultValue="jnt_hips",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"],
                "reach target = the pelvis", sub=VEC)
g.link(bhip["then"], ship["execute"])
g.link(ship["then"], tr[1]["execute"])
g.link(bhip["else"], tr[1]["execute"])
g.link(cskm["CastFailed"], tr[1]["execute"])
#     the body's / stash's centre seen from the camera, in VIEW axes (with a weapon the arm rig follows the view):
#     its direction picks the touch asset
_tcm = lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", XT + 2300, YT + 4300,
                [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                 ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"]
_tcl = member_pure(PCM, "GetCameraLocation", XT + 2500, YT + 4200, _tcm, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_tcr = member_pure(PCM, "GetCameraRotation", XT + 2500, YT + 4300, _tcm, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_tax = []
for k_, fn_ in enumerate(("GetForwardVector", "GetRightVector", "GetUpVector")):
    n_ = kml(fn_, XT + 2750, YT + 4300 + 100 * k_, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_tcr, n_["InRot"])
    _tax.append(n_["ReturnValue"])
_trel = vop("Subtract_VectorVector", XT + 2750, YT + 4100, self_get("ItemCenter", "struct", XT + 2550, YT + 4100, sub=VEC), _tcl)
_tah = vop("Dot_VectorVector", XT + 3000, YT + 4100, _trel, _tax[0], ret_sub="real")
_trt = vop("Dot_VectorVector", XT + 3000, YT + 4200, _trel, _tax[1], ret_sub="real")
_tup = vop("Dot_VectorVector", XT + 3000, YT + 4300, _trel, _tax[2], ret_sub="real")
_tel = kml("DegAtan2", XT + 3300, YT + 4100, [D("Y"), D("X"), RD])
g.link(_tup, _tel["Y"])
g.link(_tah, _tel["X"])
_taz = kml("DegAtan2", XT + 3300, YT + 4300, [D("Y"), D("X"), RD])
g.link(_trt, _taz["Y"])
g.link(_tah, _taz["X"])
_tie = _bin(XT + 3500, YT + 4100, _tel["ReturnValue"], "45.0", "15.0", 4)
_tia = _bin(XT + 3500, YT + 4300, _taz["ReturnValue"], "30.0", "15.0", 4)
_tix = _imad(XT + 4000, YT + 4200, _tie, 5, _tia)
tel = set_from("ItemElev", "real", XT + 2900, YT + 3700, _tel["ReturnValue"], "centre seen from the camera, view axes (probe)", subcat="double")
taz = set_from("ItemAzim", "real", XT + 3200, YT + 3700, _taz["ReturnValue"], "", subcat="double")
tdi = set_from("ItemDist", "real", XT + 3350, YT + 3700, kml("VSize", XT + 3200, YT + 4000, [("A", "struct", dict(sub=VEC)), RD], )["ReturnValue"], "", subcat="double")
g.link(_trel, [n_ for n_ in g.nodes if n_.name == tdi.pins["ItemDist"].links[0].node.name][0]["A"])
tbx = set_from("TouchBin", "int", XT + 3500, YT + 3700, _tix, "its bin: elevation row x 5 + azimuth column")
chain(tel, taz, tdi, tbx)
g.link(tr[-1]["then"], tel["execute"])
prev = tbx
for k in range(25):
    bk = branch(XT + 3800 + 600 * k, YT + 3700, f"bin {k}: elevation {-45 + 15 * (k // 5):+d}, azimuth {-30 + 15 * (k % 5):+d}?",
                int_eq(XT + 3700 + 600 * k, YT + 3900, self_get("TouchBin", "int", XT + 3500 + 600 * k, YT + 3900), k))
    g.link(prev["then" if k == 0 else "else"], bk["execute"])
    sa = self_set("TouchAsset", "object", XT + 4100 + 600 * k, YT + 3700, "the touch toward it", sub=ANIMSEQB)
    sa.pins["TouchAsset"].extra = f'DefaultObject="{TOUCH_SEQS[k]}",'
    g.link(bk["then"], sa["execute"])
    if k == 24:
        g.link(bk["else"], sa["execute"])
    _sa_all = globals().setdefault("_sa_all", [])
    _sa_all.append(sa)
    prev = bk
DOOR_PUSH = "/ImmersiveLooting/Runtime/AS_ImmLoot_DoorPush.AS_ImmLoot_DoorPush"
DOOR_PULL = "/ImmersiveLooting/Runtime/AS_ImmLoot_DoorPull.AS_ImmLoot_DoorPull"
bdov = branch(XT + 3800, YT + 3300, "a door? its own push / pull asset (lower left), not the bin's", self_get("DoorTouch", "bool", XT + 3600, YT + 3450))
for sa_ in _sa_all:
    g.link(sa_["then"], bdov["execute"])
# build w (tester, pistol: "very obviously twisting when coming back"; probe: the touches' AK grip is 88 deg from every
# pistol's support grip and their wrist rolls ~170 deg): with a pistol, a body / stash touch uses AS_ImmLoot_TouchPt<bin>
# (make_grab_seq build_touch_pistol: built on the pistol idle, only the upper arm / forearm move, no wrist roll)
TOUCH_PT = [f"/ImmersiveLooting/Runtime/AS_ImmLoot_TouchPt{i}.AS_ImmLoot_TouchPt{i}" for i in range(25)]
_ptq = member_pure(OBJC, "GetMainHandEquipType", XT + 3800, YT + 6300, as_pc,
                   [("ReturnValue", "byte", dict(sub=EN("/Script/Stalker2.EMainHandEquipmentType"), out=True))])["ReturnValue"]
_pti = kml("Conv_ByteToInt", XT + 4000, YT + 6300, [("InByte", "byte", dict(extra='DefaultValue="0",')), ("ReturnValue", "int", dict(out=True))])
g.link(_ptq, _pti["InByte"])
bpt = branch(XT + 4100, YT + 6000, "build w: a pistol in hand (MainHandEquipmentType 1)? the pistol touch for this bin", int_eq(XT + 4100, YT + 6200, _pti["ReturnValue"], 1))
g.link(bdov["else"], bpt["execute"])
_prev = bpt
for k in range(25):
    bk = branch(XT + 4400 + 600 * k, YT + 6000, f"pistol, bin {k}?", int_eq(XT + 4300 + 600 * k, YT + 6200, self_get("TouchBin", "int", XT + 4100 + 600 * k, YT + 6200), k))
    g.link(_prev["then" if k == 0 else "else"], bk["execute"])
    sp_ = self_set("TouchAsset", "object", XT + 4700 + 600 * k, YT + 6000, "the pistol touch toward it", sub=ANIMSEQB)
    sp_.pins["TouchAsset"].extra = f'DefaultObject="{TOUCH_PT[k]}",'
    g.link(bk["then"], sp_["execute"])
    _prev = bk
barm = branch(XT + 3950, YT + 3000, "weapon in hand? (else the empty-hands door assets)", obj_q("HasItemInMainHand", XT + 3800, YT + 3150, as_pc))
g.link(bdov["then"], barm["execute"])
DOOR_PUSH_BH = "/ImmersiveLooting/Runtime/AS_ImmLoot_DoorPushBH.AS_ImmLoot_DoorPushBH"
DOOR_PULL_BH = "/ImmersiveLooting/Runtime/AS_ImmLoot_DoorPullBH.AS_ImmLoot_DoorPullBH"
# door build B (tester: "the hand clips through the gun, the fingers look weird as they settle; the return should go in a
# downward arc under the pistol or rifle"): with a weapon, the family door assets (make_grab_seq build_door_family):
# a pistol (MainHandEquipmentType 1) -> ...Pt, any other weapon -> ...Ar
DOOR_FAM = {k_: f"/ImmersiveLooting/Runtime/AS_ImmLoot_Door{k_}.AS_ImmLoot_Door{k_}" for k_ in ("PushAr", "PullAr", "PushPt", "PullPt")}
bdpt = branch(XT + 4050, YT + 2700, "door build B: a pistol in hand? the pistol door assets",
              int_eq(XT + 3950, YT + 2850, _pti["ReturnValue"], 1))
g.link(barm["then"], bdpt["execute"])
for _ex0, _pull, _push, _yy in ((bdpt["then"], DOOR_FAM["PullPt"], DOOR_FAM["PushPt"], 2700), (bdpt["else"], DOOR_FAM["PullAr"], DOOR_FAM["PushAr"], 3300),
                                (barm["else"], DOOR_PULL_BH, DOOR_PUSH_BH, 3600)):
    _bp = branch(XT + 4100, YT + _yy, "closing (a pull)?", self_get("DoorPulling", "bool", XT + 3900, YT + _yy + 150))
    g.link(_ex0, _bp["execute"])
    for _ex, _asset, _xx in ((_bp["then"], _pull, 4400), (_bp["else"], _push, 4700)):
        _sd = self_set("TouchAsset", "object", XT + _xx, YT + _yy - 100, _asset.rsplit(".", 1)[1], sub=ANIMSEQB)
        _sd.pins["TouchAsset"].extra = f'DefaultObject="{_asset}",'
        g.link(_ex, _sd["execute"])

#     released: a tap (shorter than HoldToDrag) starts the touch; a longer press was the game's hold (carry a body,
#     vanilla: we never touch it): idle again
brel = branch(XT + 200, YT + 5000, "released after our press?", int_eq(XT, YT + 5200, tstate(XT - 200, YT + 5200), 1))
btap = branch(XT + 500, YT + 5000, "a tap (shorter than HoldToDrag)? reach for it",
              d_op("Less_DoubleDouble", XT + 400, YT + 5250, d_op("Subtract_DoubleDouble", XT + 200, YT + 5250, now(XT, YT + 5250), tp(XT, YT + 5350)),
                   self_get("HoldToDrag", "real", XT + 200, YT + 5400, subcat="double"), ret=RB))
g.link(brel["then"], btap["execute"])
g.link(btap["then"], tr[0]["execute"])
g.link(btap["else"], self_set("TouchState", "int", XT + 800, YT + 5100, "idle (vanilla handled the hold)", default="0")["execute"])

#   T7 (doors): the touch faster than a loot touch; held DoorHold s at the touch frame, then back (same as after a loot
#   window); a door touch whose reach never started (skipped) or ended is cleared
sq7d = sequence(XT + 300, YT + 9000, "door steps", 4)
g.link(sqt["then_7"], sq7d["execute"])
dtc = lambda x, y: self_get("DoorTouch", "bool", x, y)
bsp = branch(XT + 600, YT + 9000, "door touch playing, not sped up yet?",
             b_and(XT + 500, YT + 9200, dtc(XT + 300, YT + 9200), b_not(XT + 300, YT + 9270, self_get("DoorSped", "bool", XT + 100, YT + 9270)),
                   grab_active(XT + 300, YT + 9340)))
g.link(sq7d["then_0"], bsp["execute"])
msr = member_call(ANIMI, "Montage_SetPlayRate", XT + 900, YT + 9000, anim, "faster: the hand meets the swinging door", [
    ("Montage", "object", dict(sub=MONT)), ("NewPlayRate", "real", dict(subcat="float", extra='DefaultValue="1.000000",'))])
msr.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", XT + 700, YT + 9200, sub=MONT), msr["Montage"])
g.link(d_op("Multiply_DoubleDouble", XT + 700, YT + 9300, self_get("PlayRate", "real", XT + 500, YT + 9300, subcat="double"),
            self_get("DoorRate", "real", XT + 500, YT + 9380, subcat="double")), msr["NewPlayRate"])
g.link(bsp["then"], msr["execute"])
g.link(msr["then"], self_set("DoorSped", "bool", XT + 1200, YT + 9000, "", default="true")["execute"])
bdh = branch(XT + 600, YT + 9500, "door touch held long enough at the door? bring the hand back",
             b_and(XT + 500, YT + 9700, dtc(XT + 300, YT + 9700), self_get("LootPaused", "bool", XT + 300, YT + 9770),
                   d_op("GreaterEqual_DoubleDouble", XT + 300, YT + 9850,
                        d_op("Subtract_DoubleDouble", XT + 100, YT + 9850, now(XT - 100, YT + 9850), self_get("PausedAt", "real", XT - 100, YT + 9930, subcat="double")),
                        self_get("DoorHold", "real", XT + 100, YT + 9990, subcat="double"), ret=RB)))
g.link(sq7d["then_1"], bdh["execute"])
sdf = self_set("DoorTouch", "bool", XT + 900, YT + 9500, "", default="false")
g.link(bdh["then"], sdf["execute"])
g.link(sdf["then"], brv["execute"])   # the same hand return as after a loot window
bdx = branch(XT + 600, YT + 10100, "door touch, but our montage not playing (skipped / ended / cut)?",
             b_and(XT + 500, YT + 10300, dtc(XT + 300, YT + 10300), b_not(XT + 300, YT + 10370, self_get("PendingReach", "bool", XT + 100, YT + 10370)),
                   b_not(XT + 300, YT + 10440, grab_active(XT + 100, YT + 10440)),
                   b_not(XT + 300, YT + 10510, self_get("DoorWaiting", "bool", XT + 100, YT + 10510))))
g.link(sq7d["then_2"], bdx["execute"])
chain_x = [self_set("DoorTouch", "bool", XT + 900, YT + 10100, "", default="false"),
           self_set("TouchState", "int", XT + 1200, YT + 10100, "idle", default="0"),
           self_set("LootReach", "bool", XT + 1500, YT + 10100, "", default="false"),
           self_set("LootPaused", "bool", XT + 1800, YT + 10100, "", default="false"),
           self_set("LootReverse", "bool", XT + 2100, YT + 10100, "", default="false"),
           inc("NDoorCut", XT + 2400, YT + 10100, "count (probe)")]
g.link(bdx["then"], chain_x[0]["execute"])
chain(*chain_x)
#   door build A: the leaf moved (or the wait ran out)? push / pull from how the pressed point moved, then the touch
_dwt = lambda x, y: self_get("DoorWaiting", "bool", x, y)
_dcomp = self_get("DoorComp", "object", XT + 100, YT + 11000, sub=PRIM)
_dxf2 = member_pure(SC_, "K2_GetComponentToWorld", XT + 300, YT + 11000, _dcomp, [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
_dtl = kml("TransformLocation", XT + 500, YT + 11000, [("T", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC)),
                                                      ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_dxf2, _dtl["T"])
g.link(self_get("DoorLocal", "struct", XT + 300, YT + 11100, sub=VEC), _dtl["Location"])
_dw0 = lambda x, y: self_get("DoorW0", "struct", x, y, sub=VEC)
_dmv = vop("Subtract_VectorVector", XT + 700, YT + 11000, _dtl["ReturnValue"], _dw0(XT + 500, YT + 11100))
_dray = kml("Normal", XT + 700, YT + 11200, [("A", "struct", dict(sub=VEC)), ("Tolerance", "real", dict(subcat="float", extra='DefaultValue="0.000100",')),
                                            ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(vop("Subtract_VectorVector", XT + 500, YT + 11200, _dw0(XT + 300, YT + 11200), self_get("DoorCam0", "struct", XT + 300, YT + 11270, sub=VEC)), _dray["A"])
_drad = vop("Dot_VectorVector", XT + 900, YT + 11100, _dmv, _dray["ReturnValue"], ret_sub="real")
_dlen = kml("VSize", XT + 900, YT + 11000, [("A", "struct", dict(sub=VEC)), RD])
g.link(_dmv, _dlen["A"])
_dmoved = d_op("Greater_DoubleDouble", XT + 1100, YT + 11000, _dlen["ReturnValue"], b_const="0.8", ret=RB)
_dlate = d_op("Greater_DoubleDouble", XT + 1100, YT + 11300,
              d_op("Subtract_DoubleDouble", XT + 900, YT + 11300, now(XT + 700, YT + 11300), self_get("DoorPressAt", "real", XT + 700, YT + 11370, subcat="double")),
              self_get("DoorDecideMax", "real", XT + 900, YT + 11400, subcat="double"), ret=RB)
bdw = branch(XT + 600, YT + 10700, "door build A: waiting, and the leaf moved (or the wait ran out)? decide and reach",
             b_and(XT + 500, YT + 10900, _dwt(XT + 300, YT + 10900), b_or(XT + 1300, YT + 11100, _dmoved, _dlate)))
g.link(sq7d["then_3"], bdw["execute"])
bdm = branch(XT + 900, YT + 10700, "moved? toward the camera = a pull, away = a push (else the open / closed rule)", _dmoved)
g.link(bdw["then"], bdm["execute"])
sdp2 = set_from("DoorPulling", "bool", XT + 1200, YT + 10700, d_op("Less_DoubleDouble", XT + 1100, YT + 10850, _drad, b_const="0.0", ret=RB),
                "toward the camera: a pull")
g.link(bdm["then"], sdp2["execute"])
sdr = set_from("DoorRadial", "real", XT + 1500, YT + 10700, _drad, "cm toward (-) / away (+) when decided (probe)", subcat="double")
g.link(sdp2["then"], sdr["execute"])
sdw0 = self_set("DoorWaiting", "bool", XT + 1800, YT + 10700, "decided", default="false")
g.link(sdr["then"], sdw0["execute"])
g.link(bdm["else"], sdw0["execute"])
chain(sdw0, set_from("DoorDecideT", "real", XT + 2100, YT + 10700,
                     d_op("Subtract_DoubleDouble", XT + 2000, YT + 10900, now(XT + 1800, YT + 10900), self_get("DoorPressAt", "real", XT + 1800, YT + 10970, subcat="double")),
                     "s from the press to the decision (probe)", subcat="double"))
#     the touch chain from its second step: pending reach, touch mode, TouchState 2, then the asset for the direction
g.link([n_ for n_ in g.nodes if n_.comment == "s from the press to the decision (probe)"][-1]["then"], tr[1]["execute"])

#   T6: the player's interact keys polled: pressed / released this tick (no mapping context, no input on this actor)
PCC = cls("/Script/Engine.PlayerController")
kd0 = self_set("KeyDown", "bool", XT + 400, YT + 5800, "this tick", default="false")
ku0 = self_set("KeyUp", "bool", XT + 700, YT + 5800, "", default="false")
kh0 = self_set("KeyHeld", "bool", XT + 1000, YT + 5650, "", default="false")
#   n2g (tester, looting fast: "the backpack didn't come out, and then I picked up the body when I was tapping F";
#   probe: both times F was seen down (IsInputKeyDown) for 1-2 ticks but WasInputKeyJustPressed never fired, so our
#   press never ran: the game opened its plain window / started the carry): F down now and up last tick = a press too
_khp = set_from("KeyHeldPrev", "bool", XT + 100, YT + 5650, self_get("KeyHeld", "bool", XT - 100, YT + 5750), "n2g: held last tick?")
chain(_khp, kd0, ku0, kh0)
g.link(sqt["then_6"], _khp["execute"])
qk = member_pure(EISI, "QueryKeysMappedToAction", XT + 700, YT + 6100, subt["ReturnValue"], [
    ("Action", "object", dict(sub=IA_CLS, extra=f'DefaultObject="{IA_INTERACT}",')), ("ReturnValue", "struct", dict(sub=KEY, out=True))])
qk.pins["self"].cat = "interface"
qk.pins["Action"].const = True
qk.pins["ReturnValue"].container = "Array"
fek = Node(g, BG + "K2Node_MacroInstance", nm("K2Node_MacroInstance"), XT + 1000, YT + 5800, "each of the player's interact keys",
           [FOREACH, f"ResolvedWildcardType=(PinCategory=\"struct\",PinSubCategoryObject={KEY})"])
fek.pin("Exec", "exec")
fek.pin("Array", "struct", sub=KEY)
fek.pins["Array"].container = "Array"
fek.pin("LoopBody", "exec", out=True)
fek.pin("Array Element", "struct", sub=KEY, out=True)
fek.pin("Array Index", "int", out=True)
fek.pin("Completed", "exec", out=True)
g.link(qk["ReturnValue"], fek["Array"])
g.link(kh0["then"], fek["Exec"])
_jp = member_pure(PCC, "WasInputKeyJustPressed", XT + 1200, YT + 6100, gpc_t["ReturnValue"], [("Key", "struct", dict(sub=KEY)), RB])
g.link(fek["Array Element"], _jp["Key"])
bjp = branch(XT + 1400, YT + 5800, "just pressed?", _jp["ReturnValue"])
_kdn = member_pure(PCC, "IsInputKeyDown", XT + 1200, YT + 6500, gpc_t["ReturnValue"], [("Key", "struct", dict(sub=KEY)), RB])
g.link(fek["Array Element"], _kdn["Key"])
bkh = branch(XT + 1250, YT + 5500, "held?", _kdn["ReturnValue"])
g.link(fek["LoopBody"], bkh["execute"])
_skh = self_set("KeyHeld", "bool", XT + 1450, YT + 5450, "", default="true")
_ksa = set_from("KeySeenAt", "real", XT + 1700, YT + 5450, now(XT + 1550, YT + 5350), "F seen down at", subcat="double")
g.link(bkh["then"], _skh["execute"])
g.link(_skh["then"], _ksa["execute"])
g.link(_ksa["then"], bjp["execute"])
g.link(bkh["else"], bjp["execute"])
_skd = self_set("KeyDown", "bool", XT + 1700, YT + 5800, "", default="true")
g.link(bjp["then"], _skd["execute"])
g.link(_skd["then"], set_from("InteractPressAt", "real", XT + 2000, YT + 5650, now(XT + 1850, YT + 5550), "pressed at", subcat="double")["execute"])
_jr = member_pure(PCC, "WasInputKeyJustReleased", XT + 1200, YT + 6300, gpc_t["ReturnValue"], [("Key", "struct", dict(sub=KEY)), RB])
g.link(fek["Array Element"], _jr["Key"])
bjr = branch(XT + 1400, YT + 6100, "just released?", _jr["ReturnValue"])
g.link(bjp["else"], bjr["execute"])
g.link(bjr["then"], self_set("KeyUp", "bool", XT + 1700, YT + 6100, "", default="true")["execute"])
bkd = branch(XT + 2000, YT + 5800, "pressed this tick?", self_get("KeyDown", "bool", XT + 1800, YT + 6000))
_bed = branch(XT + 1700, YT + 5300, "n2g: F down now, up last tick, no 'just pressed'? a press all the same",
              b_and(XT + 1600, YT + 5450, self_get("KeyHeld", "bool", XT + 1400, YT + 5400), b_not(XT + 1500, YT + 5470, self_get("KeyHeldPrev", "bool", XT + 1300, YT + 5470)),
                    b_not(XT + 1500, YT + 5540, self_get("KeyDown", "bool", XT + 1300, YT + 5540))))
g.link(fek["Completed"], _bed["execute"])
_sed = self_set("KeyDown", "bool", XT + 2000, YT + 5300, "", default="true")
chain(_bed, _sed, set_from("InteractPressAt", "real", XT + 2300, YT + 5300, now(XT + 2150, YT + 5200), "pressed at", subcat="double"),
      inc("NPressEdge", XT + 2600, YT + 5300, "count (probe)"))
g.link([n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"], bkd["execute"])
g.link(_bed["else"], bkd["execute"])
g.link(bkd["then"], bpress["execute"])
# ---- doors (1.0.2, tester: "play the hand animation when opening and closing doors"; peeking (hold) the same) ----
# The game opens / closes / peeks the door itself at the press; we never touch its input. At the press, if the game's
# interaction target belongs to a door (its class name has "Door"), the touch reaches toward the point of the door under the crosshair
# (else the leaf's centre), holds a moment and comes back (armed: plays on onto the grip; empty hands: back along its
# path), faster than a loot touch (DoorRate) so the hand meets the door as it starts to swing.
XD, YD = XT, YT + 7000
g.box("EdGraphNode_Comment_918", XD - 400, YD - 400, 6400, 3200, "Doors: the hand reaches for the door at the press (open, close, peek)")
_dow = self_get("LookActor", "object", XD - 300, YD + 300, sub=ACTOR)   # probe 1.0.2: the game's interaction target was empty at doors
_dcm = lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", XD - 500, YD + 600,
                [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                 ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"]
_dcl = member_pure(PCM, "GetCameraLocation", XD - 300, YD + 600, _dcm, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_dds = kml("Vector_Distance", XD - 100, YD + 600, [("V1", "struct", dict(sub=VEC)), ("V2", "struct", dict(sub=VEC)), RD])
g.link(self_get("LookPoint", "struct", XD - 300, YD + 700, sub=VEC), _dds["V1"])
g.link(_dcl, _dds["V2"])
_dnear = d_op("Less_DoubleDouble", XD + 100, YD + 600, _dds["ReturnValue"], b_const="250.0", ret=RB)
# every door Blueprint (BP_DoorView = native DoorView, BP_Stalker2Door / BP_Stalker2PhysicsDoor / BP_InteractableDoor... =
# plain Actors) has "Door" in its class name; the padlock (BP_Stalker2Padlock) does not
_dcn = lib_pure(KSL, "KismetSystemLibrary", "GetClassDisplayName", XD + 100, YD + 400, [("Class", "class", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
_doc = lib_pure(GS, "GameplayStatics", "GetObjectClass", XD - 100, YD + 400, [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "class", dict(sub=OBJ, out=True))])
g.link(_dow, _doc["Object"])
g.link(_doc["ReturnValue"], _dcn["Class"])
_dcc = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "Contains", XD + 300, YD + 400,
                [("SearchIn", "string"), ("Substring", "string", dict(extra='DefaultValue="Door",')),
                 ("bUseCase", "bool", dict(extra='DefaultValue="false",')), ("bSearchFromEnd", "bool", dict(extra='DefaultValue="false",')), RB])
g.link(_dcn["ReturnValue"], _dcc["SearchIn"])
#   door build A: + closets / cabinets / lockers (BP_fur_*_closet_*, *_cabinet_*, BP_int_fur_locker_*: BP_OpeningContainer)
_dmore = []
for k_, w_ in enumerate(("closet", "cabinet", "locker")):
    n_ = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "Contains", XD + 300, YD + 500 + 100 * k_,
                  [("SearchIn", "string"), ("Substring", "string", dict(extra=f'DefaultValue="{w_}",')),
                   ("bUseCase", "bool", dict(extra='DefaultValue="false",')), ("bSearchFromEnd", "bool", dict(extra='DefaultValue="false",')), RB])
    g.link(_dcn["ReturnValue"], n_["SearchIn"])
    _dmore.append(n_["ReturnValue"])
cdr = branch(XD + 200, YD, "a door (or closet / cabinet / locker door) under the crosshair, within reach?",
             b_and(XD + 150, YD + 300, is_valid(XD - 100, YD + 300, _dow), b_or(XD + 500, YD + 450, _dcc["ReturnValue"], *_dmore), _dnear))
bdo = branch(XD - 100, YD, "no corpse / stash press: doors on, idle?",
             b_and(XD - 200, YD + 150, self_get("TouchDoors", "bool", XD - 400, YD + 150), self_get("Enabled", "bool", XD - 400, YD + 220),
                   int_eq(XD - 400, YD + 290, tstate(XD - 600, YD + 290), 0)))
g.link(bpress["else"], bdo["execute"])
g.link(bdo["then"], cdr["execute"])
sdt = self_set("DoorTouch", "bool", XD + 500, YD, "a door touch", default="true")
sds = self_set("DoorSped", "bool", XD + 800, YD, "", default="false")
g.link(cdr["then"], sdt["execute"])
chain(sdt, sds)
#     1.1 (tester): the hand stays in the lower left of the screen (one fixed direction, not toward the door); opening
#     = a push, closing = a pull. Open or closed: the leaf we look at (LookComp) turned away from its rest yaw.
_rr = other_get(SC_, "RelativeRotation", "struct", XD + 900, YD + 400, self_get("LookComp", "object", XD + 700, YD + 400, sub=PRIM), sub=ROT)
_rrb = kml("BreakRotator", XD + 1100, YD + 400, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(_rr, _rrb["InRot"])
sdy = set_from("DoorYaw", "real", XD + 1100, YD, _rrb["Yaw"], "the leaf's yaw (probe)", subcat="double")
g.link(sds["then"], sdy["execute"])
_ady = kml("Abs", XD + 1300, YD + 400, [D("A"), RD])
g.link(self_get("DoorYaw", "real", XD + 1100, YD + 500, subcat="double"), _ady["A"])
sdpl = set_from("DoorPulling", "bool", XD + 1400, YD, d_op("Greater_DoubleDouble", XD + 1500, YD + 400, _ady["ReturnValue"], b_const="10.0", ret=RB),
                "open now? then this press closes it: a pull", )
g.link(sdy["then"], sdpl["execute"])
#     empty hands: the reach table aims at ItemCenter: a point ahead, lower left in view axes (camera + 55 fwd, 22 left, 20 down)
_dcr = member_pure(PCM, "GetCameraRotation", XD + 1500, YD + 700, _dcm, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_dax = []
for k_, fn_ in enumerate(("GetForwardVector", "GetRightVector", "GetUpVector")):
    n_ = kml(fn_, XD + 1700, YD + 700 + 100 * k_, [("InRot", "struct", dict(sub=ROT)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(_dcr, n_["InRot"])
    _dax.append(n_["ReturnValue"])
def _vmc(x, y, v, c):
    n = kml("Multiply_VectorFloat", x, y, [("A", "struct", dict(sub=VEC)), ("B", "real", dict(subcat="double", extra=f'DefaultValue="{c}",')),
                                           ("ReturnValue", "struct", dict(sub=VEC, out=True))])
    g.link(v, n["A"])
    return n["ReturnValue"]


_dpt = vop("Add_VectorVector", XD + 2300, YD + 700, _dcl,
           vop("Add_VectorVector", XD + 2100, YD + 750,
               _vmc(XD + 1900, YD + 700, _dax[0], "55.0"),
               vop("Add_VectorVector", XD + 2000, YD + 850,
                   _vmc(XD + 1900, YD + 800, _dax[1], "-14.0"),
                   _vmc(XD + 1900, YD + 900, _dax[2], "-8.0"))))
sdc1 = set_from("ItemCenter", "struct", XD + 1700, YD, _dpt, "reach target: lower left ahead (empty hands)", sub=VEC)
g.link(sdpl["then"], sdc1["execute"])
nd = inc("NDoor", XD + 1700, YD, "count door touches")
g.link(sdc1["then"], nd["execute"])
#     door build A (tester: "opening always plays a push and closing a pull, but doors can be in any state: a locker
#     opens toward you"; research: BP_DoorView leaves swing +-90 deg on a physics constraint, lockers / closets are
#     BP_OpeningContainer doors): the game moves the door at the press; we remember the point of the leaf under the
#     crosshair (in the leaf's own frame) and wait until it moves: toward the camera = a pull, away = a push. Not moved
#     within DoorDecideMax s: the old rule (open now = closing = pull). The touch starts when decided (step T7).
_dlc = self_get("LookComp", "object", XD + 1900, YD + 300, sub=PRIM)
_dxf = member_pure(SC_, "K2_GetComponentToWorld", XD + 2100, YD + 300, _dlc, [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
_dil = kml("InverseTransformLocation", XD + 2300, YD + 300, [("T", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC)),
                                                            ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_dxf, _dil["T"])
g.link(self_get("LookPoint", "struct", XD + 2100, YD + 400, sub=VEC), _dil["Location"])
chain(nd, set_from("DoorComp", "object", XD + 2000, YD, _dlc, "the leaf pressed", sub=PRIM),
      set_from("DoorLocal", "struct", XD + 2300, YD, _dil["ReturnValue"], "its point under the crosshair, leaf frame", sub=VEC),
      set_from("DoorW0", "struct", XD + 2600, YD, self_get("LookPoint", "struct", XD + 2500, YD + 200, sub=VEC), "that point at the press, world", sub=VEC),
      set_from("DoorCam0", "struct", XD + 2900, YD, _dcl, "the camera at the press", sub=VEC),
      set_from("DoorPressAt", "real", XD + 3200, YD, now(XD + 3100, YD + 200), "", subcat="double"),
      self_set("DoorWaiting", "bool", XD + 3500, YD, "wait for the leaf to move (T7)", default="true"))
bku = branch(XT + 2300, YT + 5800, "released this tick? (or F reads up while we wait for tap-or-hold)",
             b_or(XT + 2200, YT + 6000, self_get("KeyUp", "bool", XT + 2000, YT + 6000),
                  b_and(XT + 2000, YT + 6100, int_eq(XT + 1800, YT + 6100, tstate(XT + 1600, YT + 6100), 1),
                        b_not(XT + 1800, YT + 6200, self_get("KeyHeld", "bool", XT + 1600, YT + 6200)))))
g.link(bkd["else"], bku["execute"])
g.link(bku["then"], brel["execute"])

#   T5: still held HoldToDrag s after the press, no release = the game's hold interaction (drag a body): our context
#   off so the held key reaches IA_Interact (plus one injected press so the game sees it at once), hand back (T2's chain)
bt5 = branch(XT + 400, YT + 3300, "key still held HoldToDrag after the press? the game's hold (carry a body): vanilla, nothing of ours",
             b_and(XT + 300, YT + 3500, int_eq(XT + 100, YT + 3500, tstate(XT - 100, YT + 3500), 1),
                   d_op("GreaterEqual_DoubleDouble", XT + 200, YT + 3650,
                        d_op("Subtract_DoubleDouble", XT, YT + 3650, now(XT - 200, YT + 3650), tp(XT - 200, YT + 3750)),
                        self_get("HoldToDrag", "real", XT, YT + 3800, subcat="double"), ret=RB)))
g.link(sqt["then_5"], bt5["execute"])
ts5 = self_set("TouchState", "int", XT + 700, YT + 3300, "idle (the idle step switches its tap interaction back on)", default="0")
g.link(bt5["then"], ts5["execute"])

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
_cbr4 = kml("BreakRotator", XT + 4000, YT + 3700, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                  ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(_cr4, _cbr4["InRot"])
tpr.append(set_from("CamPitch", "real", XT + 6200, YT + 2500, _cbr4["Pitch"], "view pitch (probe)", subcat="double"))
_gis4 = member_pure(ANIMI, "Montage_GetIsStopped", XT + 6300, YT + 2700, anim, [("Montage", "object", dict(sub=MONT)), RB])
_gis4.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", XT + 6100, YT + 2700, sub=MONT), _gis4["Montage"])
tpr.append(set_from("TouchStopped", "bool", XT + 6500, YT + 2500, _gis4["ReturnValue"], "our montage stopped / gone (probe)"))
tpr.append(set_from("BagUsing", "bool", XT + 6800, YT + 2500, member_pure(PC, "IsUsingBackpack", XT + 6600, YT + 2700, as_pc, [RB])["ReturnValue"], "the game using the backpack (probe)"))
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
_c2then = c2["then"]
_c2n = lib_pure(KSL, "KismetSystemLibrary", "GetClassDisplayName", X2 + 450, Y2 + 350, [("Class", "class", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
_c2c = lib_pure(GS, "GameplayStatics", "GetObjectClass", X2 + 300, Y2 + 350, [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "class", dict(sub=OBJ, out=True))])
g.link(c2["AsInteractable Item Container"], _c2c["Object"])
g.link(_c2c["ReturnValue"], _c2n["Class"])


def _sw(x, y, lit):
    n = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "StartsWith", x, y,
                 [("SourceString", "string"), ("InPrefix", "string", dict(extra=f'DefaultValue="{lit}",')),
                  ("SearchCase", "byte", dict(sub=EN("/Script/CoreUObject.ESearchCase"), extra='DefaultValue="IgnoreCase",')), RB])
    g.link(_c2n["ReturnValue"], n["SourceString"])
    return n["ReturnValue"]


bli = branch(X2 + 500, Y2 - 150, "a loose item (not a stash: BP_StashBackpack and co. are item containers too), not during our hold catch?",
             b_and(X2 + 450, Y2 + 450, b_or(X2 + 650, Y2 + 450, _sw(X2 + 600, Y2 + 400, "BP_StaticItemContainer_C"), _sw(X2 + 600, Y2 + 500, "BP_SkeletalItemContainer_C")),
                   b_not(X2 + 650, Y2 + 550, self_get("PreReach", "bool", X2 + 450, Y2 + 550))))
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
_pull = kml("SelectFloat", X3 - 300, Y3 + 850, [D("A", "0.001"), D("B", "0.12"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(self_get("HideItem", "bool", X3 - 500, Y3 + 900), _pull["bPickA"])   # n2j: HideItem = in the hand at once
g.link(d_op("Divide_DoubleDouble", X3 - 100, Y3 + 750, since_grab, _pull["ReturnValue"]), cl["Value"])
alpha = cl["ReturnValue"]
_bone_w = member_pure(SKC, "GetSocketLocation", X3 - 900, Y3 + 900, mesh,
                   [("InSocketName", "name", dict(extra=f'DefaultValue="{HAND}",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
# build 44 (tester: "the item doesn't go into the palm, it attaches to the wrist"): empty hands, the item is held at the palm
# (60 % of the way from the wrist jnt_l_hand to the middle finger's knuckle), not at the item bone jnt_l_weapon
_wr = member_pure(SKC, "GetSocketLocation", X3 - 1100, Y3 + 1000, mesh, [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_hand",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_kn = member_pure(SKC, "GetSocketLocation", X3 - 1100, Y3 + 1100, mesh, [("InSocketName", "name", dict(extra='DefaultValue="jnt_l_hand_middle_01",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_palm = kml("VLerp", X3 - 950, Y3 + 1050, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)), ("Alpha", "real", dict(subcat="float", extra='DefaultValue="0.6",')),
                                         ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_wr, _palm["A"])
g.link(_kn, _palm["B"])
_bsel = kml("SelectVector", X3 - 800, Y3 + 950, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)), ("bPickA", "bool", dict(extra='DefaultValue="false",')),
                                               ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_palm["ReturnValue"], _bsel["A"])
g.link(_bone_w, _bsel["B"])
g.link(pick_bh(X3 - 1000, Y3 + 1200), _bsel["bPickA"])
bone = _bsel["ReturnValue"]
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
BOX = "\"/Script/CoreUObject.ScriptStruct'/Script/CoreUObject.Box'\""
#   the item's centre in its own axes (static meshes; else its pivot)
_bb = member_pure(SM, "GetBoundingBox", X3 - 300, Y3 + 2300, self_get("ItemMesh", "object", X3 - 500, Y3 + 2300, sub=SM),
                  [("ReturnValue", "struct", dict(sub=BOX, out=True))])["ReturnValue"]
_bc = kml("GetBoxCenter", X3 - 100, Y3 + 2300, [("InBox", "struct", dict(sub=BOX)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
_bc.pins["InBox"].ref = True
_bc.pins["InBox"].const = True
g.link(_bb, _bc["InBox"])
_cz = kml("SelectVector", X3 + 100, Y3 + 2300, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)),
                                               ("bPickA", "bool", dict(extra='DefaultValue="false",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_bc["ReturnValue"], _cz["A"])
g.link(is_valid(X3 - 100, Y3 + 2450, self_get("ItemMesh", "object", X3 - 300, Y3 + 2450, sub=SM)), _cz["bPickA"])
#   the hand bone's world transform; the held turn = FlyRel composed with it
_sock = member_pure(SKC, "GetSocketTransform", X3 - 300, Y3 + 2600, mesh,
                    [("InSocketName", "name", dict(extra=f'DefaultValue="{HAND}",')),
                     ("TransformSpace", "byte", dict(sub=EN("/Script/Engine.ERelativeTransformSpace"), extra='DefaultValue="RTS_World",')),
                     ("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"]
_hc = kml("ComposeTransforms", X3 - 100, Y3 + 2700, [("A", "struct", dict(sub=XFORM)), ("B", "struct", dict(sub=XFORM)), ("ReturnValue", "struct", dict(sub=XFORM, out=True))])
g.link(self_get("FlyRel", "struct", X3 - 300, Y3 + 2750, sub=XFORM), _hc["A"])
g.link(_sock, _hc["B"])
_hcb = kml("BreakTransform", X3 + 100, Y3 + 2700, [("InTransform", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC, out=True)),
                                                  ("Rotation", "struct", dict(sub=ROT, out=True)), ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(_hc["ReturnValue"], _hcb["InTransform"])
_ixb = kml("BreakTransform", X3 + 100, Y3 + 2900, [("InTransform", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC, out=True)),
                                                  ("Rotation", "struct", dict(sub=ROT, out=True)), ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(self_get("ItemXf", "struct", X3 - 100, Y3 + 2950, sub=XFORM), _ixb["InTransform"])
# build 26 (tester: "an upright item going into the hand would clip through the fingers; it needs to rotate as it
# animates into the hand so it looks truly held"): during the pull it turns from how it lay to the hand's item axes
# (jnt_l_weapon: the axes the game holds items by; at the vanilla grab frame its Z points up), then stays in them
_sbr = kml("BreakTransform", X3 + 100, Y3 + 3100, [("InTransform", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC, out=True)),
                                                  ("Rotation", "struct", dict(sub=ROT, out=True)), ("Scale", "struct", dict(sub=VEC, out=True))])
# build 26b (tester: "the item is pointing up instead of to the right, clipping through the fingers"): the item's up axis
# goes along the axis the fingers wrap around (index to pinky knuckles = the socket's -X at the vanilla grab frame):
# the socket turned by pitch 90 (Z -> -X)
_algn = kml("MakeTransform", X3 - 100, Y3 + 3250, [("Location", "struct", dict(sub=VEC)), ("Rotation", "struct", dict(sub=ROT, extra='DefaultValue="90.000000,0.000000,0.000000",')),
                                                  ("Scale", "struct", dict(sub=VEC, extra='DefaultValue="1.000000,1.000000,1.000000",')), ("ReturnValue", "struct", dict(sub=XFORM, out=True))])
_gx = kml("ComposeTransforms", X3 + 100, Y3 + 3250, [("A", "struct", dict(sub=XFORM)), ("B", "struct", dict(sub=XFORM)), ("ReturnValue", "struct", dict(sub=XFORM, out=True))])
g.link(_algn["ReturnValue"], _gx["A"])
g.link(_sock, _gx["B"])
g.link(_gx["ReturnValue"], _sbr["InTransform"])
_rsel = kml("RLerp", X3 + 300, Y3 + 2800, [("A", "struct", dict(sub=ROT)), ("B", "struct", dict(sub=ROT)),
                                          ("Alpha", "real", dict(subcat="float", extra='DefaultValue="0.0",')),
                                          ("bShortestPath", "bool", dict(extra='DefaultValue="true",')), ("ReturnValue", "struct", dict(sub=ROT, out=True))])
g.link(_ixb["Rotation"], _rsel["A"])
g.link(_sbr["Rotation"], _rsel["B"])
# g.link(alpha, _rsel["Alpha"])   # build 41: alpha 0 = the item keeps how it lay (no turn into the grip)
held_rot = _rsel["ReturnValue"]
#   where the pivot goes so the centre sits on the hand as drawn
_mt = kml("MakeTransform", X3 + 500, Y3 + 2800, [("Location", "struct", dict(sub=VEC)), ("Rotation", "struct", dict(sub=ROT)), ("Scale", "struct", dict(sub=VEC)),
                                                ("ReturnValue", "struct", dict(sub=XFORM, out=True))])
g.link(held_rot, _mt["Rotation"])
g.link(_ixb["Scale"], _mt["Scale"])
_off = kml("TransformLocation", X3 + 700, Y3 + 2800, [("T", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC)), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(_mt["ReturnValue"], _off["T"])
g.link(_cz["ReturnValue"], _off["Location"])
_crr = kml("SelectFloat", X3 + 700, Y3 + 2900, [D("A", "0.0"), D("B", "5.0"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(self_get("AimStand", "bool", X3 + 500, Y3 + 2950), _crr["bPickA"])
_crv = vop("Multiply_VectorFloat", X3 + 850, Y3 + 2850, cr_, _crr["ReturnValue"], b_cat="real", b_sub="None", b_subcat="double")
held_pos = vop("Add_VectorVector", X3 + 1000, Y3 + 2750, vop("Subtract_VectorVector", X3 + 900, Y3 + 2700, hand, _off["ReturnValue"]), _crv)   # build 48: crouched +5 cm right
_sv5 = kml("SelectVector", X3 + 450, Y3 + 450, [("A", "struct", dict(sub=VEC)), ("B", "struct", dict(sub=VEC)),
                                               ("bPickA", "bool", dict(extra='DefaultValue="false",')), ("ReturnValue", "struct", dict(sub=VEC, out=True))])
g.link(held_pos, _sv5["A"])
g.link(bone, _sv5["B"])
g.link(pick_bh(X3 + 250, Y3 + 550), _sv5["bPickA"])
g.link(_sv5["ReturnValue"], ve["B"])   # build 26: empty hands: its centre to the hand as drawn
g.link(alpha, ve["Alpha"])
pos = ve["ReturnValue"]


sq3 = sequence(X3 + 300, Y3, "copy steps", 4)
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
bat = branch(X3 + 1300, Y3 + 250, "reached the hand, not parented yet? (with a weapon; empty hands: held as drawn, below)",
             b_and(X3 + 1150, Y3 + 450, d_op("GreaterEqual_DoubleDouble", X3 + 950, Y3 + 450, alpha, b_const="1.0", ret=RB),
                   b_not(X3 + 950, Y3 + 550, attached(X3 + 750, Y3 + 550)),
                   b_not(X3 + 950, Y3 + 620, pick_bh(X3 + 750, Y3 + 620))))
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
_pt = kml("SelectFloat", X3 + 500, Y3 + 1000, [D("A", "1.2"), D("B"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(self_get("PocketTime", "real", X3 + 300, Y3 + 1050, subcat="double"), _pt["B"])
g.link(pick_bh(X3 + 300, Y3 + 1120), _pt["bPickA"])   # build 38: empty hands: when the hand is down
pocket = d_op("GreaterEqual_DoubleDouble", X3 + 700, Y3 + 850, montage_time_since_reach(X3 + 500, Y3 + 850),
              _pt["ReturnValue"], ret=RB)   # build 28: a pickup in the use pose: when the hand is back down
stale = d_op("Greater_DoubleDouble", X3 + 700, Y3 + 1050, el, b_const="3.0", ret=RB)
bp = branch(X3 + 1250, Y3 + 600, "pocketed? (or stuck for 3 s)", b_or(X3 + 1050, Y3 + 900, pocket, stale))
g.link(sq3["then_2"], bp["execute"])
#   build 26, empty hands: at the grab its turn relative to the hand is kept; from then on it turns with the hand
_bh1 = branch(X3 + 1500, Y3 + 3300, "empty hands, at the hand, not held yet? keep its turn relative to the hand",
              b_and(X3 + 1400, Y3 + 3500, pick_bh(X3 + 1200, Y3 + 3350), b_not(X3 + 1200, Y3 + 3420, self_get("FlyHeld", "bool", X3 + 1000, Y3 + 3420)),
                    d_op("GreaterEqual_DoubleDouble", X3 + 1200, Y3 + 3500, alpha, b_const="1.0", ret=RB)))
_sq5 = sequence(X3 + 1100, Y3 + 3200, "build 26: held copy", 2)
g.link(sq3["then_3"], _sq5["execute"])
g.link(_sq5["then_0"], _bh1["execute"])
_frel = kml("MakeRelativeTransform", X3 + 1700, Y3 + 3600, [("A", "struct", dict(sub=XFORM)), ("RelativeTo", "struct", dict(sub=XFORM)),
                                                           ("ReturnValue", "struct", dict(sub=XFORM, out=True))])
g.link(member_pure(ACTOR, "GetTransform", X3 + 1500, Y3 + 3700, fly(X3 + 1300, Y3 + 3750), [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"], _frel["A"])
g.link(_sock, _frel["RelativeTo"])
chain(_bh1, set_from("FlyRel", "struct", X3 + 1800, Y3 + 3300, _frel["ReturnValue"], "its turn relative to the hand", sub=XFORM),
      self_set("FlyHeld", "bool", X3 + 2100, Y3 + 3300, "", default="true"),
      # build 29 probe: the hand as DRAWN at the grab, camera axes, and the view pitch (calibration of the pickup aim)
      *[set_from(v, "real", X3 + 2400 + 300 * k, Y3 + 3300, vop("Dot_VectorVector", X3 + 2300 + 300 * k, Y3 + 3450, hrel, ax, ret_sub="real"),
                 "hand as drawn at the grab (probe)" if k == 0 else "", subcat="double") for k, (v, ax) in enumerate((("GrabFwd", cf_), ("GrabRight", cr_), ("GrabUp", cu_)))],
      set_from("GrabPitch", "real", X3 + 3300, Y3 + 3300, _cbr["Pitch"], "view pitch at the grab (probe)", subcat="double"))
_bh2 = branch(X3 + 1500, Y3 + 3900, "empty hands? it turns into the hand (during the pull) and with it", pick_bh(X3 + 1300, Y3 + 4000))
g.link(_sq5["then_1"], _bh2["execute"])
_sar = member_call(ACTOR, "K2_SetActorRotation", X3 + 1900, Y3 + 3900, fly(X3 + 1700, Y3 + 4000), "turns with the hand",
                   [("NewRotation", "struct", dict(sub=ROT)), B("bTeleportPhysics", "true"), RB])
g.link(held_rot, _sar["NewRotation"])
g.link(_bh2["then"], _sar["execute"])
fdx = member_call(ACTOR, "K2_DestroyActor", X3 + 1550, Y3 + 600, fly(X3 + 1400, Y3 + 800), "gone into the pocket")
g.link(bp["then"], fdx["execute"])

# ---- 6: recover the left hand if our montage was cut ----
X4, Y4 = 1200, 7600
g.box("EdGraphNode_Comment_905", X4 - 80, Y4 - 200, 2600, 1100, "Reach cut short? Put the left hand back on the weapon")
br4 = branch(X4, Y4, "our reach ended?", b_and(X4 - 100, Y4 + 250, self_get("Reaching", "bool", X4 - 300, Y4 + 200),
                                                b_not(X4 - 300, Y4 + 300, grab_active(X4 - 500, Y4 + 300))))
sq6 = sequence(X4 - 400, Y4 - 400, "end steps", 5)
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
_bur = branch(X4 + 600, Y4 - 700, "build 17: our use reach? the game's use animation goes on", self_get("UseMode", "bool", X4 + 400, Y4 - 550))
g.link(mst["then"], _bur["execute"])
_mru = member_call(ANIMI, "Montage_Resume", X4 + 900, Y4 - 700, anim, "the use goes on", [("Montage", "object", dict(sub=MONT))])
g.link(self_get("UseMont", "object", X4 + 700, Y4 - 550, sub=MONT), _mru["Montage"])
_bpk1 = branch(X4 + 750, Y4 - 900, "build 28: a pickup in the use pose? its held animation stops (not resumed)", self_get("PickUse", "bool", X4 + 550, Y4 - 800))
g.link(_bur["then"], _bpk1["execute"])
g.link(_bpk1["else"], _mru["execute"])
_mst1 = member_call(ANIMI, "Montage_Stop", X4 + 1050, Y4 - 950, anim, "the use pose goes", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.250000",')), ("Montage", "object", dict(sub=MONT))])
g.link(self_get("UseMont", "object", X4 + 850, Y4 - 800, sub=MONT), _mst1["Montage"])
g.link(_bpk1["then"], _mst1["execute"])
_spk1 = self_set("PickUse", "bool", X4 + 1350, Y4 - 950, "", default="false")
g.link(_mst1["then"], _spk1["execute"])
_umf1 = self_set("UseMode", "bool", X4 + 1200, Y4 - 700, "", default="false")
g.link(_spk1["then"], _umf1["execute"])
chain(_mru, _umf1, inc("NUseResume", X4 + 1500, Y4 - 700, "count (probe)"))
# v0.2: corpse / stash touch: pause at the touch frame (0.5 s montage time) while the window is open; when the hand,
# playing backwards after the window closed, is back at the segment start, stop the montage
sqh = sequence(X4 + 700, Y4 - 1400, "touch steps", 2)
g.link(sq6["then_2"], sqh["execute"])
_pos2 = member_pure(ANIMI, "Montage_GetPosition", X4 + 500, Y4 - 1700, anim, [("Montage", "object", dict(sub=MONT)), ("ReturnValue", "real", dict(subcat="float", out=True))])
_pos2.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 300, Y4 - 1700, sub=MONT), _pos2["Montage"])
seg0 = lambda x, y: self_get("SegStart", "real", x, y, subcat="double")
_sdt = kml("SelectFloat", X4 + 300, Y4 - 1800, [D("A", "0.4"), D("B", "0.467"), B("bPickA"), RD])   # build 15: pull pauses at frame 12, push at 14
g.link(self_get("DoorPulling", "bool", X4 + 100, Y4 - 1750), _sdt["bPickA"])
_sto = kml("SelectFloat", X4 + 500, Y4 - 1800, [D("A"), D("B", "0.6"), B("bPickA"), RD])
g.link(_sdt["ReturnValue"], _sto["A"])
g.link(self_get("DoorTouch", "bool", X4 + 300, Y4 - 1650), _sto["bPickA"])
_sbg = kml("SelectFloat", X4 + 700, Y4 - 1900, [D("A", "1.4"), D("B"), B("bPickA"), RD])   # build e: the bag In plays to its end (the right hand into the bag)
g.link(_sto["ReturnValue"], _sbg["B"])
g.link(self_get("BagMode", "bool", X4 + 500, Y4 - 1950), _sbg["bPickA"])
_spt = kml("SelectFloat", X4 + 900, Y4 - 2000, [D("A", "1.233"), D("B"), B("bPickA"), RD])   # n2c: the pats end at frame 37
g.link(_sbg["ReturnValue"], _spt["B"])
g.link(self_get("PatMode", "bool", X4 + 700, Y4 - 2050), _spt["bPickA"])
_touch_at = _spt["ReturnValue"]
at_touch = d_op("GreaterEqual_DoubleDouble", X4 + 900, Y4 - 1700, _pos2["ReturnValue"],
                d_op("Add_DoubleDouble", X4 + 700, Y4 - 1600, seg0(X4 + 500, Y4 - 1600), _touch_at), ret=RB)
bhold = branch(X4 + 1100, Y4 - 1500, "touching the corpse / stash? hold there",
               b_and(X4 + 1000, Y4 - 1300, self_get("LootReach", "bool", X4 + 800, Y4 - 1300),
                     b_not(X4 + 800, Y4 - 1200, self_get("LootPaused", "bool", X4 + 600, Y4 - 1200)),
                     b_not(X4 + 800, Y4 - 1100, self_get("LootReverse", "bool", X4 + 600, Y4 - 1100)),
                     grab_active(X4 + 600, Y4 - 1000), at_touch))
g.link(sqh["then_0"], bhold["execute"])
mpa = member_call(ANIMI, "Montage_Pause", X4 + 1400, Y4 - 1500, anim, "hold", [("Montage", "object", dict(sub=MONT))])
mpa.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 1200, Y4 - 1350, sub=MONT), mpa["Montage"])
_bbh = branch(X4 + 1250, Y4 - 1700, "build e: the bag? its idle (the right hand in the bag) while the window is open, as the game's inventory", self_get("BagMode", "bool", X4 + 1050, Y4 - 1600))
g.link(bhold["then"], _bbh["execute"])
g.link(_bbh["else"], mpa["execute"])
_lp = self_set("LootPaused", "bool", X4 + 1700, Y4 - 1500, "", default="true")
g.link(mpa["then"], _lp["execute"])
_spa = set_from("PausedAt", "real", X4 + 2000, Y4 - 1500, now(X4 + 1850, Y4 - 1300), "hand out since", subcat="double")
g.link(_lp["then"], _spa["execute"])
BAG_IDLE = "/ImmersiveLooting/Runtime/AS_ImmLoot_BagIdle.AS_ImmLoot_BagIdle"
BAG_ANIM_IDLE = "/Game/_STALKER2/Animations/item/bpa/AnimSequences/AS_backpack_fp_inventory_idle.AS_backpack_fp_inventory_idle"
_bia = member_call(SKC, "PlayAnimation", X4 + 2450, Y4 - 1900, bag_comp(X4 + 2250, Y4 - 1700), "the bag's half, looping", [
    ("NewAnimToPlay", "object", dict(sub=ANIMASSET, extra=f'DefaultObject="{BAG_ANIM_IDLE}",')), B("bLooping", "true")])
_mbid = montage_play(X4 + 1850, Y4 - 1900, anim, AM_BAG_IDLE, None, "the bag's idle: the arms (the right hand in the bag)")
chain(_bbh, stop_mont(X4 + 1550, Y4 - 1900, AM_BAG_IN, 0.05, "the In goes"), _mbid, grab_is(X4 + 2150, Y4 - 1900, AM_BAG_IDLE), _bia)
g.link(_bia["then"], _lp["execute"])
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
# armed: the game's own "left hand back on the item" (its notify switches the left-hand IK back on: the hand re-grips)
bgr = branch(X4 + 2600, Y4 - 900, "weapon in hand? put the left hand back on it", obj_q("HasItemInMainHand", X4 + 2400, Y4 - 700, as_pc))
g.link(bk3["then"], bgr["execute"])
mrg = montage_play(X4 + 2900, Y4 - 900, anim, RETURN, None, "hand back on the grip")
g.link(bgr["then"], mrg["execute"])
g.link(mrg["then"], set_from("RetAt", "real", X4 + 3200, Y4 - 900, now(X4 + 3050, Y4 - 700), "played at (step 6c)", subcat="double")["execute"])

bmst = branch(X4 + 1250, Y4 - 1000, "still ours to stop?", grab_active(X4 + 1050, Y4 - 1050))
g.link(bback["then"], bmst["execute"])
g.link(bmst["then"], mst2["execute"])
g.link(bmst["else"], bk1["execute"])
sr4 = self_set("Reaching", "bool", X4 + 300, Y4, "", default="false")
g.link(br4["then"], sr4["execute"])
cut = d_op("Less_DoubleDouble", X4 + 300, Y4 + 400, montage_time_since_reach(X4 + 100, Y4 + 400),
           self_get("IKOnTime", "real", X4 + 100, Y4 + 550, subcat="double"), ret=RB)
# 1.1.2: not when a game montage started this instant (it is what stopped ours: an item's use, the weapon put away;
# MG_fp_return_left_hand_on_item would play over it and, in the same montage group, stop it)
_gm_new = d_op("Less_DoubleDouble", X4 + 300, Y4 + 850,
               d_op("Subtract_DoubleDouble", X4 + 100, Y4 + 850, now(X4 - 100, Y4 + 850),
                    self_get("GameMontageAt", "real", X4 - 100, Y4 + 920, subcat="double")), b_const="0.1", ret=RB)
br4b = branch(X4 + 600, Y4, "cut before the hand-on-grip notify, weapon held, no other left-hand montage, not by a game montage?",
              b_and(X4 + 500, Y4 + 300, cut, obj_q("HasItemInMainHand", X4 + 300, Y4 + 650, as_pc),
                    b_not(X4 + 300, Y4 + 750, slot_active(X4 + 100, Y4 + 750, anim, "LeftHand")),
                    b_not(X4 + 400, Y4 + 850, _gm_new)))
g.link(sr4["then"], br4b["execute"])
mr = montage_play(X4 + 950, Y4, anim, RETURN, None, "hand back on the grip")
g.link(br4b["then"], mr["execute"])
nrc = inc("NRecover", X4 + 1300, Y4, "count recoveries")
g.link(mr["then"], nrc["execute"])
g.link(nrc["then"], set_from("RetAt", "real", X4 + 1600, Y4, now(X4 + 1450, Y4 + 200), "played at (step 6c)", subcat="double")["execute"])

# ---- 6c (1.1.2): an item's use started while our montage is on its way back after the loot window (or while our
# "hand back on the grip" plays): ours goes at once. LeftHand comes after MainActionSlot in every arm layer and FullBody
# after everything; the use (ActionGroup) does not stop them, so they posed the arm over the use. ----
g.box("EdGraphNode_Comment_940", X4 - 480, Y4 + 1000, 5400, 3000, "An item's use started while ours plays? Ours goes")
sqy = sequence(X4 - 400, Y4 + 1200, "yield to an item's use", 5)
g.link(sq6["then_3"], sqy["execute"])
_back = lambda x, y: self_get("BackAt", "real", x, y, subcat="double")
by1 = branch(X4 + 300, Y4 + 1200, "on its way back after the window, and a game montage started since? ours goes, no hand-back",
             b_and(X4 + 200, Y4 + 1400, grab_active(X4, Y4 + 1400), b_not(X4, Y4 + 1480, self_get("BagMode", "bool", X4 - 200, Y4 + 1480)),
                   d_op("GreaterEqual_DoubleDouble", X4, Y4 + 1550, _back(X4 - 200, Y4 + 1550), self_get("ReachStart", "real", X4 - 200, Y4 + 1620, subcat="double"), ret=RB),
                   d_op("Greater_DoubleDouble", X4, Y4 + 1700, self_get("GameMontageAt", "real", X4 - 200, Y4 + 1700, subcat="double"), _back(X4 - 200, Y4 + 1770), ret=RB),
                   d_op("Less_DoubleDouble", X4, Y4 + 1850, d_op("Subtract_DoubleDouble", X4 - 200, Y4 + 1850, now(X4 - 400, Y4 + 1850), _back(X4 - 400, Y4 + 1920)),
                        b_const="3.0", ret=RB)))
g.link(sqy["then_0"], by1["execute"])
_mp1 = member_call(ANIMI, "Montage_Pause", X4 + 600, Y4 + 1200, anim, "frozen (no hand-on-grip notify over the use)", [("Montage", "object", dict(sub=MONT))])
_mp1.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 400, Y4 + 1400, sub=MONT), _mp1["Montage"])
_ms1 = member_call(ANIMI, "Montage_Stop", X4 + 900, Y4 + 1200, anim, "out quickly", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.100000",')), ("Montage", "object", dict(sub=MONT))])
_ms1.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 700, Y4 + 1400, sub=MONT), _ms1["Montage"])
chain(_mp1, _ms1, inc("NYield", X4 + 1200, Y4 + 1200, "count (probe)"))
g.link(by1["then"], _mp1["execute"])
reach_over(X4 + 1500, Y4 + 1200, [n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"])
by2 = branch(X4 + 300, Y4 + 2000, "our hand-back on the grip playing, and an item's use (MainActionSlot) started after it? it goes",
             b_and(X4 + 200, Y4 + 2200, montage_active(X4, Y4 + 2200, anim, RETURN), slot_active(X4, Y4 + 2280, anim, "MainActionSlot"),
                   d_op("Greater_DoubleDouble", X4, Y4 + 2350, self_get("GameMontageAt", "real", X4 - 200, Y4 + 2350, subcat="double"),
                        self_get("RetAt", "real", X4 - 200, Y4 + 2420, subcat="double"), ret=RB)))
g.link(sqy["then_1"], by2["execute"])
_ms2 = member_call(ANIMI, "Montage_Stop", X4 + 600, Y4 + 2000, anim, "out quickly", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.100000",')),
    ("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{RETURN}",'))])
_ms2.pins["Montage"].const = True
g.link(by2["then"], _ms2["execute"])
g.link(_ms2["then"], inc("NYield", X4 + 900, Y4 + 2000, "count (probe)")["execute"])
def loot_use_go(x, y, exec_in):
    """The item's use held for us: our use reach next (step 3); the touch kept until that reach starts (step 6c)."""
    gis = member_pure(ANIMI, "Montage_GetIsStopped", x - 400, y + 350, anim, [("Montage", "object", dict(sub=MONT)), RB])
    gis.pins["Montage"].const = True
    g.link(self_get("GrabMontage", "object", x - 600, y + 350, sub=MONT), gis["Montage"])
    slfg = set_from("LootFromGrab", "bool", x, y,
                    b_and(x - 100, y + 300, b_not(x - 300, y + 300, gis["ReturnValue"]), b_not(x - 300, y + 400, self_get("BagMode", "bool", x - 500, y + 400))),
                    "our touch still out (not the bag)? the reach starts there")
    # build c (tester: "the hand starts to reach back, then resets and does the full reach back"): our touch was stopped
    # here, a tick before the use reach started: it blended toward the held use pose, then the reach put the hand back
    # out. It is kept now and stopped in the tick the reach starts (below)
    slt = set_from("LootTouchMont", "object", x + 300, y, self_get("GrabMontage", "object", x + 100, y + 200, sub=MONT),
                   "our touch / bag: stopped when the use reach starts", sub=MONT)
    g.link(exec_in, slfg["execute"])
    # build g (tester: "a frame or flash of the arm disappearing and swapping"): from the grab frame the item is in the
    # hand at once: the game's item meshes are not hidden for a frame first (step 7's twins: hidden until the grab)
    sug = set_from("UseGrabbed", "bool", x + 150, y - 200, self_get("LootFromGrab", "bool", x - 50, y - 100), "the item already in the hand")
    # ... and the backpack (the use stopped the bag's montage; an additive bag is stopped with our touch) goes now
    bbv = branch(x + 300, y - 400, "the backpack out? it goes", is_valid(x + 200, y - 300, bag_actor(x, y - 300)))
    bdv = member_call(ACTOR, "K2_DestroyActor", x + 550, y - 400, bag_actor(x + 350, y - 200), "the backpack goes")
    bmf = self_set("BagMode", "bool", x + 800, y - 400, "", default="false")
    chain(slfg, sug, bbv, bdv, bmf, slt)
    g.link(bbv["else"], slt["execute"])
    _spm = self_set("PatMode", "bool", x + 450, y + 200, "n2: the pat is over", default="false")
    g.link(slt["then"], _spm["execute"])
    ro = reach_over(x + 600, y, _spm["then"])
    chain(ro, self_set("LootUse", "bool", x + 2100, y, "", default="false"),
          self_set("LootWait", "bool", x + 2400, y, "", default="false"),
          self_set("PendingCopy", "bool", x + 2700, y, "no copy", default="false"),
          self_set("PendingReach", "bool", x + 3000, y, "our use reach (step 3)", default="true"))


#   an item used from the loot window, held on its first frame (step 7), and the window gone: our touch / bag goes and
#   the use reach plays over the held use (step 3, as a hold to use), from its grab frame after a touch held at the body
by3 = branch(X4 + 300, Y4 + 2600, "an item's use held for us and the loot window gone? our use reach over it",
             b_and(X4 + 200, Y4 + 2800, self_get("LootUse", "bool", X4, Y4 + 2800), b_not(X4 + 100, Y4 + 2870, inv)))
g.link(sqy["then_2"], by3["execute"])
loot_use_go(X4 + 600, Y4 + 2600, by3["then"])#   the held touch / bag goes in the tick our use reach started (step 3 runs before this step), or was skipped
_ltm = lambda x, y: self_get("LootTouchMont", "object", x, y, sub=MONT)
by5 = branch(X4 + 300, Y4 + 3900, "our touch kept for the use reach, and the reach started (or was skipped)? it goes now",
             b_and(X4 + 200, Y4 + 4100, is_valid(X4, Y4 + 4100, _ltm(X4 - 200, Y4 + 4100)),
                   b_not(X4 + 100, Y4 + 4170, self_get("PendingReach", "bool", X4 - 100, Y4 + 4170))))
g.link(sqy["then_4"], by5["execute"])
_ms5 = member_call(ANIMI, "Montage_Stop", X4 + 600, Y4 + 3900, anim, "under the use reach's blend-in", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.150000",')), ("Montage", "object", dict(sub=MONT))])
_ms5.pins["Montage"].const = True
g.link(_ltm(X4 + 400, Y4 + 4100), _ms5["Montage"])
chain(by5, _ms5, self_set("LootTouchMont", "object", X4 + 900, Y4 + 3900, "done", sub=MONT))
#   waited 1 s after the window and no use came: ours goes, no return (another game action took the arms)
by4 = branch(X4 + 300, Y4 + 3300, "waited 1 s after the window, no use came? ours goes",
             b_and(X4 + 200, Y4 + 3500, self_get("LootWait", "bool", X4, Y4 + 3500), b_not(X4 + 100, Y4 + 3570, self_get("LootUse", "bool", X4 - 100, Y4 + 3570)),
                   d_op("Greater_DoubleDouble", X4 + 100, Y4 + 3640,
                        d_op("Subtract_DoubleDouble", X4 - 100, Y4 + 3640, now(X4 - 300, Y4 + 3640), self_get("LootWaitAt", "real", X4 - 300, Y4 + 3710, subcat="double")),
                        b_const="1.0", ret=RB)))
g.link(sqy["then_3"], by4["execute"])
_ms4 = member_call(ANIMI, "Montage_Stop", X4 + 600, Y4 + 3300, anim, "out quickly", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.100000",')), ("Montage", "object", dict(sub=MONT))])
_ms4.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X4 + 400, Y4 + 3500, sub=MONT), _ms4["Montage"])
chain(by4, _ms4, self_set("LootWait", "bool", X4 + 900, Y4 + 3300, "", default="false"), inc("NYield", X4 + 1200, Y4 + 3300, "count (probe)"))
reach_over(X4 + 1500, Y4 + 3300, [n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"])

# ---- 6d (1.1.2): the backpack goes when its animation has played out, or at once when a game montage (an item's use)
# took the arms from our bag montage ----
g.box("EdGraphNode_Comment_941", X4 - 480, Y4 + 4200, 2600, 2200, "The backpack goes when it is done (or an item's use took over)")
_bpl = member_pure(SKC, "IsPlaying", X4 - 100, Y4 + 4600, bag_comp(X4 - 300, Y4 + 4600), [RB])["ReturnValue"]
bcl = branch(X4 + 300, Y4 + 4400, "backpack out, and its animation over (not held) or a game montage took over? it goes",
             b_and(X4 + 200, Y4 + 4600, is_valid(X4, Y4 + 4550, bag_actor(X4 - 200, Y4 + 4550)),
                   b_or(X4 + 100, Y4 + 4700,
                        b_and(X4, Y4 + 4700, b_not(X4 - 100, Y4 + 4700, self_get("LootPaused", "bool", X4 - 300, Y4 + 4700)), b_not(X4 - 100, Y4 + 4770, _bpl)),
                        b_and(X4, Y4 + 4850, b_not(X4 - 100, Y4 + 4850, grab_active(X4 - 300, Y4 + 4850)),
                              d_op("Greater_DoubleDouble", X4 - 100, Y4 + 4920, self_get("GameMontageAt", "real", X4 - 300, Y4 + 4920, subcat="double"),
                                   self_get("BagAt", "real", X4 - 300, Y4 + 4990, subcat="double"), ret=RB)),
                        # 1.3.1 watchdog: no touch out, none of the bag montages playing, 1 s after it started
                        b_and(X4, Y4 + 5050, b_not(X4 - 100, Y4 + 5050, self_get("LootReach", "bool", X4 - 300, Y4 + 5050)),
                              b_not(X4 - 100, Y4 + 5120, montage_active(X4 - 300, Y4 + 5120, anim, AM_BAG_IN)),
                              b_not(X4 - 100, Y4 + 5190, montage_active(X4 - 300, Y4 + 5190, anim, AM_BAG_IDLE)),
                              b_not(X4 - 100, Y4 + 5260, montage_active(X4 - 300, Y4 + 5260, anim, AM_BAG_OUT)),
                              d_op("Greater_DoubleDouble", X4 - 100, Y4 + 5330,
                                   d_op("Subtract_DoubleDouble", X4 - 300, Y4 + 5330, now(X4 - 500, Y4 + 5330), self_get("BagAt", "real", X4 - 500, Y4 + 5400, subcat="double")),
                                   b_const="1.0", ret=RB)))))
_sqb = sequence(X4 - 400, Y4 + 4400, "backpack steps", 2)
g.link(sq6["then_4"], _sqb["execute"])
#   (6d below: the weapon back, then the cleanup)
#   (release cleanup 2026-10-13: the backpack / hand probes of builds l-za removed)
_bcm = lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", X4 - 300, Y4 + 5700,
                [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)),
                 ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"]
_bdes = member_call(ACTOR, "K2_DestroyActor", X4 + 600, Y4 + 4400, bag_actor(X4 + 400, Y4 + 4600), "the backpack goes")
g.link(bcl["then"], _bdes["execute"])
_sbm0 = self_set("BagMode", "bool", X4 + 900, Y4 + 4400, "", default="false")
g.link(_bdes["then"], _sbm0["execute"])
#   build f: played out (no game montage took over), empty hands: the game's own hands-up after its bag (MG_fp_bh_equip)
BH_EQUIP = "/Game/_STALKER2/Animations/Player/AnimSequences/bh/showhide/Montages/MG_fp_bh_equip.MG_fp_bh_equip"
_bnat = branch(X4 + 1200, Y4 + 4400, "build f: played out with empty hands? the game's hands-up after its bag",
               b_and(X4 + 1100, Y4 + 4600, b_not(X4 + 900, Y4 + 4600, self_get("BagWeapon", "bool", X4 + 700, Y4 + 4600)),
                     b_not(X4 + 900, Y4 + 4530, obj_q("HasItemInMainHand", X4 + 700, Y4 + 4530, as_pc)),   # build p: BagWeapon is cleared at the equip
                     b_not(X4 + 900, Y4 + 4700, d_op("Greater_DoubleDouble", X4 + 700, Y4 + 4700, self_get("GameMontageAt", "real", X4 + 500, Y4 + 4700, subcat="double"),
                                                     self_get("BagAt", "real", X4 + 500, Y4 + 4770, subcat="double"), ret=RB))))
g.link(_sbm0["then"], _bnat["execute"])
g.link(_bnat["then"], montage_play(X4 + 1500, Y4 + 4400, anim, BH_EQUIP, None, "hands up (the game's)")["execute"])
#   build m: the weapon hidden for the bag: shown again once the bag is gone (it never left the hands)
_sqb2 = sequence(X4 - 400, Y4 + 6300, "backpack, then the weapon back", 3)
g.link(_sqb["then_1"], _sqb2["execute"])
g.link(_sqb2["then_0"], bcl["execute"])
_bwd = branch(X4 + 300, Y4 + 6300, "our hidden weapon, the bag gone? shown again",
              b_and(X4 + 200, Y4 + 6500, self_get("BagWeapon", "bool", X4, Y4 + 6450),
                    b_not(X4 + 100, Y4 + 6520, is_valid(X4 - 100, Y4 + 6520, bag_actor(X4 - 300, Y4 + 6520))),
                    b_not(X4 + 100, Y4 + 6590, self_get("PatMode", "bool", X4 - 100, Y4 + 6590))))
g.link(_sqb2["then_1"], _bwd["execute"])
_wmc = member_pure(OBJC, "GetWeaponInHandsMeshComponent", X4 + 300, Y4 + 6700, as_pc, [("ReturnValue", "object", dict(sub=SKC, out=True))])["ReturnValue"]
chain(_bwd, member_call(SC_, "SetHiddenInGame", X4 + 600, Y4 + 6300, _wmc, "shown", [B("NewHidden", "false"), B("bPropagateToChildren", "true")]),
      self_set("BagWeapon", "bool", X4 + 900, Y4 + 6300, "", default="false"))
#   build m, empty hands: the pitch-fix pose table at the view pitch while the bag is out (0 crouched: the low-crouch
#   look turns the arms rigidly already), stopped when the bag is gone
_pfm = lambda x, y: self_get("PitchFixMont", "object", x, y, sub=MONT)
_sqpf = sequence(X4 - 400, Y4 + 8600, "pitch fix, bag shown, Out ended, weapon shown, pat end", 6)
g.link(_sqb2["then_2"], _sqpf["execute"])
_bpfx = branch(X4 + 300, Y4 + 8600, "build m: the pitch fix running and the bag out? its frame from the view pitch",
              b_and(X4 + 200, Y4 + 8800, is_valid(X4, Y4 + 8800, _pfm(X4 - 200, Y4 + 8800)),
                    b_or(X4 + 100, Y4 + 8900, is_valid(X4, Y4 + 8870, bag_actor(X4 - 200, Y4 + 8870)), self_get("PatMode", "bool", X4 - 200, Y4 + 8940))))
g.link(_sqpf["then_0"], _bpfx["execute"])
_pfr = member_pure(PCM, "GetCameraRotation", X4 - 300, Y4 + 9000, _bcm, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_pfb = kml("BreakRotator", X4 - 100, Y4 + 9000, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(_pfr, _pfb["InRot"])
_pfc = kml("FClamp", X4 + 100, Y4 + 9000, [D("Value"), D("Min", "0.0"), D("Max", "90.0"), RD])
_pfn = kml("NormalizeAxis", X4 - 100, Y4 + 9200, [D("Angle"), RD])
g.link(_pfb["Pitch"], _pfn["Angle"])
g.link(d_op("Multiply_DoubleDouble", X4 - 100, Y4 + 9100, _pfn["ReturnValue"], b_const="-1.0"), _pfc["Value"])
_pfs = kml("SelectFloat", X4 + 300, Y4 + 9000, [D("A", "0.0"), D("B"), B("bPickA"), RD])
g.link(d_op("Divide_DoubleDouble", X4 + 200, Y4 + 9100, _pfc["ReturnValue"], b_const="30.0"), _pfs["B"])
#   crouched = the camera below 130 cm in the mesh frame (as the pickup's AimStand, build 41)
_pfz = kml("BreakVector", X4 - 100, Y4 + 9300, [("InVec", "struct", dict(sub=VEC)), ("X", "real", dict(subcat="double", out=True)),
                                               ("Y", "real", dict(subcat="double", out=True)), ("Z", "real", dict(subcat="double", out=True))])
g.link(_to_mesh(X4 - 300, Y4 + 9300, member_pure(PCM, "GetCameraLocation", X4 - 500, Y4 + 9400, _bcm, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]), _pfz["InVec"])
g.link(d_op("Less_DoubleDouble", X4 + 100, Y4 + 9300, _pfz["Z"], b_const="130.0", ret=RB), _pfs["bPickA"])
_pfp = member_call(ANIMI, "Montage_SetPosition", X4 + 600, Y4 + 8600, anim, "frame = view pitch down (deg) / 30 fps", [
    ("Montage", "object", dict(sub=MONT)), ("NewPosition", "real", dict(subcat="float"))])
g.link(_pfm(X4 + 400, Y4 + 8800), _pfp["Montage"])
g.link(_pfs["ReturnValue"], _pfp["NewPosition"])
g.link(_bpfx["then"], _pfp["execute"])
_bpe = branch(X4 + 300, Y4 + 9400, "build m: the pitch fix running and the bag gone? it goes",
              b_and(X4 + 200, Y4 + 9600, is_valid(X4, Y4 + 9600, _pfm(X4 - 200, Y4 + 9600)), b_not(X4 + 100, Y4 + 9670, is_valid(X4 - 100, Y4 + 9670, bag_actor(X4 - 300, Y4 + 9670))),
                    b_not(X4 + 100, Y4 + 9740, self_get("PatMode", "bool", X4 - 100, Y4 + 9740))))
g.link(_sqpf["then_1"], _bpe["execute"])
_pfst = member_call(ANIMI, "Montage_Stop", X4 + 600, Y4 + 9400, anim, "out with the bag", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.300000",')), ("Montage", "object", dict(sub=MONT))])
_pfst.pins["Montage"].const = True
g.link(_pfm(X4 + 400, Y4 + 9600), _pfst["Montage"])
chain(_bpe, _pfst, self_set("PitchFixMont", "object", X4 + 900, Y4 + 9400, "done", sub=MONT))
#   build o: the bag shown after its first ticks
_bgt = kml("Greater_IntInt", X4 - 100, Y4 + 10340, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="0",')), RB])
g.link(self_get("BagShowTick", "int", X4 - 300, Y4 + 10340), _bgt["A"])
g.link(self_get("NTicks", "int", X4 - 300, Y4 + 10400), _bgt["B"])
_bsh = branch(X4 + 300, Y4 + 10000, "build o: the bag out, its first ticks over? shown",
              b_and(X4 + 200, Y4 + 10200, is_valid(X4, Y4 + 10200, bag_actor(X4 - 200, Y4 + 10200)),
                    kml_int_gt(X4 - 100, Y4 + 10270, self_get("BagShowTick", "int", X4 - 300, Y4 + 10270), "0"),
                    b_not(X4 + 100, Y4 + 10340, _bgt["ReturnValue"])))
g.link(_sqpf["then_2"], _bsh["execute"])
chain(_bsh, member_call(ACTOR, "SetActorHiddenInGame", X4 + 600, Y4 + 10000, bag_actor(X4 + 400, Y4 + 10200), "shown", [B("bNewHidden", "false")]),
      self_set("BagShowTick", "int", X4 + 900, Y4 + 10000, "done", default="0"))
#   build o (tester: closing, "the backpack turns in place instead of going down and off screen with the left hand";
#   probe: it rose from (38, -17, -27) to (47, 0, -18) cm in view = back to the weapon's grip. The Out's 0.3 s blend-out
#   started at 0.37 s (the arms back to the weapon while the bag still showed), and the game's Out holds the bag below
#   the view only from frame 16-18 (0.6 s; its last frame snaps behind the back). At 0.6 s: the Out held there and
#   blended out, the bag's own animation stopped (the cleanup takes the bag next tick, then the weapon shows)
_gpo = member_pure(ANIMI, "Montage_GetPosition", X4 - 100, Y4 + 10700, anim, [("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{AM_BAG_OUT}",')), ("ReturnValue", "real", dict(subcat="float", out=True))])
_gpo.pins["Montage"].const = True
_gso = member_pure(ANIMI, "Montage_GetIsStopped", X4 - 100, Y4 + 10800, anim, [("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{AM_BAG_OUT}",')), RB])
_gso.pins["Montage"].const = True
_boe = branch(X4 + 300, Y4 + 10600, "build o: the bag's Out at 0.6 s (the bag below the view)? it ends there",
              b_and(X4 + 200, Y4 + 10800, is_valid(X4, Y4 + 10650, bag_actor(X4 - 200, Y4 + 10650)), b_not(X4 + 100, Y4 + 10800, _gso["ReturnValue"]),
                    d_op("GreaterEqual_DoubleDouble", X4 + 100, Y4 + 10700, _gpo["ReturnValue"], b_const="0.6", ret=RB)))
g.link(_sqpf["then_3"], _boe["execute"])
_pbo = member_call(ANIMI, "Montage_Pause", X4 + 600, Y4 + 10600, anim, "held at 0.6 s", [("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{AM_BAG_OUT}",'))])
_pbo.pins["Montage"].const = True
_bstp = member_call(SKC, "Stop", X4 + 1200, Y4 + 10600, bag_comp(X4 + 1000, Y4 + 10800), "the bag's animation over (the cleanup takes it)")
chain(_boe, _pbo, stop_mont(X4 + 900, Y4 + 10600, AM_BAG_OUT, 0.25, "the arms back (0.25 s)"), _bstp)
#   build p (tester: "the weapon appears floating in the air and then the hands come up to grab it"): the game closes its
#   own bag with the weapon's equip (the weapon comes up in the hands); ours replays the last one the game played
#   (MainActionSlot; its notifies: both hands' IK on, left-hand idle unlock, "equip ended"), the weapon shown with it.
#   None remembered (no equip since the load): shown when the bag is gone, as before (6d)
_leq = lambda x, y: self_get("LastEquipMont", "object", x, y, sub=MONT)
_beq2 = branch(X4 + 1500, Y4 + 10600, "build p: our hidden weapon, an equip remembered? the game's equip brings it up",
               b_and(X4 + 1400, Y4 + 10800, self_get("BagWeapon", "bool", X4 + 1200, Y4 + 10800), is_valid(X4 + 1200, Y4 + 10870, _leq(X4 + 1000, Y4 + 10870))))
g.link(_bstp["then"], _beq2["execute"])
_mpe = montage_play(X4 + 1800, Y4 + 10600, anim, "None", None, "the weapon's equip (the game's)")
g.link(_leq(X4 + 1600, Y4 + 10800), _mpe["MontageToPlay"])
#   build q (tester: "I can see the weapon appear for a frame before the correct anim plays"): the equip poses the arms
#   from the next frame (this tick runs after the animation update), so the weapon is shown 2 ticks later
_wst = kml("Add_IntInt", X4 + 2000, Y4 + 10800, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="2",')), ("ReturnValue", "int", dict(out=True))])
g.link(self_get("NTicks", "int", X4 + 1800, Y4 + 10850), _wst["A"])
chain(_beq2, _mpe, set_from("EquipReplayAt", "real", X4 + 1800, Y4 + 10450, now(X4 + 1650, Y4 + 10350), "n2f: our replay (vs GameMontageAt)", subcat="double"),
      set_from("WeaponShowTick", "int", X4 + 2100, Y4 + 10600, _wst["ReturnValue"], "the weapon shown from this tick"),
      self_set("BagWeapon", "bool", X4 + 2400, Y4 + 10600, "", default="false"))
_wgt = kml("Greater_IntInt", X4 - 100, Y4 + 11340, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="0",')), RB])
g.link(self_get("WeaponShowTick", "int", X4 - 300, Y4 + 11340), _wgt["A"])
g.link(self_get("NTicks", "int", X4 - 300, Y4 + 11400), _wgt["B"])
_bws = branch(X4 + 300, Y4 + 11200, "build q: the equip under way 2 ticks? the weapon shown",
              b_and(X4 + 200, Y4 + 11300, kml_int_gt(X4 - 100, Y4 + 11270, self_get("WeaponShowTick", "int", X4 - 300, Y4 + 11270), "0"),
                    b_not(X4 + 100, Y4 + 11340, _wgt["ReturnValue"])))
g.link(_sqpf["then_4"], _bws["execute"])
#   n2: the pat at its segment's end (frame 48)? it goes, the hidden weapon comes back with the game's equip
_ppos = member_pure(ANIMI, "Montage_GetPosition", X4 - 100, Y4 + 12300, anim, [("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{AM_PAT}",')),
                                                                             ("ReturnValue", "real", dict(subcat="float", out=True))])
_ppos.pins["Montage"].const = True
_pend = branch(X4 + 300, Y4 + 12200, "n2: both hands back (segment + 1.6 s)? the pat goes, the weapon is drawn",
               b_and(X4 + 200, Y4 + 12400, self_get("PatMode", "bool", X4, Y4 + 12400),
                     d_op("GreaterEqual_DoubleDouble", X4 + 100, Y4 + 12500, _ppos["ReturnValue"],
                          d_op("Add_DoubleDouble", X4 - 100, Y4 + 12550, self_get("SegStart", "real", X4 - 300, Y4 + 12550, subcat="double"), b_const="1.6"), ret=RB)))
g.link(_sqpf["then_5"], _pend["execute"])
_ppa = member_call(ANIMI, "Montage_Pause", X4 + 600, Y4 + 12200, anim, "held there", [("Montage", "object", dict(sub=MONT, extra=f'DefaultObject="{AM_PAT}",'))])
_ppa.pins["Montage"].const = True
_pcl = [stop_mont(X4 + 900, Y4 + 12200, AM_PAT, 0.3, "out (0.3 s)"),
        self_set("PatMode", "bool", X4 + 1200, Y4 + 12200, "", default="false"),
        self_set("Reaching", "bool", X4 + 1500, Y4 + 12200, "no hand-back recovery", default="false")]
chain(_pend, _ppa, *_pcl)
_peq = branch(X4 + 1800, Y4 + 12200, "n2: our hidden weapon, an equip remembered? the game's equip brings it up",
              b_and(X4 + 1700, Y4 + 12400, self_get("BagWeapon", "bool", X4 + 1500, Y4 + 12400), is_valid(X4 + 1500, Y4 + 12470, self_get("LastEquipMont", "object", X4 + 1300, Y4 + 12470, sub=MONT))))
g.link(_pcl[-1]["then"], _peq["execute"])
_mpe2 = montage_play(X4 + 2100, Y4 + 12200, anim, "None", None, "the weapon's equip (the game's)")
g.link(self_get("LastEquipMont", "object", X4 + 1900, Y4 + 12400, sub=MONT), _mpe2["MontageToPlay"])
_wst2 = kml("Add_IntInt", X4 + 2300, Y4 + 12400, [("A", "int", dict(extra='DefaultValue="0",')), ("B", "int", dict(extra='DefaultValue="2",')), ("ReturnValue", "int", dict(out=True))])
g.link(self_get("NTicks", "int", X4 + 2100, Y4 + 12450), _wst2["A"])
chain(_peq, _mpe2, set_from("EquipReplayAt", "real", X4 + 2100, Y4 + 12050, now(X4 + 1950, Y4 + 11950), "n2f: our replay (vs GameMontageAt)", subcat="double"),
      set_from("WeaponShowTick", "int", X4 + 2400, Y4 + 12200, _wst2["ReturnValue"], "the weapon shown from this tick"),
      self_set("BagWeapon", "bool", X4 + 2700, Y4 + 12200, "", default="false"))
#   n2: a pat cut short (our montage gone with no touch out: a game montage, an item used from the window)? cleared, the
#   weapon is shown by 6d
_pcut = branch(X4 + 300, Y4 + 12800, "n2: the pat cut (not playing, no touch out)? cleared",
               b_and(X4 + 200, Y4 + 13000, self_get("PatMode", "bool", X4, Y4 + 13000),
                     b_not(X4, Y4 + 13070, self_get("LootReach", "bool", X4 - 200, Y4 + 13070)),
                     b_not(X4, Y4 + 13140, self_get("LootPaused", "bool", X4 - 200, Y4 + 13140)),
                     b_not(X4, Y4 + 13210, montage_active(X4 - 200, Y4 + 13210, anim, AM_PAT))))
_sqpe = sequence(X4 + 100, Y4 + 12000, "pat end / pat cut", 2)
for l_ in list(_sqpf["then_5"].links):
    _sqpf["then_5"].links.remove(l_); l_.links.remove(_sqpf["then_5"])
g.link(_sqpf["then_5"], _sqpe["execute"])
g.link(_sqpe["then_0"], _pend["execute"])
g.link(_sqpe["then_1"], _pcut["execute"])
chain(_pcut, self_set("PatMode", "bool", X4 + 600, Y4 + 12800, "", default="false"), inc("NPatCut", X4 + 900, Y4 + 12800, "count (probe)"))
_wme2 = member_pure(OBJC, "GetWeaponInHandsMeshComponent", X4 + 400, Y4 + 11400, as_pc, [("ReturnValue", "object", dict(sub=SKC, out=True))])["ReturnValue"]
chain(_bws, member_call(SC_, "SetHiddenInGame", X4 + 600, Y4 + 11200, _wme2, "shown, coming up with the hands", [B("NewHidden", "false"), B("bPropagateToChildren", "true")]),
      self_set("WeaponShowTick", "int", X4 + 900, Y4 + 11200, "done", default="0"))
g.layout_tree()
# ---- 7 (1.1, hold F to use a loose item): the game starts the item's use animation (MainActionSlot, blend-in 0) the
#      moment the hold completes and it owns the arms (probe: paused, it still hid our LeftHand reach; FullBody took the
#      camera). Its effect is applied by its own AnimNotify_UseConsumable, so: STOP it at once, let our reach take the
#      item, then play the same montage again ourselves (its notifies fire on our copy). Every montage the game starts
#      is remembered via OnMontageStarted (bound per anim instance, as in ImmersiveCampfires); our dynamic montages are
#      named AnimMontage_<n> and ignored; our own replay is ignored by time (ReplayAt). ----
X7, Y7 = 1200, 24000
g.box("EdGraphNode_Comment_917", X7 - 400, Y7 - 400, 5600, 5800, "Hold F to use: catch the hold, our whole grab, then give F back (the game's use follows)")
sq7 = sequence(X7 - 200, Y7, "use steps", 3)
g.link(sq["then_7"], sq7["execute"])
#   U0: bind OnMontageStarted on the current anim instance (once per instance)
bv7 = is_valid(X7 + 100, Y7 + 250, anim)
ne7 = kml("NotEqual_ObjectObject", X7 + 100, Y7 + 350, [("A", "object", dict(sub=OBJ)), ("B", "object", dict(sub=OBJ)), RB])
g.link(anim, ne7["A"])
g.link(self_get("BoundAnim", "object", X7 - 100, Y7 + 400, sub=ANIMI), ne7["B"])
br7 = branch(X7 + 300, Y7, "anim instance not bound yet?", b_and(X7 + 250, Y7 + 300, bv7, ne7["ReturnValue"]))
g.link(sq7["then_0"], br7["execute"])
EVN = "OnGameMontageStarted"
add7 = exec_pins(Node(g, BG + "K2Node_AddDelegate", nm("K2Node_AddDelegate"), X7 + 600, Y7, "bind: montage started",
                      [f'DelegateReference=(MemberParent={ANIMI},MemberName="OnMontageStarted")']))
add7.pin("self", "object", sub=ANIMI, extra='PinFriendlyName=NSLOCTEXT("K2Node", "BaseMCDelegateSelfPinName", "Target"),')
add7.pin("Delegate", "delegate", extra='PinFriendlyName=NSLOCTEXT("K2Node", "PinFriendlyDelegatetName", "Event"),')
add7.pins["Delegate"].member_ref = 'MemberParent="/Script/CoreUObject.Package' + "'/Script/Engine'" + '",MemberName="OnMontageStartedMCDelegate__DelegateSignature"'
g.link(anim, add7["self"])
g.link(br7["then"], add7["execute"])
sb7 = set_from("BoundAnim", "object", X7 + 950, Y7, anim, "bound to this anim instance", sub=ANIMI)
g.link(add7["then"], sb7["execute"])
ev7 = Node(g, BG + "K2Node_CustomEvent", nm("K2Node_CustomEvent"), X7, Y7 + 700, "the game started a montage",
           [f'CustomFunctionName="{EVN}"',
            'CustomProperties UserDefinedPin (PinName="Montage",PinType=(PinCategory="object",PinSubCategoryObject=' + MONT + '),DesiredPinDirection=EGPD_Output)'])
ev7.pin("OutputDelegate", "delegate", out=True)
ev7.pins["OutputDelegate"].member_ref = f'MemberName="{EVN}",bSelfContext=True'
ev7.pin("then", "exec", out=True)
ev7.pin("Montage", "object", sub=MONT, out=True)
g.link(ev7["OutputDelegate"], add7["Delegate"])
on7 = lib_pure(KSL, "KismetSystemLibrary", "GetObjectName", X7 + 300, Y7 + 950, [("Object", "object", dict(sub=OBJ)), ("ReturnValue", "string", dict(out=True))])
g.link(ev7["Montage"], on7["Object"])
ours7 = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "StartsWith", X7 + 500, Y7 + 950,
                 [("SourceString", "string"), ("InPrefix", "string", dict(extra='DefaultValue="AnimMontage",')),
                  ("SearchCase", "byte", dict(sub=EN("/Script/CoreUObject.ESearchCase"), extra='DefaultValue="IgnoreCase",')), RB])
g.link(on7["ReturnValue"], ours7["SourceString"])
_ours7b = lib_pure(cls("/Script/Engine.KismetStringLibrary"), "KismetStringLibrary", "StartsWith", X7 + 500, Y7 + 1050,
                   [("SourceString", "string"), ("InPrefix", "string", dict(extra='DefaultValue="AM_ImmLoot",')),
                    ("SearchCase", "byte", dict(sub=EN("/Script/CoreUObject.ESearchCase"), extra='DefaultValue="IgnoreCase",')), RB])
g.link(on7["ReturnValue"], _ours7b["SourceString"])
# build l: our bag montage assets (AM_ImmLoot_*) are ours too (build k: they counted as the game's: no hands-up after the bag)
bg7 = branch(X7 + 400, Y7 + 700, "not one of ours (a dynamic montage, or our AM_ImmLoot montages)?",
             b_not(X7 + 700, Y7 + 900, b_or(X7 + 650, Y7 + 950, ours7["ReturnValue"], _ours7b["ReturnValue"])))
g.link(ev7["then"], bg7["execute"])
sgm7 = set_from("GameMontage", "object", X7 + 700, Y7 + 700, ev7["Montage"], "the last montage the game started", sub=MONT)
sga7 = set_from("GameMontageAt", "real", X7 + 1000, Y7 + 700, now(X7 + 850, Y7 + 900), "when", subcat="double")
g.link(bg7["then"], sgm7["execute"])
chain(sgm7, sga7)


def _has(x, y, lit):
    n = lib_pure(KSTR, "KismetStringLibrary", "Contains", x, y,
                 [("SearchIn", "string"), ("Substring", "string", dict(extra=f'DefaultValue="{lit}",')),
                  ("bUseCase", "bool", dict(extra='DefaultValue="false",')), ("bSearchFromEnd", "bool", dict(extra='DefaultValue="false",')), RB])
    g.link(on7["ReturnValue"], n["SearchIn"])
    return n["ReturnValue"]


_isuse = b_and(X7 + 1300, Y7 + 1000, b_or(X7 + 1150, Y7 + 1000, _has(X7 + 950, Y7 + 1000, "_use"), _has(X7 + 950, Y7 + 1080, "PIR")),
               b_not(X7 + 1150, Y7 + 1100, _has(X7 + 950, Y7 + 1160, "equip")))
_waiting = b_and(X7 + 1450, Y7 + 950, self_get("UseWait", "bool", X7 + 1250, Y7 + 900),
                 d_op("Less_DoubleDouble", X7 + 1250, Y7 + 1250,
                      d_op("Subtract_DoubleDouble", X7 + 1050, Y7 + 1250, now(X7 + 850, Y7 + 1250),
                           self_get("UseWaitAt", "real", X7 + 850, Y7 + 1320, subcat="double")), b_const="2.5", ret=RB), _isuse)
_bpu = branch(X7 + 1300, Y7 + 700, "build 17: the use animation of a hold we skipped? pause it on its first frame, our reach plays over it", _waiting)
_sgn7 = set_from("GameMontageName", "string", X7 + 1150, Y7 + 550, on7["ReturnValue"], "its name (probe)")
g.link(sga7["then"], _sgn7["execute"])
#   (probe, numbers only: a String read from UE4SS crashed the game) what kind of montage, and how long
_kind = None
for code, lit in ((5, "inventory"), (6, "interact"), (7, "pick"), (4, "backpack"), (2, "equip"), (1, "unequip"), (3, "_use")):   # later wins; 5-7: 1.3.1 probe
    s_ = kml("SelectInt", X7 + 1300 + 100 * code, Y7 + 200, [("A", "int", dict(extra=f'DefaultValue="{code}",')), ("B", "int", dict(extra='DefaultValue="0",')),
                                                            B("bPickA"), ("ReturnValue", "int", dict(out=True))])
    g.link(_has(X7 + 1100 + 100 * code, Y7 + 100, lit), s_["bPickA"])
    if _kind is not None:
        g.link(_kind, s_["B"])
    _kind = s_["ReturnValue"]
_sgk = set_from("GameMontageKind", "int", X7 + 1800, Y7 + 550, _kind, "1 unequip 2 equip 3 use 4 backpack 0 other (probe)")
_sgl = set_from("GameMontageLen", "real", X7 + 2100, Y7 + 550,
                member_pure(cls("/Script/Engine.AnimationAsset"), "GetPlayLength", X7 + 1900, Y7 + 750, ev7["Montage"], [("ReturnValue", "real", dict(subcat="float", out=True))])["ReturnValue"],
                "its length (probe)", subcat="double")
chain(_sgn7, _sgk, _sgl)
#   build f (probe: as the loot window goes, the game first plays the hands' / weapon's "unequip" (0.43-0.47 s) and only
#   then the item's use; our touch rode the lowering shoulders: "the hand starts to reach back, then resets"): an unequip
#   while our touch is out, or just after it, is played 8x as fast; the use follows at once
_bun = branch(X7 + 2400, Y7 + 550, "build f: the unequip before an item used from the loot window? fast",
              b_and(X7 + 2300, Y7 + 700, int_eq(X7 + 2100, Y7 + 700, self_get("GameMontageKind", "int", X7 + 1900, Y7 + 700), 1),
                    b_or(X7 + 2200, Y7 + 800, self_get("LootReach", "bool", X7 + 2000, Y7 + 800), self_get("LootWait", "bool", X7 + 2000, Y7 + 870))))
#   build p: the game's last weapon equip (kind 2, not the bare hands' MG_fp_bh_equip), replayed after a bag with a weapon
_beq = branch(X7 + 2400, Y7 + 300, "build p: a weapon's equip? remembered (the bag's close replays it)",
              b_and(X7 + 2300, Y7 + 400, int_eq(X7 + 2100, Y7 + 400, self_get("GameMontageKind", "int", X7 + 1900, Y7 + 400), 2),
                    b_not(X7 + 2200, Y7 + 450, _has(X7 + 2000, Y7 + 450, "_bh_"))))
#   n2g: the game's pick-up (carry) montage started though F is up and was pressed less than HoldToDrag ago (a tap; the
#   probe: a 0.06 s tap carried the body within a tick): remembered, the carry is dropped (T9)
_btc = branch(X7 + 2400, Y7 + 1000, "n2g: the carry's pick-up started from a tap? dropped (T9)",
              b_and(X7 + 2300, Y7 + 1150, int_eq(X7 + 2100, Y7 + 1150, self_get("GameMontageKind", "int", X7 + 1900, Y7 + 1150), 7),
                    b_not(X7 + 2100, Y7 + 1220, self_get("KeyHeld", "bool", X7 + 1900, Y7 + 1220)),
                    d_op("Less_DoubleDouble", X7 + 2100, Y7 + 1290,
                         d_op("Subtract_DoubleDouble", X7 + 1900, Y7 + 1290, now(X7 + 1700, Y7 + 1290),
                              self_get("InteractPressAt", "real", X7 + 1700, Y7 + 1360, subcat="double")),
                         self_get("HoldToDrag", "real", X7 + 1900, Y7 + 1430, subcat="double"), ret=RB)))
g.link(_sgl["then"], _btc["execute"])
_stc = self_set("TapCarry", "bool", X7 + 2700, Y7 + 1000, "drop it", default="true")
chain(_btc, _stc, set_from("TapCarryAt", "real", X7 + 3000, Y7 + 1000, now(X7 + 2850, Y7 + 1150), "", subcat="double"),
      inc("NTapCarryPick", X7 + 3300, Y7 + 1000, "count (probe)"))
g.link([n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"], _beq["execute"])
g.link(_btc["else"], _beq["execute"])
_sle = set_from("LastEquipMont", "object", X7 + 2700, Y7 + 300, ev7["Montage"], "the weapon's equip", sub=MONT)
chain(_beq, _sle)
g.link(_sle["then"], _bun["execute"])
g.link(_beq["else"], _bun["execute"])
_spr = member_call(ANIMI, "Montage_SetPlayRate", X7 + 2700, Y7 + 550, self_get("BoundAnim", "object", X7 + 2500, Y7 + 700, sub=ANIMI), "8x", [
    ("Montage", "object", dict(sub=MONT)), ("NewPlayRate", "real", dict(subcat="float", extra='DefaultValue="8.000000",'))])
_spr.pins["Montage"].const = True
g.link(ev7["Montage"], _spr["Montage"])
g.link(_bun["then"], _spr["execute"])
g.link(_spr["then"], _bpu["execute"])
g.link(_bun["else"], _bpu["execute"])   # build 19: the pause is back (item twins paused too)
_mpu = member_call(ANIMI, "Montage_Pause", X7 + 1600, Y7 + 700, self_get("BoundAnim", "object", X7 + 1400, Y7 + 850, sub=ANIMI), "held on its first frame",
                   [("Montage", "object", dict(sub=MONT))])
g.link(ev7["Montage"], _mpu["Montage"])
g.link(_bpu["then"], _mpu["execute"])
chain(_mpu, set_from("UseMont", "object", X7 + 1900, Y7 + 700, ev7["Montage"], "the paused use animation", sub=MONT),
      self_set("UseMode", "bool", X7 + 2200, Y7 + 700, "", default="true"),
      self_set("UseGrabbed", "bool", X7 + 2200, Y7 + 550, "", default="false"),
      self_set("UseWait", "bool", X7 + 2500, Y7 + 700, "", default="false"),
      set_from("UsePausedAt", "real", X7 + 2800, Y7 + 700, now(X7 + 2650, Y7 + 900), "", subcat="double"),
      self_set("PendingReach", "bool", X7 + 3100, Y7 + 700, "our reach (step 3, next tick)", default="true"),
      inc("NUsePause", X7 + 3400, Y7 + 700, "count (probe)"))
#   1.1.2 (tester: "when an item is used from the loot window our return animation should still play, with our custom
#   use animation like when holding F on a loose item, where we freeze on the first frame"): a use started while the
#   loot window is open and our touch / bag is out = held on its first frame like a hold to use (UseMode); when the
#   window closes, the use reach plays over it (from the hand at the body, taking the item), then the use goes on
# (build a test, 2026-10-12: the use does not start in the window; as it closes the game plays the hands' "unequip"
# (~0.4 s), then the use: our touch is still out then, or waiting for it: LootWait, set by the close step)
_blu = branch(X7 + 1300, Y7 + 400, "an item used from the loot window (our touch / bag out, or waiting after it)? hold it on its first frame",
              b_and(X7 + 1200, Y7 + 550, _isuse,
                    b_or(X7 + 1100, Y7 + 550, self_get("LootReach", "bool", X7 + 900, Y7 + 550), self_get("LootWait", "bool", X7 + 900, Y7 + 620)),
                    b_not(X7 + 1100, Y7 + 690, self_get("UseMode", "bool", X7 + 900, Y7 + 690))))
g.link(_bpu["else"], _blu["execute"])
_mplu = member_call(ANIMI, "Montage_Pause", X7 + 1600, Y7 + 400, self_get("BoundAnim", "object", X7 + 1400, Y7 + 550, sub=ANIMI), "held on its first frame",
                    [("Montage", "object", dict(sub=MONT))])
g.link(ev7["Montage"], _mplu["Montage"])
g.link(_blu["then"], _mplu["execute"])
chain(_mplu, set_from("UseMont", "object", X7 + 1900, Y7 + 400, ev7["Montage"], "the paused use animation", sub=MONT),
      self_set("UseMode", "bool", X7 + 2200, Y7 + 400, "", default="true"),
      self_set("UseGrabbed", "bool", X7 + 2500, Y7 + 400, "", default="false"),
      set_from("UsePausedAt", "real", X7 + 2800, Y7 + 400, now(X7 + 2650, Y7 + 600), "", subcat="double"),
      self_set("LootUse", "bool", X7 + 3100, Y7 + 400, "our use reach once the window is gone (step 6c)", default="true"),
      inc("NLootUse", X7 + 3400, Y7 + 400, "count (probe)"))
#   build f: the window already gone (the usual case: the use starts after the unequip)? our use reach in this same frame
#   (the game starts it before our tick), not two ticks later
_blug = branch(X7 + 3700, Y7 + 400, "build f: the loot window already gone? our use reach now", b_not(X7 + 3600, Y7 + 550, inv))
g.link([n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"], _blug["execute"])
loot_use_go(X7 + 4100, Y7 + 400, _blug["then"])
#   (1.1 build 9, tester on the pre-reach: "the grab plays but quickly and gets cut off; it should be the whole grab,
#   the hand back, THEN the use".) The game's hold to use completes 0.5 s after the press (probe) and its use animation
#   owns the arms. So the hold is stretched: F held 0.15 s on a loose item still there = a hold. Our IMC_ImmLoot then
#   swallows F (the game's hold is cut: past 20 % = no pickup on the cut), the item's mesh is hidden (step 1 sees it go:
#   our normal pickup reach plays with its flying copy); when our hand has pocketed it, our context goes (keys pressed
#   are NOT ignored) and the still-held F starts the game's hold again: 0.5 s later its use animation plays. F let go
#   while we hold it = the item shows again, nothing is taken.
pr = lambda x, y: self_get("PreReach", "bool", x, y)
capd = lambda x, y: self_get("Captured", "bool", x, y)
our_held = lambda x, y: d_op("Less_DoubleDouble", x + 200, y, d_op("Subtract_DoubleDouble", x, y, now(x - 200, y),
                                                                    self_get("KeySeenAt", "real", x - 200, y + 70, subcat="double")),
                              b_const="0.12", ret=RB)
hnd = lambda x, y: self_get("Handed", "bool", x, y)
hcomp = lambda x, y: self_get("HideComp", "object", x, y, sub=SC_)


def _ctx_remove(x, y, comment):
    n = ctx_call(x, y, "RemoveMappingContext", comment, False)
    n.pins["Options"].extra = 'DefaultValue="(bIgnoreAllPressedKeysUntilRelease=False,bForceImmediately=True,bForceRebuildWithFlush=False,bNotifyUserSettings=False)",'
    return n


def _set_vis(x, y, comp_pin, on, comment):
    n = member_call(SC_, "SetVisibility", x, y, comp_pin, comment, [B("bNewVisibility", "true" if on else "false"), B("bPropagateToChildren", "true")])
    return n


_held7 = d_op("GreaterEqual_DoubleDouble", X7 + 500, Y7 + 1400,
              d_op("Subtract_DoubleDouble", X7 + 300, Y7 + 1400, now(X7 + 100, Y7 + 1400),
                   self_get("InteractPressAt", "real", X7 + 100, Y7 + 1460, subcat="double")), b_const="0.42", ret=RB)   # tester: the prompt fills (nearly) completely first
# still looked at: seen by the tracking step within 0.15 s (the game's target or our trace), not only our trace
_eq7 = {"ReturnValue": d_op("Less_DoubleDouble", X7 + 500, Y7 + 1550,
                            d_op("Subtract_DoubleDouble", X7 + 300, Y7 + 1550, now(X7 + 100, Y7 + 1550),
                                 self_get("ItemSeen", "real", X7 + 100, Y7 + 1620, subcat="double")), b_const="0.15", ret=RB)}
sqh = sequence(X7 + 600, Y7 + 1000, "hold steps", 5)
g.link(sq7["then_1"], sqh["execute"])
#   H1: catch the hold
bh1 = branch(X7 + 900, Y7 + 1100, "F held 0.15 s on a loose item still there (a hold to use), nothing of ours on? catch it",
             b_and(X7 + 850, Y7 + 1300, b_not(X7 + 700, Y7 + 1200, pr(X7 + 500, Y7 + 1200)),
                   self_get("KeyHeld", "bool", X7 + 500, Y7 + 1260), _held7, self_get("ItemArmed", "bool", X7 + 500, Y7 + 1700),
                   is_valid(X7 + 500, Y7 + 1750, self_get("ItemComp", "object", X7 + 300, Y7 + 1750, sub=SC_)), _eq7["ReturnValue"],
                   b_not(X7 + 500, Y7 + 1820, grab_active(X7 + 300, Y7 + 1820)),
                   b_not(X7 + 500, Y7 + 1890, self_get("PendingReach", "bool", X7 + 300, Y7 + 1890)),
                   int_eq(X7 + 500, Y7 + 1960, tstate(X7 + 300, Y7 + 1960), 0)))
# g.link(sqh["then_0"], bh1["execute"])   # build 17: the hold catch is off (the game's hold runs untouched)
sut = set_from("UseTap", "object", X7 + 1000, Y7 + 900, member_pure(ACTOR, "GetComponentByClass", X7 + 800, Y7 + 1000, self_get("Item", "object", X7 + 600, Y7 + 1000, sub=ACTOR), [
    ("ComponentClass", "class", dict(sub=ACOMP, extra='DefaultObject="/Script/Stalker2.ItemContainerInteractionComponent",')),
    ("ReturnValue", "object", dict(sub=ICOMP, out=True))])["ReturnValue"], "the item's tap (pickup) interaction", sub=ICOMP)
g.link(bh1["then"], sut["execute"])
_bvt = branch(X7 + 1100, Y7 + 800, "has one?", is_valid(X7 + 1000, Y7 + 700, self_get("UseTap", "object", X7 + 800, Y7 + 700, sub=ICOMP)))
g.link(sut["then"], _bvt["execute"])
_off1 = member_call(ICOMP, "SetInteractionActive", X7 + 1200, Y7 + 700, self_get("UseTap", "object", X7 + 1000, Y7 + 600, sub=ICOMP), "off: cutting the hold picks nothing up",
                    [B("bActive", "false")])
g.link(_bvt["then"], _off1["execute"])


shc = set_from("HideComp", "object", X7 + 1600, Y7 + 1100, self_get("ItemComp", "object", X7 + 1450, Y7 + 1300, sub=SC_), "the item's mesh", sub=SC_)
g.link(_off1["then"], shc["execute"])
g.link(_bvt["else"], shc["execute"])
hv1 = _set_vis(X7 + 1900, Y7 + 1100, hcomp(X7 + 1750, Y7 + 1300), False, "hidden: step 1 sees it go, our reach and copy play")
g.link(shc["then"], hv1["execute"])
chain(hv1, self_set("Captured", "bool", X7 + 2200, Y7 + 1100, "", default="true"),
      self_set("PreReach", "bool", X7 + 2500, Y7 + 1100, "", default="true"),
      set_from("PreReachAt", "real", X7 + 2800, Y7 + 1100, now(X7 + 2650, Y7 + 1300), "", subcat="double"),
      inc("NCapture", X7 + 3100, Y7 + 1100, "count (probe)"))
#   H2: our hand has pocketed it: give F back to the game (its hold starts again)
_pocketed = b_and(X7 + 800, Y7 + 2300, grab_active(X7 + 600, Y7 + 2250),
                  d_op("Greater_DoubleDouble", X7 + 600, Y7 + 2320, self_get("ReachStart", "real", X7 + 400, Y7 + 2320, subcat="double"),
                       self_get("PreReachAt", "real", X7 + 400, Y7 + 2390, subcat="double"), ret=RB),
                  d_op("GreaterEqual_DoubleDouble", X7 + 600, Y7 + 2460, montage_time_since_reach(X7 + 400, Y7 + 2460),
                       self_get("PocketTime", "real", X7 + 400, Y7 + 2540, subcat="double"), ret=RB))
bh2 = branch(X7 + 900, Y7 + 2200, "caught, F still held, our hand has pocketed it? give F back to the game",
             b_and(X7 + 850, Y7 + 2400, capd(X7 + 650, Y7 + 2400), our_held(X7 + 450, Y7 + 2470), _pocketed))
g.link(sqh["then_1"], bh2["execute"])
rm2 = member_call(ICOMP, "SetInteractionActive", X7 + 1250, Y7 + 2200, self_get("UseTap", "object", X7 + 1250 - 200, Y7 + 2200 + 200, sub=ICOMP), "its tap back on (the game targets it again)", [B("bActive", "true")])
g.link(bh2["then"], rm2["execute"])
chain(rm2, self_set("Captured", "bool", X7 + 1600, Y7 + 2200, "", default="false"),
      self_set("Handed", "bool", X7 + 1900, Y7 + 2200, "", default="true"),
      set_from("HandedAt", "real", X7 + 2200, Y7 + 2200, now(X7 + 2050, Y7 + 2400), "", subcat="double"),
      inc("NHandBack", X7 + 2500, Y7 + 2200, "count (probe)"))
#   H3: F let go while caught: the item shows again, our hand and copy go
_upfor = d_op("GreaterEqual_DoubleDouble", X7 + 650, Y7 + 3240,
              d_op("Subtract_DoubleDouble", X7 + 450, Y7 + 3240, now(X7 + 250, Y7 + 3240), self_get("KeySeenAt", "real", X7 + 250, Y7 + 3310, subcat="double")),
              b_const="0.15", ret=RB)
_grace = d_op("GreaterEqual_DoubleDouble", X7 + 650, Y7 + 3380,
              d_op("Subtract_DoubleDouble", X7 + 450, Y7 + 3380, now(X7 + 250, Y7 + 3380), self_get("PreReachAt", "real", X7 + 250, Y7 + 3450, subcat="double")),
              b_const="0.3", ret=RB)
bh3 = branch(X7 + 900, Y7 + 2900, "caught and F let go (our action quiet 0.2 s, 0.3 s grace)? nothing taken: item back, hand back",
             b_and(X7 + 850, Y7 + 3100, capd(X7 + 650, Y7 + 3100), _upfor, _grace))
g.link(sqh["then_2"], bh3["execute"])
rm3a = member_call(ICOMP, "SetInteractionActive", X7 + 1050, Y7 + 2750, self_get("UseTap", "object", X7 + 1050 - 200, Y7 + 2750 + 200, sub=ICOMP), "its tap back on", [B("bActive", "true")])
g.link(bh3["then"], rm3a["execute"])

hv3 = _set_vis(X7 + 1550, Y7 + 2900, hcomp(X7 + 1400, Y7 + 3100), True, "the item shows again")
g.link(rm3a["then"], hv3["execute"])
ms3 = member_call(ANIMI, "Montage_Stop", X7 + 1850, Y7 + 2900, anim, "our reach back", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.300000",')), ("Montage", "object", dict(sub=MONT))])
ms3.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", X7 + 1650, Y7 + 3100, sub=MONT), ms3["Montage"])
g.link(hv3["then"], ms3["execute"])
bf3 = branch(X7 + 2150, Y7 + 2900, "our copy out?", is_valid(X7 + 2000, Y7 + 3100, self_get("Fly", "object", X7 + 1800, Y7 + 3200, sub=ACTOR)))
g.link(ms3["then"], bf3["execute"])
fd3 = member_call(ACTOR, "K2_DestroyActor", X7 + 2450, Y7 + 2900, self_get("Fly", "object", X7 + 2250, Y7 + 3100, sub=ACTOR), "remove it")
g.link(bf3["then"], fd3["execute"])
_clr3 = [self_set("Captured", "bool", X7 + 2750, Y7 + 2900, "", default="false"), self_set("PreReach", "bool", X7 + 3050, Y7 + 2900, "", default="false"),
         inc("NAbort", X7 + 3350, Y7 + 2900, "count (probe)")]
g.link(fd3["then"], _clr3[0]["execute"])
g.link(bf3["else"], _clr3[0]["execute"])
chain(*_clr3)
#   H4: handed back, and the game's use animation started (or F let go / 3 s: the item shows again if still there)
_used = d_op("Greater_DoubleDouble", X7 + 600, Y7 + 3600, self_get("GameMontageAt", "real", X7 + 400, Y7 + 3600, subcat="double"),
             self_get("HandedAt", "real", X7 + 400, Y7 + 3670, subcat="double"), ret=RB)
bh4 = branch(X7 + 900, Y7 + 3500, "handed back and the game's use animation started? done",
             b_and(X7 + 850, Y7 + 3700, hnd(X7 + 650, Y7 + 3700), _used))
g.link(sqh["then_3"], bh4["execute"])
chain(*[n_ for n_ in (self_set("Handed", "bool", X7 + 1250, Y7 + 3500, "use started", default="false"),
                      self_set("PreReach", "bool", X7 + 1550, Y7 + 3500, "", default="false"),
                      inc("NHandUse", X7 + 1850, Y7 + 3500, "count (probe)"))])
_h4first = [n_ for n_ in g.nodes if n_.klass.endswith("K2Node_VariableSet") and n_.comment == "use started"][-1]
g.link(bh4["then"], _h4first["execute"])
_late5 = d_op("Greater_DoubleDouble", X7 + 600, Y7 + 4300,
              d_op("Subtract_DoubleDouble", X7 + 400, Y7 + 4300, now(X7 + 200, Y7 + 4300), self_get("PreReachAt", "real", X7 + 200, Y7 + 4370, subcat="double")),
              b_const="4.0", ret=RB)
bh5 = branch(X7 + 900, Y7 + 4100, "handed back but F let go (no use), or 4 s? the item shows again if still there",
             b_and(X7 + 850, Y7 + 4300, b_or(X7 + 700, Y7 + 4200, hnd(X7 + 500, Y7 + 4200), capd(X7 + 500, Y7 + 4250)),
                   b_or(X7 + 700, Y7 + 4350, b_and(X7 + 550, Y7 + 4400, hnd(X7 + 350, Y7 + 4400),
                                                   b_not(X7 + 350, Y7 + 4460, our_held(X7 + 150, Y7 + 4460))), _late5)))
g.link(sqh["then_4"], bh5["execute"])
rm5a = member_call(ICOMP, "SetInteractionActive", X7 + 1050, Y7 + 3950, self_get("UseTap", "object", X7 + 1050 - 200, Y7 + 3950 + 200, sub=ICOMP), "its tap back on", [B("bActive", "true")])
g.link(bh5["then"], rm5a["execute"])

bv5 = branch(X7 + 1550, Y7 + 4100, "the item still there?", is_valid(X7 + 1400, Y7 + 4300, hcomp(X7 + 1200, Y7 + 4300)))
g.link(rm5a["then"], bv5["execute"])
hv5 = _set_vis(X7 + 1850, Y7 + 4100, hcomp(X7 + 1700, Y7 + 4300), True, "shows again")
g.link(bv5["then"], hv5["execute"])
_clr5 = [self_set("Handed", "bool", X7 + 2150, Y7 + 4100, "", default="false"), self_set("Captured", "bool", X7 + 2450, Y7 + 4100, "", default="false"),
         self_set("PreReach", "bool", X7 + 2750, Y7 + 4100, "", default="false"), inc("NAbort2", X7 + 3050, Y7 + 4100, "count (probe)")]
g.link(hv5["then"], _clr5[0]["execute"])
g.link(bv5["else"], _clr5[0]["execute"])
chain(*_clr5)
sqhx = sequence(X7 + 500, Y7 + 5200, "", 8)
_late = b_and(X7 + 850, Y7 + 5500, self_get("UseMode", "bool", X7 + 650, Y7 + 5450),
              b_not(X7 + 750, Y7 + 5400, self_get("LootUse", "bool", X7 + 550, Y7 + 5400)),   # 1.1.2: waiting for the loot window to close
              # 1.1.2 build b ("snaps down and right, then the use at once"; probe: this fail-safe fired the tick step 6c
              # asked for our reach, the use went on and the reach played as a plain pickup): not while one is pending
              b_not(X7 + 750, Y7 + 5330, self_get("PendingReach", "bool", X7 + 550, Y7 + 5330)),
              b_or(X7 + 700, Y7 + 5550, b_not(X7 + 550, Y7 + 5550, grab_active(X7 + 350, Y7 + 5550)),
                   d_op("Greater_DoubleDouble", X7 + 550, Y7 + 5650,
                        d_op("Subtract_DoubleDouble", X7 + 350, Y7 + 5650, now(X7 + 150, Y7 + 5650), self_get("UsePausedAt", "real", X7 + 150, Y7 + 5720, subcat="double")),
                        b_const="3.0", ret=RB)))
_bul = branch(X7 + 900, Y7 + 5300, "build 17 fail-safe: our use reach gone (or 3 s) and the use still paused? it goes on", _late)
g.link(sqhx["then_1"], _bul["execute"])
LX, LY = X7 + 4000, Y7 + 4700
g.box("EdGraphNode_Comment_931", LX - 400, LY - 300, 3200, 1500, "Build 18: hold F to use: the left hand 'off the item' while F is held, back when our grab is over")
_offc = b_and(LX - 100, LY + 200, self_get("KeyHeld", "bool", LX - 300, LY + 150),
              b_not(LX - 300, LY + 210, self_get("LHOff", "bool", LX - 500, LY + 210)),
              d_op("GreaterEqual_DoubleDouble", LX - 300, LY + 280,
                   d_op("Subtract_DoubleDouble", LX - 500, LY + 280, now(LX - 700, LY + 280),
                        self_get("InteractPressAt", "real", LX - 700, LY + 350, subcat="double")), b_const="0.25", ret=RB),
              self_get("ItemArmed", "bool", LX - 300, LY + 420), _eq7["ReturnValue"],
              int_eq(LX - 300, LY + 500, tstate(LX - 500, LY + 500), 0),
              b_not(LX - 300, LY + 570, self_get("DoorTouch", "bool", LX - 500, LY + 570)))
_bof = branch(LX, LY, "F held 0.25 s on a loose item (a hold to use coming)? the left hand 'off the item'", _offc)
# g.link(sqhx["then_2"], _bof["execute"])   # build 19: no left hand "off" (build 18: no effect)
_rmo = member_call(PC, "RemoveLeftHandFromItemEnded", LX + 300, LY, as_pc, "left hand off the item (the game's use waits for it?)")
g.link(_bof["then"], _rmo["execute"])
chain(_rmo, self_set("LHOff", "bool", LX + 650, LY, "", default="true"),
      set_from("LHOffAt", "real", LX + 950, LY, now(LX + 800, LY + 200), "", subcat="double"),
      inc("NLHOff", LX + 1250, LY, "count (probe)"))
_since_off = d_op("Subtract_DoubleDouble", LX - 500, LY + 900, now(LX - 700, LY + 900), self_get("LHOffAt", "real", LX - 700, LY + 970, subcat="double"))
_onc = b_and(LX - 100, LY + 800, self_get("LHOff", "bool", LX - 300, LY + 750),
             b_or(LX - 200, LY + 850,
                  b_and(LX - 300, LY + 850, d_op("Greater_DoubleDouble", LX - 400, LY + 850, _since_off, b_const="0.3", ret=RB),
                        b_not(LX - 400, LY + 1050, grab_active(LX - 600, LY + 1050)),
                        b_not(LX - 400, LY + 1120, self_get("PendingReach", "bool", LX - 600, LY + 1120)),
                        b_not(LX - 400, LY + 1190, self_get("KeyHeld", "bool", LX - 600, LY + 1190))),
                  b_and(LX - 300, LY + 1260, d_op("Greater_DoubleDouble", LX - 400, LY + 1260, _since_off, b_const="0.3", ret=RB),
                        self_get("Reaching", "bool", LX - 600, LY + 1260),
                        b_not(LX - 400, LY + 1330, grab_active(LX - 600, LY + 1330))),
                  d_op("Greater_DoubleDouble", LX - 300, LY + 1400, _since_off, b_const="4.0", ret=RB)))
_bon = branch(LX, LY + 700, "left hand off, and our grab over (or F let go with nothing taken, or 4 s)? the hand back on", _onc)
g.link(sqhx["then_3"], _bon["execute"])
TX, TY = X7 + 4000, Y7 + 6600
# build 21 (tester on build 20: "the hand comes out and reaches toward the item! but: it holds a copy of the item, the
# item flickers and flies off to the left, the use is still out of sync"; probe: the hand reached the view centre;
# no other animated mesh found by GetComponentsByClass). The game's item for the use is already in Skif's hand on the
# use animation's first frame (its own hand-item meshes: Obj.GetSecondaryHandItemMeshComponent /
# GetWeaponInHandsMeshComponent, each with its own anim instance playing the item's half of the use). So, while our
# reach plays over the paused use: those meshes are hidden and their animations paused; our copy stays where the item
# lay; at the grab frame the copy goes and the game's own item shows in the hand (its real grip), which then comes back
# with it; at the end everything goes on together.
g.box("EdGraphNode_Comment_932", TX - 600, TY - 300, 6400, 3600, "Build 21: the game's own item meshes in Skif's hands: hidden and paused while our hand reaches, shown at the grab, going on with the use")
HANDS = (("GetSecondaryHandItemMeshComponent", "TwinHidden", "TwinComp"), ("GetWeaponInHandsMeshComponent", "TwinHidden2", "TwinComp2"))


def _hand_mesh(x, y, fn):
    return member_pure(OBJC, fn, x, y, as_pc, [("ReturnValue", "object", dict(sub=SKC, out=True))])["ReturnValue"]


def _hand_ai(x, y, comp_pin):
    return member_pure(SKC, "GetAnimInstance", x, y, comp_pin, [("ReturnValue", "object", dict(sub=ANIMI, out=True))])["ReturnValue"]


#   P: every tick while our use reach plays
_bp19 = branch(TX - 300, TY, "our use reach on? the game's item meshes in the hands: paused, hidden until the grab", self_get("UseMode", "bool", TX - 500, TY + 150))
g.link(sqhx["then_4"], _bp19["execute"])
_fbs = set_from("FBActive", "bool", TX - 300, TY - 250, slot_active(TX - 500, TY - 150, anim, "FullBody"), "our FullBody slot active? (probe)")
g.link(_bp19["then"], _fbs["execute"])
_prev = _fbs["then"]
for k, (fn, hid, cvar) in enumerate(HANDS):
    x0, y0 = TX + 2600 * k, TY
    comp = _hand_mesh(x0 - 300, y0 + 300, fn)
    bv = branch(x0, y0, f"{fn.replace('Get', '').replace('Component', '')} there?", is_valid(x0 - 100, y0 + 200, comp))
    g.link(_prev, bv["execute"])
    ai = _hand_ai(x0 - 100, y0 + 450, comp)
    cur = member_pure(ANIMI, "GetCurrentActiveMontage", x0 + 100, y0 + 550, ai, [("ReturnValue", "object", dict(sub=MONT, out=True))])["ReturnValue"]
    pr_ = [set_from("CandComp" if k == 0 else "CandComp2", "object", x0 + 300, y0, comp, "probe", sub=SKC),
           set_from("CandMont" if k == 0 else "CandMont2", "object", x0 + 600, y0, cur, "", sub=MONT)]
    g.link(bv["then"], pr_[0]["execute"])
    chain(*pr_)
    ba = branch(x0 + 900, y0, "has an anim instance? pause it (the item's half of the use)", is_valid(x0 + 800, y0 + 200, ai))
    g.link(pr_[-1]["then"], ba["execute"])
    mp_ = member_call(ANIMI, "Montage_Pause", x0 + 1200, y0, ai, "held with the player's", [("Montage", "object", dict(sub=MONT))])
    g.link(ba["then"], mp_["execute"])
    chain(mp_, self_set("TwinsPaused", "bool", x0 + 1500, y0, "", default="true"))
    bh = branch(x0 + 1200, y0 + 400, "shown and before the grab? hide it (our hand reaches empty)",
                b_and(x0 + 1100, y0 + 600, member_pure(SC_, "IsVisible", x0 + 900, y0 + 650, comp, [RB])["ReturnValue"],
                      b_not(x0 + 900, y0 + 750, self_get("UseGrabbed", "bool", x0 + 700, y0 + 750))))
    g.link([n_ for n_ in g.nodes if n_.klass.endswith("K2Node_VariableSet") and n_.pins.get("TwinsPaused") is not None][-1]["then"], bh["execute"])
    g.link(ba["else"], bh["execute"])
    hv = member_call(SC_, "SetVisibility", x0 + 1500, y0 + 400, comp, "hidden", [B("bNewVisibility", "false"), B("bPropagateToChildren", "true")])
    g.link(bh["then"], hv["execute"])
    chain(hv, set_from(cvar, "object", x0 + 1800, y0 + 400, comp, "", sub=SKC), self_set(hid, "bool", x0 + 2100, y0 + 400, "", default="true"),
          inc("NTwinPause", x0 + 2400, y0 + 400, "count (probe)"))
    jn = sequence(x0 + 2300, y0 - 200, "next", 1)
    g.link(bv["else"], jn["execute"])
    g.link(bh["else"], jn["execute"])
    g.link([n_ for n_ in g.nodes if n_.comment == "count (probe)"][-1]["then"], jn["execute"])
    _prev = jn["then_0"]
#   G: at the grab frame: our copy goes, the game's item shows in the hand
_gt = d_op("GreaterEqual_DoubleDouble", TX - 400, TY + 1500, montage_time_since_reach(TX - 600, TY + 1500),
           self_get("GrabTime", "real", TX - 600, TY + 1600, subcat="double"), ret=RB)
_bg = branch(TX - 300, TY + 1300, "our use reach at its grab frame? the game's own item into the hand, our copy goes",
             b_and(TX - 400, TY + 1400, self_get("UseMode", "bool", TX - 600, TY + 1350), b_not(TX - 500, TY + 1450, self_get("UseGrabbed", "bool", TX - 700, TY + 1450)),
                   grab_active(TX - 600, TY + 1700), _gt, b_not(TX - 500, TY + 1800, self_get("PickUse", "bool", TX - 700, TY + 1800))))
g.link(_prev, _bg["execute"])
_sg = self_set("UseGrabbed", "bool", TX, TY + 1300, "", default="true")
g.link(_bg["then"], _sg["execute"])
_bfc = branch(TX + 300, TY + 1300, "our copy out?", is_valid(TX + 200, TY + 1500, self_get("Fly", "object", TX, TY + 1500, sub=ACTOR)))
g.link(_sg["then"], _bfc["execute"])
_dfc = member_call(ACTOR, "K2_DestroyActor", TX + 600, TY + 1300, self_get("Fly", "object", TX + 400, TY + 1500, sub=ACTOR), "gone (the hand has the game's own now)")
g.link(_bfc["then"], _dfc["execute"])


def _show_all(x, y, exec_in, comment):
    prev = exec_in
    for k, (fn, hid, cvar) in enumerate(HANDS):
        bs = branch(x + 700 * k, y, f"{cvar} hidden by us?", b_and(x + 700 * k - 100, y + 200, self_get(hid, "bool", x + 700 * k - 300, y + 200),
                                                                   is_valid(x + 700 * k - 100, y + 300, self_get(cvar, "object", x + 700 * k - 300, y + 300, sub=SKC))))
        g.link(prev, bs["execute"])
        sv = member_call(SC_, "SetVisibility", x + 700 * k + 300, y, self_get(cvar, "object", x + 700 * k + 100, y + 200, sub=SKC), comment,
                         [B("bNewVisibility", "true"), B("bPropagateToChildren", "true")])
        g.link(bs["then"], sv["execute"])
        cl = self_set(hid, "bool", x + 700 * k + 600, y - 200, "", default="false")
        g.link(sv["then"], cl["execute"])
        jn = sequence(x + 700 * k + 600, y + 100, "", 1)
        g.link(cl["then"], jn["execute"])
        g.link(bs["else"], jn["execute"])
        prev = jn["then_0"]
    return prev


_sa = _show_all(TX + 900, TY + 1300, _dfc["then"], "the game's item shows in the hand")
g.link(_bfc["else"], [n_ for n_ in g.nodes if n_.comment == "TwinComp hidden by us?"][-1]["execute"])
#   R: our reach over (UseMode off) and something paused / hidden: everything goes on, items shown
_br19 = branch(TX - 300, TY + 2400, "our use reach over and the item's side held? it goes on with the player's",
               b_and(TX - 400, TY + 2600, b_or(TX - 500, TY + 2600, self_get("TwinsPaused", "bool", TX - 700, TY + 2550),
                                               self_get("TwinHidden", "bool", TX - 700, TY + 2620), self_get("TwinHidden2", "bool", TX - 700, TY + 2690)),
                     b_not(TX - 500, TY + 2750, self_get("UseMode", "bool", TX - 700, TY + 2750))))
g.link(sqhx["then_5"], _br19["execute"])
_prev = _br19["then"]
for k, (fn, hid, cvar) in enumerate(HANDS):
    x0, y0 = TX + 1200 * k, TY + 2400
    comp = _hand_mesh(x0 - 300, y0 + 300, fn)
    ai = _hand_ai(x0 - 100, y0 + 400, comp)
    ba = branch(x0, y0, "its anim instance?", b_and(x0 - 100, y0 + 200, is_valid(x0 - 300, y0 + 500, comp), is_valid(x0 - 100, y0 + 550, ai)))
    g.link(_prev, ba["execute"])
    mr = member_call(ANIMI, "Montage_Resume", x0 + 300, y0, ai, "its half of the use goes on", [("Montage", "object", dict(sub=MONT))])
    g.link(ba["then"], mr["execute"])
    jn = sequence(x0 + 700, y0 + 100, "", 1)
    g.link(mr["then"], jn["execute"])
    g.link(ba["else"], jn["execute"])
    _prev = jn["then_0"]
_sa2 = _show_all(TX + 2600, TY + 2400, _prev, "shows again")
_clr19 = [self_set("TwinsPaused", "bool", TX + 4200, TY + 2400, "", default="false"), self_set("UseGrabbed", "bool", TX + 4500, TY + 2400, "", default="false"),
          inc("NTwinResume", TX + 4800, TY + 2400, "count (probe)")]
g.link(_sa2, _clr19[0]["execute"])
chain(*_clr19)
_rto = member_call(PC, "ReturnLeftHandOnItemEnded", LX + 300, LY + 700, as_pc, "left hand back on the item")
g.link(_bon["then"], _rto["execute"])
chain(_rto, self_set("LHOff", "bool", LX + 650, LY + 700, "", default="false"), inc("NLHOn", LX + 950, LY + 700, "count (probe)"))
_mrl = member_call(ANIMI, "Montage_Resume", X7 + 1250, Y7 + 5300, anim, "the use goes on", [("Montage", "object", dict(sub=MONT))])
g.link(self_get("UseMont", "object", X7 + 1050, Y7 + 5450, sub=MONT), _mrl["Montage"])
_bpk2 = branch(X7 + 1050, Y7 + 5100, "a pickup in the use pose? its held animation stops", self_get("PickUse", "bool", X7 + 850, Y7 + 5150))
g.link(_bul["then"], _bpk2["execute"])
g.link(_bpk2["else"], _mrl["execute"])
_mst2 = member_call(ANIMI, "Montage_Stop", X7 + 1350, Y7 + 5050, anim, "the use pose goes", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.250000",')), ("Montage", "object", dict(sub=MONT))])
g.link(self_get("UseMont", "object", X7 + 1150, Y7 + 5200, sub=MONT), _mst2["Montage"])
g.link(_bpk2["then"], _mst2["execute"])
_spk2 = self_set("PickUse", "bool", X7 + 1650, Y7 + 5050, "", default="false")
g.link(_mst2["then"], _spk2["execute"])
_umf2 = self_set("UseMode", "bool", X7 + 1550, Y7 + 5300, "", default="false")
g.link(_spk2["then"], _umf2["execute"])
chain(_mrl, _umf2, inc("NUseLate", X7 + 1850, Y7 + 5300, "count (probe)"))
g.link(sq7["then_2"], sqhx["execute"])
#   our copy: gone when the game's use animation starts (its own item is in its hands)
bcu = branch(X7 + 900, Y7 + 4700, "the game's use started after we caught the hold, our copy still out? remove it",
             b_and(X7 + 850, Y7 + 4900, is_valid(X7 + 650, Y7 + 4900, self_get("Fly", "object", X7 + 450, Y7 + 4900, sub=ACTOR)),
                   d_op("Greater_DoubleDouble", X7 + 650, Y7 + 4970, self_get("GameMontageAt", "real", X7 + 450, Y7 + 4970, subcat="double"),
                        self_get("PreReachAt", "real", X7 + 450, Y7 + 5040, subcat="double"), ret=RB),
                   d_op("Less_DoubleDouble", X7 + 650, Y7 + 5110,
                        d_op("Subtract_DoubleDouble", X7 + 450, Y7 + 5110, now(X7 + 250, Y7 + 5110), self_get("GameMontageAt", "real", X7 + 250, Y7 + 5180, subcat="double")),
                        b_const="1.0", ret=RB)))
# g.link(sqhx["then_0"], bcu["execute"])   # build 17: our copy stays until our hand pockets it
g.link(bcu["then"], member_call(ACTOR, "K2_DestroyActor", X7 + 1250, Y7 + 4700, self_get("Fly", "object", X7 + 1050, Y7 + 4900, sub=ACTOR), "remove it")["execute"])

for _q in list(_c2then.links):
    if _q is not bli["execute"]:
        _c2then.links.remove(_q); _q.links.remove(_c2then)
        g.link(bli["then"], _q)
g.link(_c2then, bli["execute"])

# build 22: the stand-in copy
GX, GY = X1 + 2800, Y1 - 2600
g.box("EdGraphNode_Comment_933", GX - 400, GY - 300, 3600, 1300, "Build 22: hold to use: a stand-in copy where the item lay, the moment it goes (no flicker)")
_bgo = branch(GX - 200, GY, "an older stand-in still out? remove it", is_valid(GX - 300, GY + 200, self_get("Ghost", "object", GX - 500, GY + 200, sub=ACTOR)))
g.link(_suwa["then"], _bgo["execute"])
_dgo = member_call(ACTOR, "K2_DestroyActor", GX + 100, GY - 150, self_get("Ghost", "object", GX - 100, GY + 50, sub=ACTOR), "remove it")
g.link(_bgo["then"], _dgo["execute"])
_sga = set_from("GhostAt", "real", GX + 400, GY, now(GX + 250, GY + 200), "", subcat="double")
g.link(_dgo["then"], _sga["execute"])
g.link(_bgo["else"], _sga["execute"])
_gsm = branch(GX + 700, GY, "static mesh item?", is_valid(GX + 600, GY + 200, self_get("ItemMesh", "object", GX + 400, GY + 200, sub=SM)))
g.link(_sga["then"], _gsm["execute"])
g.link(_gsm["then"], spawn_copy(GX + 1000, GY, SMA, "StaticMeshComponent", "stand-in (static mesh)", "Ghost", "NGhost")["execute"])
_gsk = branch(GX + 1000, GY + 500, "skeletal mesh item?", is_valid(GX + 900, GY + 700, self_get("ItemSkel", "object", GX + 700, GY + 700, sub=SKMESH)))
g.link(_gsm["else"], _gsk["execute"])
g.link(_gsk["then"], spawn_copy(GX + 1300, GY + 500, SKA, "SkeletalMeshComponent", "stand-in (skeletal mesh)", "Ghost", "NGhost")["execute"])
#   removed: our real copy is out (spawned after it), or no use animation came (0.35 s, or 3 s once the game started one)
_gat = self_get("GhostAt", "real", X7 + 600, Y7 + 6200, subcat="double")
_gage = d_op("Subtract_DoubleDouble", X7 + 800, Y7 + 6250, now(X7 + 600, Y7 + 6300), self_get("GhostAt", "real", X7 + 600, Y7 + 6370, subcat="double"))
_gdone = b_or(X7 + 1100, Y7 + 6200,
              b_and(X7 + 950, Y7 + 6100, is_valid(X7 + 750, Y7 + 6050, self_get("Fly", "object", X7 + 550, Y7 + 6050, sub=ACTOR)),
                    d_op("GreaterEqual_DoubleDouble", X7 + 750, Y7 + 6120, self_get("FlyStart", "real", X7 + 550, Y7 + 6120, subcat="double"), _gat, ret=RB)),
              b_and(X7 + 950, Y7 + 6300, d_op("Greater_DoubleDouble", X7 + 1000, Y7 + 6300, _gage, b_const="0.35", ret=RB),
                    b_not(X7 + 950, Y7 + 6400, d_op("Greater_DoubleDouble", X7 + 750, Y7 + 6400,
                                                     self_get("GameMontageAt", "real", X7 + 550, Y7 + 6400, subcat="double"),
                                                     self_get("GhostAt", "real", X7 + 550, Y7 + 6470, subcat="double"), ret=RB))),
              d_op("Greater_DoubleDouble", X7 + 1000, Y7 + 6500, _gage, b_const="3.0", ret=RB))
_bgd = branch(X7 + 1300, Y7 + 6100, "stand-in out and done? (our copy took over, or no use came)",
              b_and(X7 + 1200, Y7 + 6300, is_valid(X7 + 1050, Y7 + 6600, self_get("Ghost", "object", X7 + 850, Y7 + 6600, sub=ACTOR)), _gdone))
g.link(sqhx["then_6"], _bgd["execute"])
g.link(_bgd["then"], member_call(ACTOR, "K2_DestroyActor", X7 + 1600, Y7 + 6100, self_get("Ghost", "object", X7 + 1400, Y7 + 6300, sub=ACTOR), "remove the stand-in")["execute"])

# (builds 36-37, the game's left-hand IK driven through WeaponData.WeaponMesh: removed. 36: with empty hands there is no
#  weapon mesh to move; 37: WeaponData's members are read-only to Blueprints ("Make Anim Player Weapon Data" has no pins))

# v1.3.0 release cleanup: the strafe experiments (builds 47-55) were switched off in v1.1.1 (never wired: their nodes
# compiled out); they are no longer emitted (STRAFE_EXPERIMENTS False drops their nodes and box, and AS_ImmLoot_Twist
# is gone). The design for the real fix: zonekit/research/strafe/README.md
STRAFE_EXPERIMENTS = False
_n_strafe0, _b_strafe0 = len(g.nodes), len(g.boxes)
TWX, TWY = X7 + 4000, Y7 + 13000
g.box("EdGraphNode_Comment_936", TWX - 600, TWY - 300, 4200, 1300, "Build 47: strafing turns the body; the pickup's segment is re-picked every tick by the shoulder's turn (the hand stays on the item)")
_twon = b_and(TWX - 300, TWY + 200, self_get("GrabBH", "bool", TWX - 500, TWY + 150), grab_active(TWX - 500, TWY + 250),
              b_not(TWX - 400, TWY + 350, self_get("UseMode", "bool", TWX - 600, TWY + 350)), b_not(TWX - 400, TWY + 420, self_get("LootReach", "bool", TWX - 600, TWY + 420)),
              b_not(TWX - 400, TWY + 490, self_get("DoorTouch", "bool", TWX - 600, TWY + 490)))
_btw = branch(TWX, TWY, "our empty-hands pickup playing? keep it aimed through the body's turn", _twon)
# g.link(sqhx["then_7"], _btw["execute"])   # v1.1.1: the strafe experiments (builds 47-55, no visible effect) are off until the strafe fix is built
_dyaw = kml("NormalizeAxis", TWX - 100, TWY + 600, [D("Angle"), RD])
g.link(d_op("Subtract_DoubleDouble", TWX - 250, TWY + 600, _sh_yaw(TWX - 400, TWY + 700), ar("AimShYaw0", TWX - 400, TWY + 800)), _dyaw["Angle"])
_az_now = d_op("Subtract_DoubleDouble", TWX + 50, TWY + 650, self_get("ItemAzim", "real", TWX - 100, TWY + 750, subcat="double"), _dyaw["ReturnValue"])
_seg_now = _pick_seg(TWX + 200, TWY + 600, self_get("ItemElev", "real", TWX + 50, TWY + 550, subcat="double"), _az_now)
_cvn = kml("Conv_IntToDouble", TWX + 550, TWY + 600, [("InInt", "int"), RD])
g.link(_seg_now, _cvn["InInt"])
_segst = d_op("Multiply_DoubleDouble", TWX + 700, TWY + 600, _cvn["ReturnValue"], b_const="1.5")
_stw = set_from("TwYaw", "real", TWX + 300, TWY, _dyaw["ReturnValue"], "the shoulder's turn since the grab started (probe)", subcat="double")
g.link(_btw["then"], _stw["execute"])
_dif = d_op("Subtract_DoubleDouble", TWX + 850, TWY + 450, _segst, self_get("SegStart", "real", TWX + 700, TWY + 500, subcat="double"))
_abs = kml("Abs", TWX + 950, TWY + 450, [D("A"), RD])
g.link(_dif, _abs["A"])
_bsw = branch(TWX + 600, TWY, "another segment now? jump to it (same time in the segment)", d_op("Greater_DoubleDouble", TWX + 1100, TWY + 450, _abs["ReturnValue"], b_const="0.01", ret=RB))
# g.link(_stw["then"], _bsw["execute"])   # build 49: off (build 48 probe: the shoulder turned only 0-3 deg while strafing)
_hrel_t = vop("Subtract_VectorVector", TWX + 400, TWY - 400, hand, cl_)
_vel = member_pure(ACTOR, "GetVelocity", TWX + 400, TWY - 600, as_pc, [("ReturnValue", "struct", dict(sub=VEC, out=True))])["ReturnValue"]
_crot = member_pure(PCM, "GetCameraRotation", TWX + 200, TWY - 800, lib_pure(GS, "GameplayStatics", "GetPlayerCameraManager", TWX, TWY - 800,
            [("WorldContextObject", "object", dict(sub=OBJ, hidden=True)), ("PlayerIndex", "int", dict(extra='DefaultValue="0",')), ("ReturnValue", "object", dict(sub=PCM, out=True))])["ReturnValue"],
            [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_crb = kml("BreakRotator", TWX + 400, TWY - 800, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                 ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(_crot, _crb["InRot"])
_arot = member_pure(ACTOR, "K2_GetActorRotation", TWX + 200, TWY - 1000, as_pc, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_arb = kml("BreakRotator", TWX + 400, TWY - 1000, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                  ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(_arot, _arb["InRot"])
_mrel = member_pure(SC_, "K2_GetComponentRotation", TWX + 200, TWY - 1200, mesh, [("ReturnValue", "struct", dict(sub=ROT, out=True))])["ReturnValue"]
_mrb = kml("BreakRotator", TWX + 400, TWY - 1200, [("InRot", "struct", dict(sub=ROT)), ("Roll", "real", dict(subcat="float", out=True)),
                                                  ("Pitch", "real", dict(subcat="float", out=True)), ("Yaw", "real", dict(subcat="float", out=True))])
g.link(_mrel, _mrb["InRot"])
_logs = [("HandF", vop("Dot_VectorVector", TWX + 600, TWY - 400, _hrel_t, cf_, ret_sub="real")),
         ("HandR", vop("Dot_VectorVector", TWX + 600, TWY - 330, _hrel_t, cr_, ret_sub="real")),
         ("HandU", vop("Dot_VectorVector", TWX + 600, TWY - 260, _hrel_t, cu_, ret_sub="real")),
         ("VelR", vop("Dot_VectorVector", TWX + 600, TWY - 600, _vel, cr_, ret_sub="real")),
         ("CamRoll", _crb["Roll"]), ("CamYawRel", d_op("Subtract_DoubleDouble", TWX + 600, TWY - 900, _crb["Yaw"], _arb["Yaw"])),
         ("MeshYawRel", d_op("Subtract_DoubleDouble", TWX + 600, TWY - 1100, _mrb["Yaw"], _arb["Yaw"]))]
_lg = [set_from(v, "real", TWX + 700 + 300 * k, TWY - 200, pin, "per tick while grabbing (probe)" if k == 0 else "", subcat="double") for k, (v, pin) in enumerate(_logs)]
g.link(_stw["then"], _lg[0]["execute"])
chain(*_lg)
# build 49b (tester: "the camera doesn't tilt; it's the body that rotates and the arm rotates with the body"): the shoulder
# measure was in the body's own space, so the body's turn never showed. Now, as ImmersiveCampfires pins the seated body: the
# body mesh keeps the rotation it had (relative to the player) when the grab started, every tick while the grab plays
_bpin = branch(TWX + 2900, TWY - 200, "first tick of this grab? remember the body's rotation", b_not(TWX + 2800, TWY, self_get("BodyPinned", "bool", TWX + 2600, TWY)))
g.link(_lg[-1]["then"], _bpin["execute"])
_brt = kml("BreakTransform", TWX + 3000, TWY - 300, [("InTransform", "struct", dict(sub=XFORM)), ("Location", "struct", dict(sub=VEC, out=True)),
                                                    ("Rotation", "struct", dict(sub=ROT, out=True)), ("Scale", "struct", dict(sub=VEC, out=True))])
g.link(member_pure(SC_, "GetRelativeTransform", TWX + 2850, TWY - 300, mesh, [("ReturnValue", "struct", dict(sub=XFORM, out=True))])["ReturnValue"], _brt["InTransform"])
_srr = set_from("BodyRel0", "struct", TWX + 3200, TWY - 400, _brt["Rotation"], "the body's rotation relative to the player", sub=ROT)
g.link(_bpin["then"], _srr["execute"])
_spn = self_set("BodyPinned", "bool", TWX + 3500, TWY - 400, "", default="true")
g.link(_srr["then"], _spn["execute"])
# build 50 (build 49 probe while strafing: the body mesh and the camera never turn (0 deg), but the shoulder turned 60-86 deg
# INSIDE the walk / strafe animation, the arm with it). The hips' turn since the grab started is measured every tick and the
# upper body (jnt_spine_01 up) turned back by as much: AS_ImmLoot_Twist in DeathSlot, its frame = the turn
_hip_yaw = lambda x, y: _sh_yaw_b(x, y, "jnt_spine_03", axis="0.119700,-0.992800,0.000000")
_shy0 = set_from("HipYaw0", "real", TWX + 3800, TWY - 600, _hip_yaw(TWX + 3600, TWY - 800), "the hips' yaw at the grab start", subcat="double")
_mtw = member_call(ANIMI, "PlaySlotAnimationAsDynamicMontage", TWX + 4100, TWY - 600, anim, "the upper-body counter-turn (DeathSlot, after FullBody)", [
    ("Asset", "object", dict(sub=ANIMSEQB, extra='DefaultObject="/ImmersiveLooting/Runtime/AS_ImmLoot_Twist.AS_ImmLoot_Twist",')),
    ("SlotNodeName", "name", dict(extra='DefaultValue="DefaultSlot",')),   # build 55: the counter-turn again (the game files: strafing = a mesh-space turn of the whole body)
    ("BlendInTime", "real", dict(subcat="float", extra='DefaultValue="0.150000",')),
    ("BlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.200000",')),
    ("InPlayRate", "real", dict(subcat="float", extra='DefaultValue="0.000100",')),
    ("LoopCount", "int", dict(extra='DefaultValue="1",')),
    ("BlendOutTriggerTime", "real", dict(subcat="float", extra='DefaultValue="-1.000000",')),
    ("InTimeToStartMontageAt", "real", dict(subcat="float", extra='DefaultValue="3.000000",')),
    ("ReturnValue", "object", dict(sub=MONT, out=True))])
_stm = set_from("TwistMont", "object", TWX + 4400, TWY - 600, _mtw["ReturnValue"], "", sub=MONT)
_sok = set_from("TwistOk", "bool", TWX + 4700, TWY - 600, is_valid(TWX + 4600, TWY - 450, _mtw["ReturnValue"]), "the counter-turn started? (probe)")
_spn_then = _spn["then"]
for _q in list(_spn_then.links):
    _spn_then.links.remove(_q); _q.links.remove(_spn_then)
_bhst = branch(TWX + 4000, TWY - 900, "standing? hold the left arm at rest under the pickup", self_get("AimStand", "bool", TWX + 3800, TWY - 800))
chain(_spn, _shy0, self_set("TwistApplied", "real", TWX + 3950, TWY - 750, "", default="0.0", subcat="double"))
g.link([n_ for n_ in g.nodes if n_.klass.endswith("K2Node_VariableSet") and n_.pins.get("TwistApplied") is not None][0]["then"], _bhst["execute"])
g.link(_bhst["then"], _mtw["execute"])
chain(_mtw, _stm, _sok)
_srl = member_call(SC_, "K2_SetRelativeRotation", TWX + 3800, TWY - 200, mesh, "held there (the strafe does not turn it)", [
    ("NewRotation", "struct", dict(sub=ROT)), B("bSweep"), ("SweepHitResult", "struct", dict(sub=HIT, out=True)), B("bTeleport", "true")])
g.link(self_get("BodyRel0", "struct", TWX + 3600, TWY, sub=ROT), _srl["NewRotation"])
g.link(_sok["then"], _srl["execute"])   # build 50: after the counter-turn started
g.link(_bhst["else"], _mtw["execute"])   # build 55: crouched too
g.link(_bpin["else"], _srl["execute"])
_hd = kml("NormalizeAxis", TWX + 4000, TWY + 300, [D("Angle"), RD])
_shrest = kml("SelectFloat", TWX + 3700, TWY + 550, [D("A", "82.0"), D("B", "86.0"), ("bPickA", "bool", dict(extra='DefaultValue="false",')), RD])
g.link(self_get("AimStand", "bool", TWX + 3500, TWY + 600), _shrest["bPickA"])
# build 55: the shoulder's turn from its RESTING angle (standing ~82 deg in game, 84.9 in fp_bh_idle_stand; crouched 86.8),
# not from the grab's start: a grab started mid-strafe is corrected too
g.link(d_op("Subtract_DoubleDouble", TWX + 3850, TWY + 300, _sh_yaw(TWX + 3700, TWY + 400), _shrest["ReturnValue"]), _hd["Angle"])
_twpos = kml("FClamp", TWX + 4300, TWY + 300, [D("Value"), D("Min", "0.0"), D("Max", "6.0"), RD])
_phi = kml("FClamp", TWX + 4100, TWY + 450, [D("Value"), D("Min", "-90.0"), D("Max", "90.0"), RD])
g.link(d_op("Subtract_DoubleDouble", TWX + 3950, TWY + 450, self_get("TwistApplied", "real", TWX + 3800, TWY + 500, subcat="double"), _hd["ReturnValue"]), _phi["Value"])
g.link(d_op("Divide_DoubleDouble", TWX + 4250, TWY + 300, d_op("Add_DoubleDouble", TWX + 4150, TWY + 350, _phi["ReturnValue"], b_const="90.0"), b_const="30.0"), _twpos["Value"])
_mtsp = member_call(ANIMI, "Montage_SetPosition", TWX + 4500, TWY - 200, anim, "the upper body turned back by the hips' turn", [
    ("Montage", "object", dict(sub=MONT)), ("NewPosition", "real", dict(subcat="float"))])
g.link(self_get("TwistMont", "object", TWX + 4300, TWY - 100, sub=MONT), _mtsp["Montage"])
g.link(_twpos["ReturnValue"], _mtsp["NewPosition"])
_btv = branch(TWX + 4300, TWY - 400, "the counter-turn playing? (with no montage SetPosition would move every montage)",
              is_valid(TWX + 4200, TWY - 250, self_get("TwistMont", "object", TWX + 4000, TWY - 250, sub=MONT)))
g.link(_srl["then"], _btv["execute"])
g.link(_btv["then"], _mtsp["execute"])
chain(_mtsp, set_from("HipTurn", "real", TWX + 4800, TWY - 200, _hd["ReturnValue"], "the upper body's measured turn since the start (probe)", subcat="double"),
      set_from("TwistApplied", "real", TWX + 5100, TWY - 200, _phi["ReturnValue"], "the counter-turn now applied", subcat="double"))
#   grab over: forget it (the game turns the body as before)
_bunp = branch(TWX + 300, TWY + 1100, "pinned and the grab over? let the body go", self_get("BodyPinned", "bool", TWX + 100, TWY + 1200))
g.link(_btw["else"], _bunp["execute"])
_bpf = self_set("BodyPinned", "bool", TWX + 600, TWY + 1100, "", default="false")
g.link(_bunp["then"], _bpf["execute"])
_mtst = member_call(ANIMI, "Montage_Stop", TWX + 900, TWY + 1100, anim, "the counter-turn goes", [
    ("InBlendOutTime", "real", dict(subcat="float", extra='DefaultValue="0.200000",')), ("Montage", "object", dict(sub=MONT))])
g.link(self_get("TwistMont", "object", TWX + 700, TWY + 1250, sub=MONT), _mtst["Montage"])
g.link(_bpf["then"], _mtst["execute"])
_gpos = member_pure(ANIMI, "Montage_GetPosition", TWX + 900, TWY + 300, anim, [("Montage", "object", dict(sub=MONT)), ("ReturnValue", "real", dict(subcat="float", out=True))])
_gpos.pins["Montage"].const = True
g.link(self_get("GrabMontage", "object", TWX + 700, TWY + 300, sub=MONT), _gpos["Montage"])
_newp = d_op("Add_DoubleDouble", TWX + 1150, TWY + 250, _segst, d_op("Subtract_DoubleDouble", TWX + 1050, TWY + 300, _gpos["ReturnValue"], self_get("SegStart", "real", TWX + 900, TWY + 380, subcat="double")))
_msp = member_call(ANIMI, "Montage_SetPosition", TWX + 1300, TWY, anim, "the same moment of the reach, another direction", [
    ("Montage", "object", dict(sub=MONT)), ("NewPosition", "real", dict(subcat="float"))])
g.link(self_get("GrabMontage", "object", TWX + 1100, TWY + 150, sub=MONT), _msp["Montage"])
g.link(_newp, _msp["NewPosition"])
g.link(_bsw["then"], _msp["execute"])
chain(_msp, set_from("SegStart", "real", TWX + 1600, TWY, _segst, "", subcat="double"), inc("NTwSwitch", TWX + 1900, TWY, "count (probe)"))
if not STRAFE_EXPERIMENTS:
    for n_ in g.nodes[_n_strafe0:]:
        for p_ in n_.pins.values():
            for q_ in list(p_.links):
                q_.links.remove(p_)
            p_.links.clear()
    del g.nodes[_n_strafe0:]
    del g.boxes[_b_strafe0:]

# build 35: the aim steps run first in the reach (brs.else -> Aim* -> reach steps)
_brs_else = brs["else"]
for _q in list(_brs_else.links):
    _brs_else.links.remove(_q); _q.links.remove(_brs_else)
    g.link(AIM_LAST["then"], _q)
g.link(_brs_else, AIM_FIRST["execute"])

write(sys.argv[1], g.text())
print("ok", len(g.nodes), "nodes")
