"""Creates every ImmersiveLooting asset except the two event graphs (those are pasted, gen_*.py). Headless, editor
closed, after the tester picked the mod once in the toolbar selector (GameFeatureData):

    powershell -File harness\\tools\\run_headless.ps1 -Script zonekit\\tools\\setup_assets.py

1. (v1.0.0: the montage copy AM_ImmLoot_Grab of builds 1-3 is no longer made; the sequences from make_grab_seq.py
   play as dynamic montages.) The input action IA_ImmLootInteract and context IMC_ImmLoot (make_input).
2. /ImmersiveLooting/Runtime/BP_ImmLootActor (Actor) and BP_ImmLootSubsystem (ModWorldSubsystem) with their member
   variables and defaults. Re-running keeps existing assets and only adds what is missing.
Log: <SCRATCH>/setup_assets.log and "[harness]" lines in the commandlet output.
"""
import os
import traceback
import unreal

RT = f"{MOD_ROOT}/Runtime"
SRC_GRAB = "/Game/_STALKER2/Animations/Player/AnimSequences/ar/ak74/MG_fp_ak74_weapon_grab"
GRAB = f"{RT}/AM_ImmLoot_Grab"
ACTOR = f"{RT}/BP_ImmLootActor"
SUBSYS = f"{RT}/BP_ImmLootSubsystem"
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
LOG = os.path.join(SCRATCH, "setup_assets.log")
lines = []


def log(s):
    lines.append(str(s)); unreal.log("[harness] " + str(s))


def mount_mod():
    if not EAL.does_asset_exist(f"{MOD_ROOT}/{MOD}"):
        try:
            unreal.GameFeaturesSubsystem.load_and_activate_game_feature_plugin(
                "file:" + os.path.abspath(UPLUGIN).replace("\\", "/"), unreal.GameFeaturePluginLoadComplete())
        except Exception as e:
            log(f"load_and_activate failed: {e}")
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([MOD_ROOT], True)
    return EAL.does_asset_exist(f"{MOD_ROOT}/{MOD}")


def notify_names(seq):
    return [(e.notify.get_class().get_name() if e.notify else str(e.notify_name)) for e in
            unreal.AnimationLibrary.get_animation_notify_events(seq)]


def make_grab():
    if not EAL.does_asset_exist(GRAB):
        dup = EAL.duplicate_asset(SRC_GRAB, GRAB)
        if dup is None:
            dup = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(GRAB.rsplit("/", 1)[1], RT, unreal.load_asset(SRC_GRAB))
        log(f"duplicated grab: {dup}")
    m = unreal.load_asset(GRAB)
    log(f"grab notifies before: {notify_names(m)}")
    for name in ("AttachItem", "AnimNotify_AttachItem"):
        unreal.AnimationLibrary.remove_animation_notify_events_by_name(m, name)
    after = notify_names(m)
    log(f"grab notifies after: {after}")
    if any("AttachItem" in n for n in after):
        raise RuntimeError("AttachItem notifies still present")
    log(f"grab saved: {EAL.save_asset(GRAB, only_if_is_dirty=False)}")


def make_bp(path, parent):
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    f = unreal.BlueprintFactory()
    f.set_editor_property("parent_class", parent)
    folder, name = path.rsplit("/", 1)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, f)
    log(f"created {path}: {bp}")
    return bp


def T(kind):
    if kind in ("bool", "int", "real"):
        return BEL.get_basic_type_by_name(kind)
    if kind == "transform":
        return BEL.get_struct_type(unreal.Transform.static_struct())
    if kind == "vector":
        return BEL.get_struct_type(unreal.Vector.static_struct())
    return BEL.get_object_reference_type(kind)


def add_vars(bp, path, vars_):
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    for name, kind, default in vars_:
        try:
            cdo.get_editor_property(name)
            continue
        except Exception:
            pass
        log(f"{path}: add {name} ({kind if isinstance(kind, str) else kind.get_name()}) -> {BEL.add_member_variable(bp, name, T(kind))}")
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    for name, kind, default in vars_:
        if default is not None:
            cdo.set_editor_property(name, default)
        log(f"{path}: {name} = {cdo.get_editor_property(name)!r}")
    log(f"{path} saved: {EAL.save_asset(path, only_if_is_dirty=False)}")


W_TEXT = unreal.load_class(None, "/Game/GameLite/FPS_Game/UIRemaster/CommonWidgets/W_Text.W_Text_C")
ACTOR_VARS = [
    ("Init", "bool", None), ("Enabled", "bool", True), ("TouchBodies", "bool", True), ("TouchDoors", "bool", True), ("KeyHeld", "bool", None), ("DoorYaw", "real", None), ("BoundAnim", unreal.AnimInstance.static_class(), None), ("GameMontage", unreal.AnimMontage.static_class(), None), ("GameMontageAt", "real", -100.0), ("HeldUse", unreal.AnimMontage.static_class(), None), ("UseHeld", "bool", None), ("NUseHolds", "int", None), ("ReplayAt", "real", -100.0), ("NReplays", "int", None), ("PreReach", "bool", None), ("PreReachAt", "real", -100.0), ("NPreReach", "int", None), ("NPreUse", "int", None), ("Captured", "bool", None), ("Handed", "bool", None), ("HandedAt", "real", -100.0), ("HideComp", unreal.SceneComponent.static_class(), None), ("NCapture", "int", None), ("NHandBack", "int", None), ("NAbort", "int", None), ("NHandUse", "int", None), ("NAbort2", "int", None), ("KeySeenAt", "real", -100.0), ("NDoorCut", "int", None), ("ReenableAt", "real", -100.0), ("OurHeldAt", "real", -100.0), ("UseWait", "bool", None), ("UseWaitAt", "real", -100.0), ("UseMode", "bool", None), ("UseMont", unreal.AnimMontage.static_class(), None), ("UsePausedAt", "real", -100.0), ("NUsePause", "int", None), ("NUseResume", "int", None), ("NUseLate", "int", None), ("NUseNoTable", "int", None), ("LHOff", "bool", None), ("LHOffAt", "real", -100.0), ("NLHOff", "int", None), ("NLHOn", "int", None), ("TwinsPaused", "bool", None), ("TwinHidden", "bool", None), ("TwinComp", unreal.SkeletalMeshComponent.static_class(), None), ("TwinMont", unreal.AnimMontage.static_class(), None), ("NTwinPause", "int", None), ("NTwinResume", "int", None), ("FBActive", "bool", None), ("CandComp", unreal.SkeletalMeshComponent.static_class(), None), ("CandMont", unreal.AnimMontage.static_class(), None), ("CandAnim", unreal.AnimInstance.static_class(), None), ("NCand", "int", None), ("TwinHidden2", "bool", None), ("TwinComp2", unreal.SkeletalMeshComponent.static_class(), None), ("CandComp2", unreal.SkeletalMeshComponent.static_class(), None), ("CandMont2", unreal.AnimMontage.static_class(), None), ("UseGrabbed", "bool", None), ("Ghost", unreal.Actor.static_class(), None), ("GhostAt", "real", -100.0), ("NGhost", "int", None), ("FlyHeld", "bool", None), ("PickUse", "bool", None), ("GrabPitch", "real", None), ("AimCX", "real", None), ("AimCZ", "real", None), ("AimAX", "real", None), ("AimAY", "real", None), ("AimAZ", "real", None), ("IKMoved", "bool", None), ("IKRel", "transform", None), ("IKErr", "real", None), ("IKSock", "real", None), ("IKOk", "bool", None), ("IKProxy", unreal.SkeletalMeshActor.static_class(), None), ("IKOrigWM", unreal.SkeletalMeshComponent.static_class(), None), ("WMKept", "bool", None), ("AimStand", "bool", None), ("AimC", "vector", None), ("AimP", "vector", None), ("AimA", "vector", None), ("AimD", "vector", None), ("AimOC", "vector", None), ("AimB", "real", None), ("AimT", "real", None), ("AimTp", "vector", None), ("AimU", "vector", None), ("AimBW", "real", None), ("AimL", "real", None), ("AimXE", "vector", None), ("NPickUse", "int", None), ("FlyRel", "transform", None), ("UseTap", unreal.InteractionComponent.static_class(), None), ("NHoldInject", "int", None), ("InjRetries", "int", None), ("NInjRetry", "int", None), ("DoorPulling", "bool", None), ("InteractPressAt", "real", -100.0), ("DoorTouch", "bool", None), ("DoorSped", "bool", None), ("DoorRate", "real", 1.0), ("DoorHold", "real", 0.12), ("NDoor", "int", None), ("LookPoint", "vector", None), ("Player", unreal.PC.static_class(), None),
    ("Item", unreal.Actor.static_class(), None), ("ItemComp", unreal.SceneComponent.static_class(), None),
    ("ItemMesh", unreal.StaticMesh.static_class(), None), ("ItemSkel", unreal.SkeletalMesh.static_class(), None),
    ("ItemSeen", "real", -100.0), ("ItemArmed", "bool", None), ("ItemXf", "transform", None),
    ("ReachStart", "real", -100.0), ("Reaching", "bool", None),
    ("Fly", unreal.Actor.static_class(), None), ("FlyFrom", "vector", None), ("FlyStart", "real", None),
    ("FlyDur", "real", 0.5), ("FlyAttached", "bool", None),
    # settings (montage seconds; real seconds = montage seconds / PlayRate)
    ("PlayRate", "real", 1.15), ("GrabTime", "real", 0.40), ("PocketTime", "real", 0.87),
    ("IKOnTime", "real", 1.179), ("SeenWindow", "real", 0.3),
    ("GrabMontage", unreal.AnimMontage.static_class(), None), ("PendingReach", "bool", None), ("PendingCopy", "bool", None),
    # loot window (corpse / stash)
    ("InvIMC", unreal.InputMappingContext.static_class(), None), ("InvOpen", "bool", None), ("OpenAt", "real", None),
    ("InvGoneAt", "real", -1.0), ("LootTarget", unreal.InteractionComponent.static_class(), None),
    ("LootObj", unreal.Object.static_class(), None), ("LootKind", "int", None), ("Took", "bool", None),
    ("PWText", W_TEXT, None), ("LWText", W_TEXT, None), ("InvView", unreal.UserWidget.static_class(), None),
    ("StartPW", "real", None), ("StartLW", "real", None), ("StartMoney", "real", None),
    ("CurPW", "real", None), ("CurLW", "real", None), ("CurMoney", "real", None),
    # counters for the dev probe
    ("NPickups", "int", None), ("NReaches", "int", None), ("NSkips", "int", None), ("NRecover", "int", None),
    ("NFly", "int", None), ("SkipBits", "int", None), ("NLootOpen", "int", None), ("NLootTook", "int", None),
    ("NTicks", "int", None), ("GrabFwd", "real", None), ("GrabRight", "real", None), ("GrabUp", "real", None),
    ("FovS", "real", None), ("TanFOVv", "real", None), ("FovOn", "real", None), ("CamOff", "real", None), ("TraceX", "real", None), ("TraceY", "real", None), ("TraceZ", "real", None), ("GrabBH", "bool", None), ("SegStart", "real", None), ("ItemCenter", "vector", None), ("ItemElev", "real", None), ("ItemDist", "real", None), ("ItemAzim", "real", None), ("LootComp", unreal.PrimitiveComponent.static_class(), None), ("LootReach", "bool", None), ("LootPaused", "bool", None), ("LootReverse", "bool", None), ("TouchState", "int", None), ("TouchAdded", "bool", None), ("Lootable", "bool", None), ("KeysSynced", "bool", None), ("TouchPressAt", "real", None), ("TouchOpenAt", "real", None), ("NTouch", "int", None), ("GripAt", "real", None), ("GripPending", "bool", None), ("TrBusy", "bool", None), ("TrLH", "bool", None), ("TrPos", "real", None), ("TouchHX", "real", None), ("TouchHY", "real", None), ("TouchHZ", "real", None), ("PausedAt", "real", None), ("TouchHoldBeforeOpen", "real", 0.25), ("TouchAsset", unreal.AnimSequenceBase.static_class(), None), ("TouchBin", "int", None), ("TouchReleased", "bool", None), ("HoldToDrag", "real", 0.4), ("Dragging", "bool", None), ("TapComp", unreal.InteractionComponent.static_class(), None), ("TapOff", "bool", None), ("KeyDown", "bool", None), ("KeyUp", "bool", None), ("LookActor", unreal.Actor.static_class(), None), ("LookComp", unreal.PrimitiveComponent.static_class(), None), ("ResetFor", unreal.InteractionComponent.static_class(), None), ("WeapX", "real", None), ("WeapY", "real", None), ("WeapZ", "real", None), ("CamPitch", "real", None), ("SpX", "real", None), ("SpY", "real", None), ("SpZ", "real", None), ("ShX", "real", None), ("ShY", "real", None), ("ShZ", "real", None), ("ElX", "real", None), ("ElY", "real", None), ("ElZ", "real", None), 
]

def make_input():
    """v0.2: our interact action and context (corpse / stash touch). The Blueprint adds the player's own interact keys
    at runtime (QueryKeysMappedToAction); F and the gamepad face-left button are the defaults."""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    ia_path, imc_path = f"{MOD_ROOT}/Input/IA_ImmLootInteract", f"{MOD_ROOT}/Input/IMC_ImmLoot"
    if not EAL.does_asset_exist(ia_path):
        tools.create_asset("IA_ImmLootInteract", f"{MOD_ROOT}/Input", unreal.InputAction, unreal.InputAction_Factory())
    ia = unreal.load_asset(ia_path)
    ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    ia.set_editor_property("consume_input", True)   # 1.1: swallows F (hold to use) while our grab plays; corpses never get it
    log(f"IA: {ia} consume={ia.get_editor_property('consume_input')} saved={EAL.save_asset(ia_path, only_if_is_dirty=False)}")
    if not EAL.does_asset_exist(imc_path):
        tools.create_asset("IMC_ImmLoot", f"{MOD_ROOT}/Input", unreal.InputMappingContext, unreal.InputMappingContext_Factory())
    imc = unreal.load_asset(imc_path)
    imc.unmap_all_keys_from_action(ia)
    for key in ("F", "Gamepad_FaceButton_Left"):
        k = unreal.Key()
        k.import_text(key)
        imc.map_key(ia, k)
    log(f"IMC: {imc} mappings={len(imc.get_editor_property('mappings'))} saved={EAL.save_asset(imc_path, only_if_is_dirty=False)}")


try:
    log(f"mod mounted: {mount_mod()}")
    # make_input()  # 1.1 build 15: not needed (hold to use works through the item's tap interaction); deleted 1.0.1h (unused since 1.0.1d; bisect: their presence vs the body carry)
    # make_grab()  # AM_ImmLoot_Grab (builds 1-3) deleted for v1.0.0: the sequences play as dynamic montages
    actor = make_bp(ACTOR, unreal.Actor)
    add_vars(actor, ACTOR, ACTOR_VARS)
    cdo = unreal.get_default_object(BEL.generated_class(actor))
    cdo.set_editor_property("auto_receive_input", unreal.AutoReceiveInput.DISABLED)   # 1.1 build 15: no input of ours at all (keys polled)
    log(f"actor auto_receive_input = {cdo.get_editor_property('auto_receive_input')} saved={EAL.save_asset(ACTOR, only_if_is_dirty=False)}")
    sub = make_bp(SUBSYS, unreal.ModWorldSubsystem)
    add_vars(sub, SUBSYS, [("LootActor", BEL.generated_class(actor), None), ("SpawnAttempts", "int", None)])
    for p in (GRAB, ACTOR, SUBSYS):
        log(f"verify {p}: {EAL.does_asset_exist(p)}")
except Exception:
    log("EXCEPTION: " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(LOG, "w", encoding="utf-8").write("\n".join(lines))
