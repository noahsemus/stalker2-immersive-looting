"""Creates every ImmersiveLooting asset except the two event graphs (those are pasted, gen_*.py). Headless, editor
closed, after the tester picked the mod once in the toolbar selector (GameFeatureData):

    powershell -File harness\\tools\\run_headless.ps1 -Script zonekit\\tools\\setup_assets.py

1. /ImmersiveLooting/Runtime/AM_ImmLoot_Grab: duplicate of the unused vanilla MG_fp_ak74_weapon_grab (LeftHand slot,
   left-hand grab over a held rifle), without its two native AttachItem notifies (their effect outside a real
   PickUpItem is unknown); the two HandIK notifies (left hand off / back on the grip) stay.
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
    ("Init", "bool", None), ("Enabled", "bool", True),
    ("Item", unreal.Actor.static_class(), None), ("ItemComp", unreal.SceneComponent.static_class(), None),
    ("ItemMesh", unreal.StaticMesh.static_class(), None), ("ItemSkel", unreal.SkeletalMesh.static_class(), None),
    ("ItemSeen", "real", -100.0), ("ItemArmed", "bool", None), ("ItemXf", "transform", None),
    ("ReachStart", "real", -100.0), ("Reaching", "bool", None),
    ("Fly", unreal.Actor.static_class(), None), ("FlyFrom", "vector", None), ("FlyStart", "real", None),
    ("FlyDur", "real", 0.5), ("FlyAttached", "bool", None),
    # settings (montage seconds; real seconds = montage seconds / PlayRate)
    ("PlayRate", "real", 1.4), ("GrabTime", "real", 0.569), ("PocketTime", "real", 0.80),
    ("IKOnTime", "real", 1.179), ("SeenWindow", "real", 0.3),
    ("PendingReach", "bool", None), ("PendingCopy", "bool", None),
    # loot window (corpse / stash)
    ("InvIMC", unreal.InputMappingContext.static_class(), None), ("InvOpen", "bool", None), ("OpenAt", "real", None),
    ("InvGoneAt", "real", -1.0), ("LootTarget", unreal.InteractionComponent.static_class(), None),
    ("LootKind", "int", None), ("Took", "bool", None),
    ("PWText", W_TEXT, None), ("LWText", W_TEXT, None), ("InvView", unreal.UserWidget.static_class(), None),
    ("StartPW", "real", None), ("StartLW", "real", None), ("StartMoney", "real", None),
    ("CurPW", "real", None), ("CurLW", "real", None), ("CurMoney", "real", None),
    # counters for the dev probe
    ("NPickups", "int", None), ("NReaches", "int", None), ("NSkips", "int", None), ("NRecover", "int", None),
    ("NFly", "int", None), ("SkipBits", "int", None), ("NLootOpen", "int", None), ("NLootTook", "int", None),
]

try:
    log(f"mod mounted: {mount_mod()}")
    make_grab()
    actor = make_bp(ACTOR, unreal.Actor)
    add_vars(actor, ACTOR, ACTOR_VARS)
    sub = make_bp(SUBSYS, unreal.ModWorldSubsystem)
    add_vars(sub, SUBSYS, [("LootActor", BEL.generated_class(actor), None), ("SpawnAttempts", "int", None)])
    for p in (GRAB, ACTOR, SUBSYS):
        log(f"verify {p}: {EAL.does_asset_exist(p)}")
except Exception:
    log("EXCEPTION: " + traceback.format_exc())
os.makedirs(SCRATCH, exist_ok=True)
open(LOG, "w", encoding="utf-8").write("\n".join(lines))
