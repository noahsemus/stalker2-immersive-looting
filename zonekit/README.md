# ImmersiveLooting — engineering log

What each kit check and each in-game test showed, newest at the bottom. Record dead ends here so they are never
retried. Plan: [../PLAN.md](../PLAN.md); reproducible edits: [../BUILD.md](../BUILD.md). Facts that hold for any
mod go to `harness/docs/` instead (promote them).

## 2026-10-09 — repo created from the harness
- `new_mod.ps1` created the repo, the kit plugin and the GitHub repo. GameFeatureData pending (tester picks the mod
  in the toolbar selector).
- Kit research (dumps, cfgs, uncooked assets read with a headless editor script, Nexus search, installed paks):
  `research/2026-10-09-pickup-and-left-hand-research.md`. Chosen route: NewContent host detects the pickup from the
  cached interaction target, plays a copy of the unused vanilla left-hand grab montage in `LeftHand`, flies a mesh
  copy of the item to `jnt_l_weapon`. See `../PLAN.md`.

## 2026-10-09 — builds 1-11 (one session)
- b1: nothing happened: `PC.GetInteractionTarget` is None while looking at a loose item. b2: `GetInteractedActor`
  first; pickups detected, reach + copy work.
- b2-b4 "item flies up-left off screen": first explained as the arms' FOV squeeze (`MF_Foreground_FOVCorrection`,
  real and in `harness/docs/animation.md`), but the main cause (b4-b7 probe traces) is that the arm bones do NOT follow
  the view pitch: looking 27 deg down, the reaching hand sat 53 cm above the view axis. b5/b6 tried the jnt_camera bone
  frame and the mesh frame (both wrong: CamOff 0, the arms do not pitch).
- "The animation plays twice" (b6): the vanilla grab dips the hand to the lower left before reaching; b7 removed the dip.
- The tester tests UNARMED: the rifle-solved arm on the empty-handed spine put the hand ~40 cm above the eye (b7 trace;
  the in-game rest hand matched `fp_bh_idle_stand` to 1 cm). b8: empty-hands grab re-solved on that spine; its copied
  "hand IK back on" notify made the hand jump centre-left (removed).
- b9: pitch table (8 segments of 2 s, -75..+30 deg) + item waits, is pulled into the hand at the grab frame. Tester:
  parent it to the hand (b9 shrank it to keep its screen size: wrong, dropped).
- b10/b11: target lower left. b10 landed at ~(55, +4, -8) view frame whatever the target: left-hand IK to the grip
  point; b11 switches it off at each segment start (HandIK notify, default = off) and aims at (40, -28, -16). Tester:
  "this is good" -> checkpoint-b11.
- b12-b15 "the hand grabs the item where it is": table by item elevation and distance (b12), + body azimuth (b13);
  both landed ~15 cm right / up of the computed point. b14 traced the grip point (`jnt_weapon`): at the hip, so not the
  left-hand IK. The rest pose matches the model to ~3 cm; the reached pose is off by ~(+9 ahead, +15 right, +5 up) in
  the view frame (neither a local- nor a mesh-space rotation blend model reproduces it). b15 aims short by that bias:
  tester "looks good" -> checkpoint-b15 (release candidate). Items picked up were 100-130 cm away (arm ~52 cm): far
  items still slide the last part into the hand.
- v0.2 corpse / stash touch, rifle (2026-10-10): the reach table `AS_ImmLoot_GrabAR` (segment 58, elev -35, out of
  reach) played in `LeftHand` (slot active, position 0 -> 0.62) but the hand (`jnt_l_weapon`, view axes) went from the
  grip (41, 2, -17, swaying) to a fixed (41.5, 2.7, -13.5) and stayed there through the window and after: left-hand
  IK off, slot pose not shown. The same frames in the AR table (AR_FROM_RIFLE) also did nothing; `AS_ImmLoot_Grab`
  from 0 moves the hand to (20, -20, -9) in the same session. Tester: "reaches a little, window, hand stuck". Kit:
  `AnimBP_PlayerWeaponLayer` puts the `LeftHand` slot under `left_hand_blend_mask` then `TwoBoneIK_GSC` (alpha
  `HandsIKData.LeftHand.Alpha`) unless `StateData.bIsLeftHandBusy` (then the left arm comes from the "Additional" input:
  drag-body / detector / idle machine). Next build: armed touch = `AS_ImmLoot_Grab` held at 0.6 s, played on forward
  after the window (its own IK-on notify re-grips, as after a loose item).
- 2026-10-10 b (rifle grab as the touch): tester "small progress: the hand doesn't reach out fully, but when the window
  closes it returns to the weapon like vanilla". Probe: montage 0 -> 0.64, paused, window, played on after the close,
  `Reaching` cleared. So the short-asset form shows over a rifle; the raised rifle grab just moves the hand ~10 cm (it
  grabs at the crosshair). Kit, `AnimBP_PlayerWeaponLayer` → `WeaponUnderbarrelIdleLayer`: on rifles with an underbarrel
  idle type the left arm is replaced by the GripIdle pose weighted by `LeftHandCurveValueInverse` (= 1 - montage curve
  `left_hand_curve`), which is why the game's left-hand gestures carry that curve. Next build: `AS_ImmLoot_Touch`
  (make_grab_seq `build_touch`): copy of the grab, hand from the grip to 97 % of the arm's reach at elevation -45 /
  azimuth -10 (body frame) by frame 12 (29 cm below the grip, 13 cm left), held to 20, straight back to the grip by
  36, IK on at 1.2 s, `left_hand_curve` 0 / 1 (0.17 s) / 1 (1.1 s) / 0 (1.3 s).
- 2026-10-10 c (`AS_ImmLoot_Touch`, one asset aimed 45 deg down in the body frame): tester "better, but the arm goes
  down to the player's side rather than out toward the body". Probe: hand held at (52, -8, -51) in view axes = 51 cm
  below the view axis: the view was level, the arm does not follow the view pitch. Next build: six assets
  `AS_ImmLoot_Touch0..5` for sight-line pitch -60..+15 (body frame, 15 deg bins); the hand ends ON the sight line as
  far as the arm reaches (95 %), 10 deg left of it. The press computes the camera forward in the mesh frame
  (`InverseTransformDirection`), bins it, stores the asset in `TouchAsset` (new variable); step 3 plays that.
  `CamPitch` now also logged during a touch.
- 2026-10-10 d (six pitch-binned touch assets): tester "no change". Probe: sight line -48.6 deg in the mesh frame
  (bin 1, planned hand (42.3,-7.5,-42.9) rel camera bone), hand held at (50.7,-5.2,-48.0) in VIEW axes: the same
  offset from the plan as build c (+8.5 ahead, +2.5 right, -5 up) although the view pitch differed by ~45 deg. So with
  a weapon in hand the arm rig FOLLOWS the view (the weapon layer pitches jnt_spine_03 with the look-vertical
  additive): a hand position relative to the camera bone in the sequence is its position in view axes in game. Empty
  hands differ (bh layer: body frame, hence the BH table's pitch bins). Also explains why the rifle grab lands at the
  crosshair at any pitch. Next build: one `AS_ImmLoot_Touch`, hand on the camera axis minus the bias (+7 deg,
  -15 deg az in the camera-bone frame -> (43.4,-11.6,5.5), expected in view (52,-9,0)); the pitch cascade removed.
- 2026-10-10 e (tester: "not toward the centre of the screen: toward the body being looted, like loose items"): 25
  short assets `AS_ImmLoot_Touch0..24`, the hand on the ray from the camera to the body's / stash's centre (bounds
  origin) in VIEW axes, elevation -45..+15 x azimuth -30..+30 (15 deg bins, index ie * 5 + ia), 95 % of the arm,
  landing bias (+8.5, +2.5, -5) solved in. Short assets cook to ~15 KB each (the 305 KB is editor data). The press
  computes the centre's direction in view axes, stores `TouchBin` (new int variable) and `TouchAsset`; a 25-branch
  cascade (comparing the variable, so untangle() does not clone the whole tree 25 times: 2769 -> 1739 nodes).
- 2026-10-10 e (25 assets, bounds centre): tester "the hand goes up to the top centre edge". Probe: human corpse
  (BP_AI_Human_C, CharacterMesh0), centre computed 21 deg ABOVE the view: a dead body's mesh component keeps its
  bounds at the standing position (the bones lie on the ground, the component does not move). Landing fit over three
  builds: view = (plan ahead + 8.4, 1.14 x right + 4.0, 1.15 x up + 2.0) (the sideways scale ~ the arms' FOV squeeze),
  the earlier constant bias was wrong for high targets. Next build: a body's target = its `jnt_hips` bone
  (`DoesSocketExist`, else the bounds centre: stashes, mutants); assets rebuilt with the affine map solved in; the
  probe now prints CamPitch, TouchBin, LootComp.
- 2026-10-10 f (pelvis target, affine map): tester "body works now, but loose items is broken: the hand doesn't go
  fully out" (rifle). Probe, item pickups: the grab montage played (LeftHand active, position 0.2 -> 0.76) but the hand
  stayed at the grip (41.5, 2.7, -13.5) the whole time, the same signature as the AR table; the touch assets, which
  carry `left_hand_curve`, moved it in the same session with the same rifle. The grab asset itself is unchanged since
  the checkpoint (same hand path). So the rifle in use has an underbarrel idle type: `WeaponUnderbarrelIdleLayer`
  replaces the left arm by the GripIdle pose weighted by 1 - `left_hand_curve`, hiding any LeftHand montage without
  the curve (the earlier "fine with a rifle" was another rifle). Fix: `left_hand_curve` on `AS_ImmLoot_Grab` (1 from
  0.17 s to 1.15 s, 0 at 1.4 s), no Blueprint change. The same explains the AR table (its curve version was never
  tested).
- 2026-10-10 v1.0.0 report (Nexus, discotizer: "grabbing dead bodies don't work anymore"; Noah: "the prompt to hold F
  to pick up the body doesn't even appear"): our `IMC_ImmLoot` consumes the interact key while a corpse is in sight
  and the press is passed on as a one-frame injected `IA_Interact` = always a tap; the game's hold interaction (carry
  the body, native `HoldTime` / `HoldPreventFromDefaultInteractionPercent`) never sees the key held. Fix (build
  1.0.1a): the window opens only after the key was RELEASED while reaching (`TouchReleased`, set on our action's
  Completed); still held `HoldToDrag` (0.4 s) after the press = the game's hold: TouchState 0, our context removed
  (the physically held key now reaches `IA_Interact`), one injected press, hand back through T2's chain.
- 1.0.1a (context off + one injected press at 0.4 s): Noah: hold F = hand out and back, THEN the loot window; the
  carry never starts; the hold prompt stays a dot. Kit: `IA_Interact` has no action-level triggers; `IMC_Interactivity`
  maps F / gamepad face-left with `InputTriggerDown` (actuation 0.5): the native code (`HoldIPU`, `HoldComponent`)
  gets Triggered every tick while held and times the hold itself; a one-frame injected press is a tap (the default
  interaction = the window). 1.0.1b: in drag mode keep our context, `Dragging` (new bool) = true, and on every
  Triggered tick of our action inject `IA_Interact` (= Down each tick): the game sees a continuous hold from 0.4 s;
  any release clears `Dragging`. Still open: the "hold F" prompt (dot) while our context is on.
- 1.0.1b (inject IA_Interact every tick in drag mode): Noah: hold F = hand out and back, no window, no carry, prompt
  still a dot. Injection does not drive the native hold. Noah: the vanilla "hold F" prompt MUST show and the carry
  must be pure vanilla (no touch). Kit: a body has `DeadBody` (SingleClickComponent: the search / tap) and
  `DeadBodyHoldComponent` (HoldComponent: the carry); a stash `ItemContainerInteractionComponent` +
  `ItemContainerHoldComponent`; both derive from `InteractionComponent`, which has `SetInteractionActive(bActive)`
  (pin name from BP_Bed's own call). The game's interact widgets (`W_InteractView`, `W_InteractViewDots`, the hint
  controller) have empty graphs: native. 1.0.1c: `IA_ImmLootInteract` no longer consumes the key (the game's
  `IA_Interact` and its hold work natively, prompt included); at our press the target's TAP interaction component
  (`TapComp`, remembered each idle tick) is switched off so the game's own tap does nothing; released within
  `HoldToDrag` (0.4 s) = a tap: the touch plays, then the component is switched back on and `IA_Interact` injected
  (window); held longer = the game's hold (carry), nothing of ours; every exit back to idle switches the component on
  again (`TapOff`). TouchState 1 = pressed, tap or hold unknown.
- 1.0.1c (no consume, tap component off at the press): Noah: still no "hold F" prompt, hold does nothing. So the
  consumption was not it: any mapping of the key (or input on our actor) hides the game's hold. 1.0.1d: NO input
  mapping context and NO input on the actor (`auto_receive_input` DISABLED): the player's interact keys
  (`QueryKeysMappedToAction`) are polled every tick with `PlayerController.WasInputKeyJustPressed / Released`
  (`KeyDown` / `KeyUp` set in a ForEach over the keys); the press / release handlers are unchanged. `IMC_ImmLoot` /
  `IA_ImmLootInteract` are no longer referenced (delete before the release). The context add / remove steps are gone.
- 1.0.1d (keys polled, no input context, no input on the actor): Noah: "no change". The probe shows the new logic
  ran (TouchState 1 on the press, 3 for the window), the game was started after the cook, only the test pak was
  deployed: the build loads, so input is NOT the cause. Noah refuses runs without the mod ("we know it works in
  vanilla"). Every call the actor makes is pure except our montage / copy / SetInteractionActive ones (none near
  a body before a press); the only calls into the game's interaction system left were `PC.GetInteractedActor`,
  `GetInteractionTarget`, `GetInteractedComponent` every tick (the probe called them once a second too). 1.0.1e:
  they are gone: our own `SphereTraceSingle` (10 cm, 3.5 m, visibility, player ignored) from the camera sets
  `LookActor` / `LookComp` each tick before the steps; the probe dumps every plain property of the body's `DeadBody`
  and `DeadBodyHoldComponent` once a second while looking at a body (and no longer calls the PC getters).
- 1.0.1e (own sphere trace, no PC interaction getters): Noah: "no change" (prompt a dot, hold does nothing; tap
  touch + window and loose items fine: TouchState 1 / 2 / 3 seen). So none of our calls is the cause: every call the
  actor makes near a body before a press is pure, and the input path is untouched since 1.0.1d. Remaining suspects:
  the base mod's existence (subsystem + ticking actor; 0.1.0 never had the carry tested) or something outside the
  mod. The probe's component dump printed nothing: `ForEachProperty` lists a struct's own properties only; it now
  walks the class chain and also dumps `PlayerInteractionComponent`.
- Noah (2026-10-10): no more probe-only runs, every run carries a change. Fact: a LOOSE item's hold prompt ("hold F
  to use") shows and works with the release build (our reach plays, then the item's use animation): the game's hold
  system is fine with the mod; only the body's carry is dead. UE4SS Lua here has no class property enumeration
  (ForEachProperty nil); the UE4SS GUI (header dump) was declined; settings restored. 1.0.1f: bisect by change:
  `CORPSE_TOUCH = False` in the generator skips the corpse branch of T0 (IsAlive, GetComponentByClass DeadBody,
  TapComp, pelvis target): bodies are plain vanilla, stashes keep the touch.
- 1.0.1f (corpse branch off): Noah: "no change; when I loot a body the hand still comes out too". The hand: the press
  handler only checks `IsValid(LootComp)`, and since the trace LootComp is whatever the crosshair hits (the body's
  mesh, a wall): BUG, the press path must also require `Lootable`. The carry: dead with no corpse reads at all. So
  the body carry is killed by the mod's presence, while a loose item's hold works. 1.0.1g (no paste): the actor's
  `PrimaryActorTick.bStartWithTickEnabled` = false on the CDO: the subsystem still spawns it, nothing of ours runs.
  Carry back = the cause is in the tick (then bisect the steps); still dead = subsystem / actor existence / pak.
- 1.0.1g (actor never ticks): Noah: carry still dead, prompt a dot (and no touch, as expected). So nothing the actor
  DOES is the cause; the loose item's hold works. Left: the mod's content / registration. GFD actions:
  AddToContentPackAction, AddConfigsPathGameFeatureAction, GameFeatureAction_AddWPContent (kit defaults). 1.0.1h: the
  unused `IA_ImmLootInteract` / `IMC_ImmLoot` deleted (an InputMappingContext asset in the pak is the one thing of
  ours that touches input even unused, if the game scans contexts), the tick back on, the corpse branch back on, the
  press requires `Lootable` (the wall / body press bug).
- 1.0.1h (input assets deleted) and the dev probe removed: Noah: still a dot. Noah: "before Immersive Looting this
  worked", not other mods. Everything executed and every asset is excluded, so the remaining suspect is STATE the mod
  left behind: the first touch builds (patch_touch3, 2026-10-10 ~10:50) called `PC.RemoveLeftHandFromItemEnded` at
  every touch and never `ReturnLeftHandOnItemEnded` (its grip report never fired); `IsLeftHandBusy` has read true at
  rest in every log since; the carry is a left-hand action; a player state can be in the save. 1.0.1i: once per
  world the actor calls `ReturnLeftHandOnItemEnded`.
- 1.0.1i: Noah: "finally. holding F picks up a body" (the carry is back); only the "hold F" legend is still a dot.
  CAUSE of the dead carry: a dev build's `RemoveLeftHandFromItemEnded` without the matching `ReturnLeftHandOnItemEnded`
  left the player's left-hand state set (persisted in the save); nothing in the shipped mod, nothing in the probe.
  The once-per-world `ReturnLeftHandOnItemEnded` stays in as a safety. The missing legend: the carry prompt is a
  contextual hint; ImmersiveCampfires overrides `HUDContextualLegend` with LegendText collapsed (guitar hint), which
  would hide every contextual hint, the carry's included (loose-item hold prompts come from the interact view, not
  the legend: they show).
- Noah: the carry hint is attached to the body (world-space, like the loot hint), not the bottom-centre legend: the
  Campfires override is NOT it (retracted). Every bisect step before 1.0.1i ran under the poisoned left-hand state,
  which alone kills the carry, so they say nothing about the hint. Redo from the clean state: 1.0.1j = the actor's
  tick off again (no paste).
- RELEASE REQUIREMENT (Noah): the Nexus update must repair users' saves so they can carry bodies: keep the
  once-per-world `PC.ReturnLeftHandOnItemEnded` in the shipped Blueprint (1.0.0 never made the poisoning call, so
  users' saves should be clean, but the reset covers it either way) and say so in the changelog.
- 1.0.1j (tick off, clean state): Noah: carry dead again, dot, no touch. The reset lives in the tick, so it did not
  run: the state is re-read from the save at every load; the reset must run every load (it does when the actor
  ticks). 1.0.1k: tick on, and `PC.EnableInteractions()` once after the reset (the HUD's hold hints may be switched
  off together with the left-hand state).
- 1.0.1k (reset + `EnableInteractions`, layout fixed): Noah: carry dead, dot. The only logic difference to 1.0.1i
  (which carried) is `EnableInteractions` and the timing of the once-per-world reset. 1.0.1l: `EnableInteractions`
  removed; the reset also runs each time a new body comes into sight (`ResetFor` != its search component), never
  during an interaction or a LeftHand animation. Layout bug found and fixed in the harness (`layout_tree`: two boxes
  linking both ways lost every root, nothing was laid out, 818 of 1777 nodes outside the boxes; since 1.0.1e).
- 1.0.1l (per-body reset): Noah: carry dead, dot. 1.0.1m: the per-body reset removed (back to 1.0.1i: once per world),
  new setting `TouchBodies` (default true; off = corpses / stashes are not `Lootable` for us = pure vanilla; written by
  the coming MCM toggle). Noah on the 10:08 and 13:13 saves of 2026-10-10: no change. Then with Immersive Looting
  REMOVED (no pak at all, every other mod on): the 10:08 save still cannot carry. The 2026-10-09 17:13 save (made
  ~4 h before Immersive Looting first ran in game, same mod list including the three mods installed 2026-10-09 23:12)
  CARRIES. So Noah's later saves hold a broken state that survives removing the mod; every bisect step 1.0.1a-l ran on
  such a save, which is why none of them said anything. Source still unknown (a dev build of 2026-10-09 evening is the
  window; 1.0.1m does not repair those saves).
- 1.0.1m on the clean 2026-10-09 17:13 save, full sequence (carry; 3-4 loose items then carry; tap a body = touch +
  window, then carry; tap a stash, then carry; save, reload, carry): Noah: "carrying bodies fully works"; the loot
  window on a body also opens sooner than in 1.0.0 with the touch still looking right (no timing value changed; 1.0.0
  removed its input context and the input map was rebuilt before the injected press counted). = rc-1.0.1
  (`zonekit/builds/rc-1.0.1/`).

## 2026-10-12 — 1.1.2 a: item used from the loot window; bag looting
- Report (Nexus, Tim0st, video; Noah after re-watching it: the player right-clicks an item in the loot window and
  uses it; when the window closes our return animation plays and the hand inverts during it, just before the vanilla
  use animation). The use (MainActionSlot, ActionGroup) does not stop our LeftHand touch / FullBody additive, which
  come after it in the arm layers: our return posed the arm over the use. A first reading (our recovery
  `MG_fp_return_left_hand_on_item` over a weapon put-away) was dropped on Noah's word. Probe fact (2026-10-12 log): with
  a weapon, every pickup's recovery plays that montage when our grab starts blending out (Montage_IsActive is false
  while blending out, and the "cut" test is time-based): unchanged, it looks right in game.
- Build a, fix (Noah: "our return animation should still play, with our custom use animation like when holding F on a
  loose item, where we freeze on the first frame"): a use montage starting while the window is open and our touch /
  bag is out is held on its first frame like a hold to use (`UseMode`, `LootUse`, twins hidden until the grab) and our
  touch stops then (the world stands still while the window is open, so it is gone by the close); at the close, step 3
  plays the use reach for that use (`AS_ImmLoot_<use montage>`, aimed at the body / stash) over the held frame, the
  hand takes the item there, and the use goes on (as a hold to use). The "action" and "left-hand" skips do not apply
  to it. Any other game montage that took the arms since our reach: ours goes in 0.1 s, no return (`bused`); while on
  the way back (`BackAt`) the same (6c); the recovery montage yields to a use started after it (`RetAt`) and is not
  played in the tick a game montage started.
- Build a, bag looting (Noah: "an optional MCM toggle, on by default, that uses the bag animation (like opening the
  player's inventory) when looting bodies and stashes"): kit research: the inventory animation is
  `MG_fp_backpack_inventory` (MainActionSlot; In 1.5 s, Idle, Out 0.667 s, OutFast; `UseHandItem` notify at 0.567 s
  opens the inventory, so it is not played) plus `MG_backpack_fp_inventory` on `SK_bpa_pla_01` (`AnimBP_Backpack`,
  `BackpackPrototypes.cfg`; material `MI_bpa_sta_09_a_01_fov`, first-person). The bag's root bone is keyed in the
  player's component space; the player animation keys `jnt_weapon` behind the back (-49, -7, 120) throughout, and the
  Out ends with both hands down out of view. `make_bag_seq.py` copies In / Out into `AS_ImmLoot_BagIn` / `BagOut`
  (all 110 tracks, HandIK off at the start, on near the end, `left_hand_curve`); the actor plays them in MainActionSlot
  (rate 1) and spawns a SkeletalMeshActor with the backpack at the player mesh's origin playing the bag's own In /
  Out; held at 0.6 s like the touch, Out after the window, the backpack destroyed when its animation is over.
  Setting `BagLoot` (default on; MCM "Bag for bodies and stashes").
- Build a result (Noah): no bag: "the hand holding nothing"; with the hand touch "the hand stays reaching out over the
  stash, then the use plays at once with no tween". Probe: bag spawned (NBag 1); the use was never caught (NLootUse 0):
  as the window goes the game starts one montage at once (not "_use": by its timing the hands' `MG_fp_bh_unequip`,
  bh/showhide), the use ~0.4 s later (after our close step), and ~2.7 s later another (`MG_fp_bh_equip`). Engine:
  `ASkeletalMeshActor` ticks its pose (`AlwaysTickPose`) but refreshes bones only when drawn: our backpack stayed in its
  reference pose (worn on the back, behind the camera), never drawn, never posed.
- Build b: the close step waits up to 1 s for the use (`LootWait`, our touch held where it is); a use starting during
  the touch or that wait is held on its first frame (`LootUse`); once the window is gone our touch / bag goes and the
  use reach plays over it, from its grab frame after a touch (`LootFromGrab`: the hand is out at the body / stash with
  the item, then comes back into the use pose); no use in 1 s = ours goes (no return). Backpack: bones refreshed
  always (`AlwaysTickPoseAndRefreshBones`) and the player mesh's bounds. Probe: `GameMontageName`, `BagF/R/U` (the
  bag's jnt_backpack in view axes), `BagPlay`.
- Build b result (Noah): still no bag (and: bag looting off by default); with the hand "it holds for a second, snaps
  down and right and goes straight into the use". Probe: the use was caught (NLootUse 1, 2), but the build-17 fail-safe
  (`_late`: UseMode and no reach of ours playing) fired in the same tick step 6c asked for the reach: the use went on
  (NUseLate) and the reach played as a plain pickup segment (SegStart 117 / 118.5). Backpack: posed but still, 61 cm
  ahead and 81 cm below the view: the bag sequences lock their root to the reference pose (`bForceRootLock`), and their
  keyed root equals the player's `jnt_l_weapon` (= `jnt_second_weapon`) in every frame, rotated -90 deg about X = the
  root's own reference rotation: the game holds the bag in the left hand.
- Build c: the fail-safe waits while a reach is pending; the backpack is attached at `jnt_l_weapon`; `BagLoot` off by
  default (actor and MCM). A Lua probe read of the String variable `GameMontageName` crashed the game while loading a
  save (UE4SS): removed from the probe (harness/docs/diagnostics.md).
- Build c result (Noah): the bag shows, but "in front of the face for a bit before the normal animation"; the use reach
  "starts to reach back, resets, then does the correct full reach back with the item". The game's own montage blends
  in / out in 0 s (ours 0.25: the arms carried the bag across the face to the In's first pose). Probe: step 6c stopped
  our touch a tick before step 3 started the use reach.
- Build d: In blend-in 0.01 (a pasted 0.0 reads back as the 0.25 default), Out blend-in 0.1; the touch is kept
  (`LootTouchMont`) and stopped in the tick the use reach starts (or is skipped).
- Build d result (Noah): "the bag is supposed to have the right hand going into the bag: copy the ENTIRE vanilla
  animation"; "the bag is not off by default" (probe: the actor starts with BagLoot false, MCM's saved value from
  Noah's own earlier choice turns it on at load: MCM keeps a player's setting); the use reach unchanged ("starts to
  reach back, resets, then the full reach back"). Probe: the use reach played from its grab frame 0.07 s after the use
  started; the touch was stopped with a 0.15 s blend in that tick: the reach is an additive on the held use frame, so
  while the touch still shaped the arm the reach was bent.
- Build e: the bag In plays to its end (1.4 s, the right hand reaches into the bag), then `AS_ImmLoot_BagIdle` (the
  game's idle, the hand in the bag) loops while the window is open (with the bag mesh's own idle), Out after; In blends
  out in 0.05 s into the idle. The held touch stops at once (0.01 s) when the use reach starts. Probe (numbers only):
  `GameMontageKind` (1 unequip, 2 equip, 3 use, 4 backpack), `GameMontageLen`, `TouchStopped` (to see what the game
  plays as the window goes and whether it stops our touch).
- Build e result (Noah): use return "no change"; "the closing bag animation is janky too". Probe (montage kind / length,
  numbers only): as the loot window goes the game plays the weapon's "unequip" (kind 1, 0.467 s), the use 0.36 s later
  (kind 3, 2.97 s); our touch is NOT stopped by it (TouchStopped false until our reach): our left arm rode the
  lowering shoulders, then the use reach (2 ticks after the use) put it back out. The player's own inventory (I key):
  unequip (0.43-0.47 s) -> MG_fp_backpack_inventory (kind 4, 7.5 s) -> equip (0.5 s) at the close. Our Out blended
  out over its last 0.3 s (hands rising while the Out still lowered them) with nothing after it.
- Build f: an unequip while our touch is out or just after it plays 8x as fast; a use caught after the window is gone
  starts our reach in the same frame (`loot_use_go` from the montage event). Bag: a weapon in hand is put away at the
  bag's start (`RemoveWeaponFromHands`, `BagWeapon`) and drawn by the game (`EquipLastHeldItem`) once the bag is gone
  and the arms are free (unless already shown); empty hands: `MG_fp_bh_equip` after a played-out Out (as the game's
  inventory); Out blends out in 0.05 s.
- Build f result (Noah): use "much better, but a frame or flash of the arm disappearing and swapping"; bag "the right
  hand clips into the bag and it hijacks the camera and looks down". Probe: view pitch -51 -> -75 for the whole bag
  (the player's own inventory leaves it alone); the weapon had been put away, so the bag played in the bare-hands
  layer. The game plays its bag over the rifle-type stance (`AnimCollection_fp_Backpack` -> `AnimCollection_fp_ar`).
- Build g: weapon in hand: the bag in MainActionSlot over its stance again (no put-away), the Out blends out after its
  last frame (0.35 s); empty hands: `AS_ImmLoot_BagInAdd / IdleAdd / OutAdd` (make_bag_seq add=True: local-space
  additives on fp_bh_idle_stand, upper body only, spine root re-solved for the bare-hands hips) in FullBody from
  frame 1, `MG_fp_bh_equip` after the Out. Use from the window: the item shown in the hand at once (no twin hide
  frame), the use reach blends in 0.001 s, the backpack destroyed when the use reach takes over.
- Noah on build g's plan (an additive copy for empty hands): "the open inventory animation is VANILLA; did you fully
  research how it works?" No: the inventory animation is driven by native code: `PC.StartUseBackpack` (the backpack as a
  hand item: `HandItem` BACKPACK, `AnimBP_Player_TwoHandedItem` + `AnimCollection_fp_ar`, `SetHandItemSkeletalMesh`
  with `AnimBP_Backpack` (a DefaultSlot over the bag idle), both montages, `AnimNotify_UseHandItem` opens the
  inventory, `OnBackpackUseEnded` the Out and the weapon draw). The pawn Blueprint has none of it. The game also has
  `PC.OpenLootMenu` / `CloseLootMenu` and `AnimNotify_InteractAction` (OPEN_LOOT_MENU / CLOSE_LOOT_MENU) for animations
  that open a loot menu. Builds a-g reproduced only the montage part by hand (copies, attach, layer, camera): dropped.
- Build h (test): a bag tap calls `StartUseBackpack`; once the game's inventory is open (`IMC_Inventory`,
  `IsUsingBackpack`) `OpenLootMenu` is called. Probe: `NBag`, `NBagLoot`, `BagUsing`, `InvOpen`, `LootKind`.
- Build h result (Noah): the bag "just opens my inventory, not the stash"; the use from a stash "finally looks
  correct". Probe: the game's unequip, then IMC_Inventory at 0.45 s (before its bag montage, kind 4, starts) with
  IsUsingBackpack; `OpenLootMenu` called then changed nothing lasting (no interaction in progress for it to open).
- Build i (test): the moment the game's inventory is open, its own close input `IA_UI_Inventory_Close` is injected (the
  backpack goes back natively), and once IMC_Inventory is gone, the game's interact (T8: after 0.12 s, retried) opens
  the stash's / body's loot window as without the bag. Watch: a flash of the inventory; the bag's Out against the
  loot window.
- Build i was not built (Noah: closing the game's inventory to open the loot window "will almost certainly just close
  the inventory animation"; no jank-prone tricks). Research: no Blueprint route puts the game into its backpack state
  but `StartUseBackpack`, which always ends in Skif's inventory. The posture the game plays its bag over is
  `AnimBP_Player_TwoHandedItem` (implements only `AnimLI_PlayerWeapon`: the WeaponLayer, ungrouped), linked by the
  native backpack use; `AnimBP_PlayerWeaponLayer` / `AnimBP_player_bh` are the firearm / bare-hands WeaponLayer classes.
- Build j: at a bag tap the WeaponLayer instance's class is remembered (`GetLinkedAnimLayerInstancesByGroup(None)`,
  the one implementing AnimLI_PlayerWeapon) and `AnimBP_Player_TwoHandedItem` linked (`LinkAnimClassLayers`); the
  copied In / Idle / Out play in MainActionSlot over it for both weapon and empty hands (the additive set unused);
  when the bag is gone the remembered class is linked back if the backpack posture is still linked. Noah still sees
  the right arm clip through the bag flap in the earlier own-bag builds: to watch with the game's posture.
- Build j result (Noah): "I didn't see the right hand at all and the game crashed when I closed the stash loot window".
  Game log: AV in game code at 09:14:50.8, 0.5 s after our Out started (the posture link-back had not run). Linking the
  game's posture from a mod is a crash family (harness/docs/animation.md). Reverted (the bag tap back to build g's
  path; not rebuilt). The posture's AnimGraph shows what it adds over the montage (camera / weapon from virtual bones,
  spine_03 from another pose in component space, a smooth copy of the right forearm): harness/docs/animation.md.
- Build k (Noah: "yes let's do it": the bag as an arms-only layer over Skif's posture). Slot study: every full-pose slot
  a mod can reach in the bare-hands layer takes the camera (MainActionSlot: legs mask only; UpperBody: `under_hips`
  mask; FullBody: everything); only LeftHand / RightHand are masked to the arms (`left_hand_blend_mask` /
  `right_hand_blend_mask`, shoulder down). Both are DefaultGroup, so one dynamic montage per slot stops the other:
  montage assets `AM_ImmLoot_BagIn / Idle / Out` (`make_bag_montages.py`) with a LeftHand and a RightHand track (set by
  Noah in the montage editor: Python cannot edit slot tracks), played with `Montage_Play(bStopAllMontages false)`; the
  previous montage of the bag stopped explicitly. Weapon in hand: `RemoveWeaponFromHands` at the start (the hand masks
  leave `jnt_weapon` alone), `EquipLastHeldItem` after the bag (if the game has not drawn it); empty hands:
  `MG_fp_bh_equip` after a played-out Out.
- Build k result (Noah): "the right arm still clips through the backpack, too far up, not through the flap opening";
  "after the stash it forces me unarmed; the weapon key needs two presses". Cause of the second: the weapon redraw
  block never made it into the generator (a CRLF mismatch in the edit script; the file is LF now), and our AM_ montage
  assets counted as the game's in `GameMontageAt` (so no hands-up either). Data check (copied animation, bag frame =
  jnt_backpack, root locked): right hand (-1.2, -10.8, -1.3), middle fingertip (4.6, -1.6, 2.5), the bag's bones span
  x -16..16, y -26..14, z -22..4.4 (top caps to 3.5): the animation itself has the fingers at the flap's level.
- Build l: weapon redraw restored (`EquipLastHeldItem` once the bag is gone and the arms are free), `AM_ImmLoot*` not
  counted as game montages; probe `RHand*` / `RFing*` = the right hand / middle fingertip in the backpack's frame in
  game, to compare with the data above.
- Build l also: probe of the game's own backpack while it is in use (I key): `VRHand*` / `VRFing*` (right hand / fingertip in its jnt_backpack frame), `VAttL` / `VAttS` (its root to the player's jnt_l_weapon / jnt_second_weapon, cm), `VBag*` (its jnt_backpack in view axes), `VBagComp` (1 secondary-hand mesh, 2 in-hands mesh).
- Build l result (Noah): right hand unchanged (clips through the flap), weapon still needs two presses after the
  stash; standing, the bag plays "way above the screen" (crouched roughly right). Cause (data: look-vertical deltas):
  the bare-hands standing look additive (`fp_bh_stand_lookvertical_idle`) leaves the hands where they are when looking
  down while the camera turns, so the arms layer lands above the view; the rifle and low-crouch look additives turn
  spine, arms and camera together. The game's bag posture turns the arms with the view.
- Build m: armed, the weapon stays in the hands, hidden (`SetHiddenInGame` on `GetWeaponInHandsMeshComponent`), shown
  again when the bag is gone (no `RemoveWeaponFromHands` / `EquipLastHeldItem`), so the weapon posture's rigid look
  turn carries the arms. Empty hands: `AS_ImmLoot_BagPitchFix` (`make_bag_seq.py --arg PART=pitch`, 91 frames =
  view pitch 0..-90, mesh-space rotation offset: shoulder subtrees turned by the spine's look turn and the bare-hands
  look's own arm turn undone) in FullBody, paused, its position = pitch down / 30 every tick (0 crouched: camera below
  130 cm in the mesh frame), stopped 0.3 s when the bag is gone.
- Build m result (Noah): standing, the bag is on screen and the left hand is right; the weapon comes back after the
  stash; but armed, the right hand "still holds the weapon that isn't there", the elbow bends up, the hand never goes
  into the bag. Cause: the weapon layer's right-hand IK (`TwoBoneIK_GSC` on `jnt_r_hand` to the weapon mesh's
  `jnt_r_hand` socket, alpha `HandsIKData.RightHand.Alpha`) still pins the hand to the hidden weapon's grip.
- Build n: `AS_ImmLoot_BagIn` / `BagOut` carry a second `AnimNotify_HandIK` for the right hand (off at the start of
  In, on at the end of Out), like the left one. No Blueprint change.
- Build n result (Noah): "right hand is perfect, finally fixed". Left: the bag pops for a frame or two on the left at
  the open; at the close it "turns in place instead of going down and off screen with the left hand". Probe: first
  frame after the spawn the bag sat (40, -92, -106) cm in view (its reference pose); at the close it rose from
  (38, -17, -27) to (47, 0, -18) = back to the weapon grip. Data (game's Out, `jnt_l_weapon` in `jnt_camera`): the bag
  drops to (25, -9, -36) by frame 18 (0.6 s), the last frame (20) snaps behind the back; our Out's 0.3 s auto blend-out
  started at 0.37 s.
- Build o: the bag hidden for its first 3 ticks (`BagShowTick`); `AM_ImmLoot_BagOut` blend-out 0.25 s triggered at its
  end only (`blend_out_trigger_time` 0); at Out 0.6 s the actor pauses it, stops it (0.25 s) and stops the bag mesh's
  animation, so the cleanup removes the bag (then the weapon shows / the empty-hands hands-up).
- Build o result (Noah): no backpack at all (the show step's condition was negated: `BagShowTick > 0` under a NOT);
  at the close "the weapon appears floating in the air and then the hands come up to grab it".
- Build p: show condition fixed; the game's last weapon equip montage is remembered from `OnMontageStarted` (kind 2,
  not `_bh_`; e.g. `MG_fp_ak74_equip`: MainActionSlot 1 s, HandIK both on, WeaponAction unlock-left-hand idle,
  PlayerAction END EQUIP_MAIN_ITEM) and replayed at the Out's 0.6 s with the weapon shown at the same moment (the game
  closes its own bag with the equip). None remembered: shown when the bag is gone. `MG_fp_bh_equip` only without an
  item in the main hand.
- Build p result (Noah): "almost perfect": the open looks great; at the close the weapon shows for a frame before the
  equip. Build q: the weapon shown 2 ticks after the equip starts (`WeaponShowTick`; our tick runs after the animation
  update, so the equip poses the weapon from the next frame).
- Build q result (Noah): "bag is perfect, done and delivered". Checkpoint `checkpoint-bag` (paks in
  `zonekit/builds/checkpoint-bag/`).
- After checkpoint-bag (Noah): bag off, a stash touch with a weapon, "when the
  hand returns to the weapon it does the rotate and twist 360 thing" (the session's first report; Nexus, Tim0st).
  Data: the armed grab / touch (copies of the vanilla `MG_fp_ak74_weapon_grab`, 1.667 s, played at 1.15) blended out
  over 0.7 s from 0.97 s montage time = frame 29, inside the hand-at-the-chest frames 23-34 whose `jnt_l_hand` local
  rotation is 120-180 deg from every weapon idle (ak74 173, dnipro 171, fora 170, pistols 142-162). A local-space blend
  across ~180 deg flips direction as the frames change: the hand spins. By frame 40 every rifle / pistol / shotgun
  idle is within 100 deg.
- Build r: the armed grab (`mp`) and touch (`mpt`) blend out over 0.35 s (from frame ~40). Loose-item armed pickups
  had the same blend.
- Build r result (Noah): "still twisting awkwardly when returning to the weapon". Data: the touch's way back (frames
  20-36) re-solved only upper arm / forearm / hand with the elbow pole and shoulder from the vanilla grab's own frames
  (hand to the chest and flipped back onto the grip, 23-34): the solved upper arm swung 55-64 deg in single frames,
  and the untouched roll / shoulder / finger tracks twisted with the vanilla motion.
- Build s (assets only, `make_grab_seq.py --arg PART=touchret`; also in `build_touch_one`): every left-arm track of
  `AS_ImmLoot_Touch0..24` plays the reach in reverse after the hold (frame 18 + i = frame 18 - i), the start pose
  (the grip) from 36 on (the IK-on notify). Largest per-frame step now 29 deg (the reach-out's own). Blueprint as r.
- Build s result (Noah): "no change". r and s changed everything before frame 36 and nothing after it, so the twist is
  at the end: the left-hand IK came on at 1.2 s over 0.2 s with the hand in the vanilla AK grab's grip pose, 35-98 deg
  (local) from the held weapon's own grip (ak74 idle 52, pistols 90-98).
- Build t: touch IK-on at 0.8 s (the hand starts back) over 0.5 s (`TOUCH_IK_ON`, `touch_notifies`; assets via
  `--arg PART=touchret`). Probe: per tick, the left hand's turn in the camera bone's frame (hand forward / up axes,
  forearm up axis) for 2.5 s from the reach start or the way back: `TwStep`, `TwPos` (our montage position), `TwMax`
  at `TwMaxPos` / `TwMaxT`, `TwSum`, `TwLate` (from montage 1.1 s), `NTwBig` (> 20 deg steps).
- Build t result (Noah): "still looks like it's twisting". Probe (works): the hand's turn per tick stays under 15 deg
  from the animation itself, but jumps 71-82 deg in one tick on the way out (montage 0.18-0.25 s) and 125 deg on the
  way back (~1.0 s), each inside the left-hand IK's off / on blend: the IK's grip (the weapon's own `jnt_l_hand`
  socket) and our keyed grip (the vanilla AK grab) are far apart, and the IK's blend between them flips.
- Build u: armed body / stash touches are left-arm local-space additives (`AS_ImmLoot_TouchAdd0..24`, from the touch
  assets, base frame 0, shoulder subtree only, no notifies, no curve; `make_grab_seq.py --arg PART=touchadd`) played in
  FullBody (after the weapon layer and its IK, which stays on). Doors keep the LeftHand touch (`mpt`).
- Build u result (Noah): "way worse: the normal reach out looks totally broken, like the hand is jelly or alien".
  Reverted (assets deleted). Dead end: a left-arm local additive (against the AK grab's frame 0) over another
  weapon's grip pose in FullBody.
- Build v: the LeftHand touch of build t back; touch notifies: IK off at 0.036 s over 0.06 s (the reach-out turns the
  hand ~170 deg by frame 7, the default 0.2 s blend crossed 180 deg = the way-out flip at 0.18-0.25 s), IK on at 1.2 s
  (frame 36, the start pose again) over 0.25 s.
- Build v result (Noah, pistol): "very obviously twisting when coming back". Probe: 76-116 deg in one tick at montage
  0.10-0.20 s (the LeftHand slot's 0.2 s blend-in), 23-30 deg a tick for ~0.3 s on the way back. Data: the touches
  start / end in the vanilla AK grab's grip, 9.7 cm / 88 deg from every pistol's support grip (kora / apb / pm / udp /
  rhino within 2.6 cm / 24 deg of each other), and their wrist rolls ~170 deg with the vanilla reach.
- Build w: with a pistol (`GetMainHandEquipType` = 1) the touch is `AS_ImmLoot_TouchPt<bin>` (`make_grab_seq.py --arg
  PART=touchpt`): every left-arm track at `AS_fp_pm_idle` frame 0, only upper arm / forearm solved to the same point
  (elbow pole turning from the pistol pose's own to out-left-down: the rest pole flipped the low-left bins 30-35 deg a
  frame), hand at the pistol grip wrist (no roll); out by 12, held to 18, back by 36; max step 13.5 deg a frame.
- Build w result (Noah): pistol "no more twisting, but the hand isn't facing away from the player, it looks like it is
  still holding a grip instead of a high five facing away"; rifles still twist. Research: the game authors its own
  left-hand gestures per weapon family (`MG_fp_ar_flashlight`, `MG_fp_pt_flashlight`, `MG_fp_bh_flashlight`, NVG
  per family...). Long-gun idles' left hands (rifle / SMG / sniper / shotgun) lie within 0-64 deg of
  `fp_ar_idle_stand` (m10, bucket, integral, m16 grip farthest), 32 deg from the old touches' start.
- Build x: `build_touch_pistol(i, family)` for "pt" (`AS_fp_pm_idle` -> `AS_ImmLoot_TouchPt`) and "ar"
  (`fp_ar_idle_stand` -> `AS_ImmLoot_TouchAr`, now every long gun's touch): the hand follows the swung forearm, then
  turns one way round to the palm facing the target, fingers up (`palm_q`), the fingers opening (the dialogue open
  hand), over frames 5-17 (after the slot's blend-in, so the blend only spans grip-to-grip gaps: <= 60 deg for most
  weapons, 108 for the m10), back over 19-31; half the turn about the forearm goes to `jnt_l_fore_arm_roll`. Largest
  per-frame step 14 deg (pistol), 28 deg (rifle, low-left bin: a ~170 deg palm turn).
- Build x result (Noah): "the twisting is now totally gone". But: fingers should be spread, the hand angled down and
  away a bit ("too robotic and upright"); on the way back the hand goes too far right (clipping the gun), then left
  into place.
- Build y: fingers from `AS_fp_dialogue_bothhands_statement` k70 (searched vanilla left hands with straight fingers:
  max index-pinky spread 49-56 deg; the old door hand ~20); palm toward the target tilted ~30 deg down
  (`TOUCH_PALM_DOWN`), fingers leaning out-left ~20 deg (`TOUCH_FINGERS_UP`; `palm_q` up vector). IK on at 1.0 s
  (frame 30, palm already back) over 0.35 s so the hand converges on the real grip while travelling in. Probe adds the
  hand's offset from the held weapon's left-hand socket in view axes (`TwGF/TwGR/TwGU` cm) and the farthest right
  (`TwRMax` at `TwRMaxPos`).
- Build y result (Noah): better; the hand "twisted counter clockwise too much, like breaking the wrist"; on the return
  the hand clips through the barrel to the grip (pistols and rifles). Probe: on the way back the hand came from above
  the grip and passed it 3.5 cm right / 3-5 cm above (rifle), straight down from above-left (pistol).
- Build z (assets only): fingers lean `TOUCH_FINGERS_UP` (0, 0.1, 1) (was out-left); the hand path is a quadratic
  curve through `TOUCH_EXIT` (2 fwd, 10 left, 5 down cm of the grip), so it leaves and rejoins the grip from the left
  and below (checked: frames 30-34 at (1,-4,-2) .. (0,-1,0) cm of the grip).
- Build z result (Noah): wrist angle good; still clips through pistols and rifles on the return; at the end "the hand
  goes left and right slightly before it settles". Probe: rifle returns go from 4 cm left to 3 cm right of the
  weapon's grip at montage 1.05-1.1 s (2 cm above), then back to 0: the stand idle's grip R sits ~3-4 cm right /
  2.5 cm above the held rifle's own grip, and the IK (on from 1.0 s) pulled the hand back from R. ZST's watch check
  (extracted, `zen_names`): montages in the LeftHand slot with `left_hand_curve` and an `AnimNotify_HandIKState`
  window (Grip / Free variants), plus `BPI_WatchPose013.SetWatchPose013(Alpha, PreserveGrip)` implemented in its
  own `AnimBP_Player` override: its smooth hand-back comes from that override, not available to us.
- Build za (assets only): the touch path starts / ends at R + `TOUCH_END_OFF` (1 fwd, 5 left, 4 down cm), leaving and
  rejoining through R + END + `TOUCH_EXIT` (2, -8, -6): the IK takes the hand to the real grip from the left / below.
- Build za result (Noah): "YESSSS perfeeeeccctttttttt. clean it up and get it ready for release".
- Release cleanup: probe chains of builds l-za removed from the actor graph (backpack view / right-hand / vanilla
  backpack probes, the build t / y hand turn and grip-offset logger); unused assets deleted from the kit, the repo
  mirror and NewPackages: `AS_ImmLoot_Touch0..24` (replaced by the family touches), `AS_ImmLoot_Bag*Add` (unused since
  build k), `AS_ImmLoot_ArmHold`, `AS_ImmLoot_PickReach` (no referencers); the generators no longer build them.
- Door build A (push / pull from the leaf's motion; closets / cabinets / lockers count as doors). Probe: 6 door
  presses decided in 0.11-0.19 s: opening moved the pressed point 4-10 cm away (push), closing 3-4 cm toward the
  camera (pull) on leaves open at -85 and +85 deg. Tester: "the animation still looks bad: the hand clips through the
  gun and the fingers look weird as they settle into the resting pose; the return should go in a downward arc under
  the pistol or rifle".
- Door build B: `build_door_family(family, mode)` (`--arg PART=doorfam`): `AS_ImmLoot_DoorPush/PullAr` (rifle stand
  idle) and `...Pt` (pistol idle) with the touch recipe; the path leaves / rejoins the grip through `DOOR_ARC` (3 fwd,
  4 left, 14 down cm from the path's end): a downward arc under the weapon (checked: return frames 24-28 at 11-14 cm
  below the grip); push = spread palm + stroke 8-14, pull = palm inward, hand closes 8-12, drawn back 12-26, opens
  26-32; fingers back to the stance's own; IK on push 1.0 s / pull 1.13 s over 0.35 s. Blueprint: a pistol picks
  `...Pt`, other weapons `...Ar`; empty hands keep the BH assets.
- Door build B result (Noah): loaded after one crash at load (UE4SS frame on top, 2 s after our actor started, while
  UltraExtensions set its world cvars; not reproduced on the retry); "honestly looks pretty good. maybe the push
  could use more of a push, the hand just kinda stays static when pushing".
- Door build C (assets only): the push comes up nearer the body (`DOOR_PUSH_STROKE_FAM` 24 cm back from the door, was
  14) and drives forward accelerating (ease-in, frames 8-14): ~20 cm, the last 6 cm in the final frame before the
  Blueprint's hold.
- v1.3.0 (Noah: "cut a release"): door builds A-C; release cleanup: the replaced armed `AS_ImmLoot_DoorPush` /
  `DoorPull` deleted (kit, mirror, NewPackages; `build_doors` no longer builds them).
- After v1.3.0 (not published; Noah: keep building on it). Nexus feedback: Farsot (MCM option to not show the item
  in the hand: "looks like you're force pulling items"), Scorpius34 (loot corpses with both hands), bug MonaPona
  (1.2.0: "after looting multiple bodies very quickly the backpack glitched out and never went back to normal";
  picture: the bag fills the bottom of the view with the scoped rifle on it).
- Build n1: bag: a bag started while the last one was still on its way out replaced `BagActor` and the old one stayed
  attached to the left hand for good: the old bag is destroyed first; cleanup watchdog (no touch out, no bag montage
  active, 1 s after it started). MCM "Hide items in the hand" (`HideItem`, off): no flying copy at a pickup.
- Build n2: both hands on bodies (Nexus, Scorpius34; tester: not the mutant-looting animation (knife), "the right hand
  out the same way as the left, as if patting down the body"): `AS_ImmLoot_PatTable` (`make_grab_seq.py --arg PART=pat`):
  75 segments of 51 frames = family (rifle stance, pistol, bare hands) x the 25 touch bins; both arms from their own
  stance with the touch recipe (right hand: the left's palm-down orientation mirrored), out by 13, two alternating pats,
  held at 27 (0.9 s), back by 45; both hands' IK off / on; through `AM_ImmLoot_Pat` (LeftHand + RightHand slot tracks set
  by hand). Weapon hidden and drawn again with the last equip (as the bag); bare hands standing get the bag pitch fix.
  Pat end at segment + 1.6 s, a cut pat is cleared (`NPatCut`).
- MCM consolidation (tester: "consolidate some of the toggles in a dropdown"): "Body looting" (Hand / Both hands /
  Backpack / Off -> `BodyMode`), "Stash looting" (Hand / Backpack / Off -> `StashMode`), "Door animation", "Hide
  items in the hand". MCM combo boxes = setting type `NewEnumerator7` with `ComboBoxOptions` labels and
  `ComboBoxSelectedOption` (from MCM_ModExample1). `TouchBodies` / `BagLoot` / `PatLoot` are no longer read.
- n2b: pats slower (held at frame 33 = 1.1 s, out by 11, back by 47; same table length so the hand-set montage keeps
  working; the Blueprint holds the pat at 1.1 s). Montage checked: LeftHand + RightHand tracks, both the table.
- Nexus EMPERORTECH (1.1.1 with Weapon Reposition Project and Weapon Viewmodel FOV +20%): standing, the sleeve is
  stretched from the shoulder when picking up items and touching stashes with empty hands; crouched it is fine. Data:
  the standing and crouched pickup tables keep the arm equally far from the camera (31-38 cm for items below); the
  difference is the posture: standing, the bare-hands look leaves the arms level while the camera pitches, so looking
  down the shoulder and upper arm sit in the bottom-left of the view near the camera, where the arms' FOV squeeze
  (MF_Foreground) stretches them; crouched, the look turns the arms with the view.
- Fix: `build_use_table(..., follow_pitch=True)` for `AS_ImmLoot_GrabBHAdd` (`make_grab_seq.py --arg PART=pickstand`):
  `jnt_l_shoulder` keyed too, turned about `jnt_spine_03` by the row's elevation (the view pitch when looking at the
  item), eased in by frame 10 and out over 16-36; the arm solved from the turned shoulder (the hand still lands on the
  item).
- MCM fixes: (1) the combo types were lost on paste (a pin default written right after `PinName` is reset for enum
  pins): `defaults()` now writes `DefaultValue` where the editor does; combos renamed "Looting bodies" / "Looting
  stashes". (2) Dead settings ("Body looting" / "Stash looting" bools from that build, 1.2's "Body and stash animation"
  / "Bag for bodies and stashes") stay in the save and are listed: MCM (decompiled `BP_MCM_Manager`,
  `WBP_MCM_ModContainer`) lists all saved settings of a mod id but only mod ids added this session; no remove call.
  New mod id `"Immersive Looting "` (trailing space): the old id's entries are no longer listed. Saved values reset
  once to the defaults.
- n2c (tester: "still too fast and pats too many times: only 3 pats, slow and eased, not too slow"): three pats in
  turn (left, right, left), smooth dips over 9 frames each (frames 10-37), held at 37 (1.233 s montage time), back by
  48; `AM_ImmLoot_Pat` played at 0.78 (~0.38 s a pat). Table length unchanged (the hand-set montage still matches).
- n2d (tester: "pat in different places, as if searching the body"; "leaving the window the hands should go fully out of
  view before the equip; now you see the weapon appear, then the equip"): each pat on its own spot (`PAT_SPOTS`: left
  pats 1 and 3 ~11 cm apart, right waits then pats 2), the hand gliding between them; with a weapon the way back goes
  down out of view (`PAT_DROP`, ~35-40 cm below the stance grip by frame 48) and the table has no IK-on for the weapon
  families (the game's equip switches it on). Fallback without a remembered equip (right after a load): the hidden
  weapon is shown with the hands still down (IK off until the game's next IK notify).
- n2e (tester: pats "still robotic: moves, then down and up; should be one smooth eased motion in an arc"): `pat_off`:
  one continuous path per hand over the pat timeline: hovers 3 cm above its first spot, drops onto it eased in, lifts in
  a 6 cm arc to the next spot and lands, lifts off at the end.
- Bag on bodies, looting fast (tester: "sometimes the bag doesn't play and the window opens at once; sometimes no
  window for the body, then my inventory opens"). Probe: (a) most presses had the loot window open within 0.1 s of the
  tap (the game's own tap opened it before the bag showed); (b) one press came 34 ms after the last bag's weapon draw
  started: bag In took 2.7 s, the injected interact opened nothing, 2 retries, then a game montage (kind 0) and a draw.
  Fix (b): no injected interact while a game action plays (`MainActionSlot` active). Probe: montage kinds 5 inventory,
  6 interact, 7 pick, to name that montage next time. (a) not changed yet.
- n2e tested (tester): "sleeve looks fixed" (EMPERORTECH, `follow_pitch`); pats "a lot better"; bag looting fast "definitely
  better" but at speed the bag sometimes still does not appear, and once a tap on a body picked it up (carry).
- n2f, pat (tester: "rotate the hands up, toward the sky; a little too far rotated down, it doesn't look fully like a
  pat"): the palm was tilted toward the body's direction (fingers forward and down, ~12 deg); now `PAT_PALM_UP` 0.25
  tilts it back (fingers forward and ~14 deg up). Pat table rebuilt (patscan: no step above 39 deg, arms unchanged).
- n2f, bag at speed. Probe (session 14:31): (1) twice a press came during the last bag's weapon draw (our replay of the
  game's equip, `MainActionSlot`) more than 0.3 s in and was skipped as "action" (SkipBits 4): no bag. The skipped touch
  still ran the touch states: at its window's close it counted as "an item used from the window" (our montage stopped),
  set `LootWait`, and 1 s later that wait stopped the NEXT bag's In (NYield 1, BagPlay never true): a second missing bag.
  In the other case the player closed the window and the retry (`bwr`, TouchState 3, window not open) opened it again.
  Fixes: our own equip replay (`EquipReplayAt` >= `GameMontageAt`) no longer skips a bag / pat press, and the bag / pat
  start stops it (0.1 s) and cancels its weapon show; a skipped press on a body / stash / door clears its touch state
  (`reach_over`); every body / stash press clears `LootWait`; the retry needs no window opened since the press
  (`OpenAt` < `TouchPressAt`). (2) The carry on a tap (t 190.06): the F press was never a "just pressed" for the
  player controller (`InteractPressAt` unchanged, the key seen down 1-2 ticks), 0.36 s after the loot window closed;
  the game started the carry (unequip, kind 7 "pick") within a tick. Reading: F went down while the window was still
  closing (the UI took the press), so the game saw a key already held = a hold. Not changed: asked the tester how the
  window was closed.
- n2f, the carry on a tap: tester closes the loot window with Esc / Alt (custom inventory key), so F was not held across
  the close; the press after it was still never a "just pressed" and the game carried within a tick (as if the hold
  had been running since an earlier press: the window opened at that press's release). Fix: when a body's loot window
  closes (`TouchIsBody`, body looting on), its `DeadBodyHoldComponent` (`HoldComp`, found with the `DeadBody` in T0) is
  switched off (`HoldOffComp`, `NHoldOff`); our next fresh press on a body / stash switches it back on (the game then
  times the hold from that press) and the pressed body's own carry is switched on at every press (a save made during
  the block cannot keep it off); looking away from that body (T9) also switches it back on (`NHoldOn`).
- n2f tested (tester): pats worse, "tilted the wrong way, the wrists look broken, hands way too far down"; bag at speed
  and the tap carry both came back after ~10 bodies in a row, "the pick-up seems to happen right after the backpack
  not appearing". Probe (session 15:0x): bag fine for 20 bodies; then twice F was seen down (`KeyHeld`, 1-2 ticks) with
  NO "just pressed" (`InteractPressAt` unchanged), so our press never ran: (t 156.37) the game opened its plain window
  (no bag); (t 171.85) the game started the carry within a tick (unequip, then kind 7 "pick") on a 0.06 s tap. The
  carry block after the window (n2f) was already switched back on by the look-away rule (bodies side by side), so it
  never mattered: removed (the carry is not touched again; actor variables `HoldComp` / `HoldOffComp` / `NHoldOff` /
  `NHoldOn` left unused, delete before the release).
- n2g: (1) pat palm: n2f's sign was backwards (a palm normal tilted toward the body's direction lifts the fingers):
  `PAT_PALM_UP` 0.55 toward it (fingers ~29 deg up from flat; scan at the contact frame: ~20 deg above n2e). (2) T6:
  F down this tick and up last tick (`KeyHeldPrev`) with no "just pressed" counts as a press (`NPressEdge`). (3) the
  game's carry pick-up montage (kind 7) starting while F is up and was pressed under `HoldToDrag` ago (`TapCarry`,
  `NTapCarryPick`): T9 calls the game's own `Obj.DropCorpse` (with its animation) each tick until it returns true
  (`NTapCarry`); given up after 2.5 s or when F is held again.
- n2h (tester: "a safety net isn't good enough, the body pickup should never happen in the first place"): prevention.
  (1) A body press no longer switches the body's search (tap) interaction off. Since 1.0.1 every body press did; the
  window still opened at the release (logs: `InvOpen` true in the release tick), so with the search off it came
  through the hold interaction, the only one left: suspected to leave the carry hold half-done so a later tap
  finishes it at once. The game's own tap / hold on bodies now run untouched (stashes unchanged). (2) T10: the body we
  look at (`BodyHold`, its `DeadBodyHoldComponent`, found in T0) reporting `HoldComponent.IsHoldStarted` while F has
  been up 0.15 s and the left hand is free = a stale hold (`HoldStale`): its interaction is switched off for one tick
  and on again (`HoldResetComp`, `NStaleHold`). (3) n2g's press edge and the tap-carry drop stay as the last layer.
- n2h tested (tester): pat "still wrong, looks like it was when I first asked; rotate the hand up"; the carry bug
  happened again with the backpack. Probe: a tap 0.24 s after the last window closed: the game did NOT open the
  window at the release (the only such press of the session); the bag waited 3 s (`late`), then our injected interact
  (T8) found the body's carry hold started (`HoldStale` true in that tick, `NStaleHold` 1) and the game carried it at
  once (kind 7 the next tick). The carry came from OUR injected press.
- n2i: (1) a body never gets an injected interact (T1 `bt1` and the retry `bwr`): without a window by then the touch /
  bag waits as requested (TouchState 3, `NBodyNoInject`): the player's next tap opens the window natively, or T2 brings
  it back after 1 s. Stashes keep the injection. (2) pat: scan n2e vs n2g: the fingers rose 12 deg but the wrist bend
  stayed 30 deg (the palm tilt turned the hand about the forearm, not up). Now n2e's palm plus a local wrist bend
  `PAT_WRIST_UP` 35 deg about the hand's own side axis (fingers toward the back of the hand), weighted with the turn
  (`wv`); right hand's axis mirrored through `C_hand`. Scan: fingers +79/+80 deg (component) vs n2e +46, both hands
  alike; the turn out stays one way (largest hand step 31-33 deg, as n2e; bending the target instead gave 46 deg steps).

## 2026-10-14 — after checkpoint-131: Hide items, armed pickup return
- Tester: "Hide items" works but the item vanishes at the F tap, before the hand gets there; it should stay, then be
  in the hand at once when the reach is done (no animating into the hand). And armed: on the way back to the weapon
  after the grab the hand "goes a little too far right and then recorrects; the stash return looks good, copy it".
- n2j: (1) the copy always waits where the item lay (`PendingCopy` true); `HideItem` makes the pull into the hand
  0.001 s instead of 0.12 s (step 5), so at the grab frame the item is in the hand at once. (2) armed pickups play
  `AS_ImmLoot_GrabPt` (pistol, MainHandEquipmentType 1) / `AS_ImmLoot_GrabAr` (else), `ArmedGrab`:
  `make_grab_seq.py` PART=grabfam `build_grab_family`: `AS_ImmLoot_Grab` unchanged to the pocket frame 26, then the
  touch's return on the family stance (path from the pocket to TOUCH_END_OFF off the stance grip through TOUCH_EXIT,
  arm solved, elbow from the pocket's toward the stance's, hand turn / shoulder / roll / fingers eased, ends frame 38),
  IK on at 1.067 s over 0.35 s, left_hand_curve 0 / 1 / 1 at 1.1 / 0 at 1.3. Scan: the hand comes in from the left and
  below (frame 30: 24 cm left, 16 cm below the stance grip; frame 38: (1, -5, -4)), never right of the grip.
- n2j MCM: "Hide items in the hand" renamed "Disable item fly animation" (tester's name; hover: the item stays where it
  lies until the hand reaches it, then is in the hand at once). Tester: "do not keep the old toggle": mod id
  "Immersive Looting  " (two trailing spaces; the one-space id's entries stay in Noah's save, unlisted; settings back
  to their defaults once).
