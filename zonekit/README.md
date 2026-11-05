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
- Release cleanup (tester: "remove the leftovers and we'll test again"): the strafe experiments' nodes (builds 47-55,
  unwired since v1.1.1) are no longer emitted (`STRAFE_EXPERIMENTS` False; 3165 -> 3040 nodes), 104 unused actor
  variables and 3 MCM ones removed (`BlueprintEditorLibrary.remove_unused_variables`; setup_assets / probe lists pruned),
  deleted: `AS_ImmLoot_Twist` (strafe), `AS_ImmLoot_GrabBH` (18 MB, unreferenced since the additive tables), and
  `AS_ImmLoot_Grab` (the family grabs' template; the editor would not delete it while it held it from this session's
  builds, deleted from disk with the editor closed). Build intermediates now: `make_grab_seq.py` `load_tmpl` falls back
  to `GrabAr` / `GrabBHAdd`, `PART=dropint` deletes the intermediates after a full rebuild. NewContent 7.0 -> 5.4 MB.

## 2026-10-15 — next release (Nexus feedback on 1.3.0)
- Reports: wyruzzah1987 (screenshot: one-hand body touch "like hailing", the hand up-left, not toward the body; the
  backpack "laggy / choppy a few seconds"; the pat "like healing / blocking"), Rodom87 (upright bottles clip through
  the hand; lying ones look right), Sevowin (the delay opening a stash), bulaike0725 (Instant Intel no longer opens
  the PDA for a picked-up note, except while sprinting). Tester: the touch problem is the AIM ("the hand isn't pointing
  to the body"), not the palm; stashes the same; pat: keep, but cancel it when the window closes mid-pat (it played on
  in full, then the weapon); bag: smooth on his PC (probe: 53-62 ticks / 2 s with the bag, no drop).
- Instant Intel (subagent read of its paks): overrides `W_SystemNotificationItem`; each tick while a toast shows, if
  its icon is the Note icon and `AnimInstancePlayer.StateData.bInCombat` is false, it calls `PC.StartUsePDA(2)` ONCE
  (DoOnce, no retry) and hides the toast. During our reach the native call is refused (hands busy), so the one shot is
  lost; sprinting = no reach = it works. Note / PDA items = ItemPrototypes `Type = EItemType::Info` with meshes
  `SM_dev_pda`, `SM_que_pda_*`, `SM_cns_notes_*`, `SM_que_notepad_*` (+ `SM_que_folders_*`).
- n3a: (1) no press switches the target's open interaction off any more (stashes open at the release, as bodies; the
  hand / bag plays alongside); (2) skip cond "note" (bit 512; "use" now 1024, IsLeftHandBusy 2048): `ItemMesh` name
  contains `_pda` / `_notes_` / `_notepad_` / `_folders_` = vanilla pickup; (3) an upright tall item (local Z the
  longest box extent, 1.3x, within ~53 deg of vertical) turns during the pull to lie across the view (`MakeRotFromZX`:
  Z = the camera's flat right, X = toward the camera); others keep how they lay (RLerp alpha linked again);
  (4) the window gone while the pats still play (`OpenAt` >= `TouchPressAt`, position < seg + 1.15): the pat montage
  restarts at its way out (seg + 1.233, rate 0.78) = hands out of view, then the equip (`NPatCancel`); (5) probe T11:
  while a touch is held, the hand's elevation / azimuth from the eye (view axes) vs `ItemElev` / `ItemAzim`, the view
  pitch and `jnt_camera`'s pitch / roll (`RigPitch`), to find why the armed touch missed the body.
- n3b (tester: "for PDAs and notes I still want our reach to play and then the note should open after our animation
  is done"): the "note" skip removed; a note / PDA pickup sets `NoteItem` (+ `NoteAt`); T12: once our montage is over
  (>= 0.3 s after the pickup), if `/InstantIntel/ModActor` is in the asset registry (`K2_GetAssetByObjectPath`,
  `IEFound` probe), `AnimInstancePlayer.StateData.bInCombat` is false and `PC.IsUsingPDA` false: `PC.StartUsePDA(Notes)`
  (`NNotePDA`); given up after 6 s. Without Instant Intel nothing opens (vanilla).
- n3b tested (tester): PDA works (reach, then the PDA on notes); pat cancel works. Upright bottles "don't work, tested
  with water, didn't seem to change at all; it needs to look like the hand is actually holding the bottle (like the use
  animation grab)". Cause: n3a set the copy's turn only with empty hands (an armed pickup never set its rotation) and
  only for items whose local Z was the long axis. (Builds 28-31 tried pickups in the game's use pose: abandoned, "forget
  it"; the game's own hand item mesh exists only during a real use.)
- n3c: any ELONGATED item (longest box extent > 1.3x the middle one) turns during the pull so its long axis lies along
  the hand's grip axis (index_01 -> pinky_01 knuckles, sign nearer the long axis; `RotatorFromAxisAndAngle` about long x
  grip, `ComposeRotators` after how it lay): the shortest turn into the fingers; others keep how they lay; the pull sets
  the copy's rotation with a weapon too (`K2_SetActorRotation` each tick before the copy is parented).
- n3c tested (tester): bottles turn and "look pretty good", sometimes not fully in the palm (a little left / right by
  angle); stashes fixed; body touch "can still go too high when looking down at a body not fully on the ground".
  Probe (17 touches): rig pitch = view pitch every time (the armed arm rig follows the view exactly); the hand went
  where aimed (hand elev / az within ~5-10 deg of the bin); the aim = the pelvis was +9..+13 deg ABOVE the crosshair
  in those cases (bins 21 / 22), so the hand rose toward it.
- n3d: one-hand body touch aims at `LookPoint` (the crosshair's hit on the body at the press); the pat (BodyMode 1)
  keeps the pelvis. Armed pickup: the copy's centre (not its pivot) goes to the hand bone during the pull, parented
  KeepWorld (was SnapToTarget = pivot on the bone).
- n3d (tester: "make the fix apply to the both hands pat too"): every body touch, pat included, aims at `LookPoint`
  (also mutants without a pelvis bone; the pelvis branch is gone).
- n3e (tester: "we shouldn't touch mutants? that should be vanilla, no?"; the game has its own knife animation for
  mutant looting): a body counts for us only if `Obj.IsHuman`; mutant bodies stay vanilla (touch, pat, backpack).
- n3e tested (tester): body hand "could still go lower on the screen across the board"; bottles look good, but "a beer
  bottle didn't seem to rotate, came into the hand standing up, clipping through the top of the hand". `SM_cns_beer_c`
  box 7.4 x 7.6 x 27.8 (elongated like water's 8.2 x 8.0 x 27.8), so the turn ran; likely the grip axis itself was
  near vertical at that grab (the shortest turn then keeps a standing bottle standing).
- n3f: a body touch with Looting bodies = Hand aims 15 deg (one row) below the crosshair point; probe during the pull:
  `PullElong`, `PullLongZ` / `PullGripZ` (world Z of the item's long axis / the grip axis), `PullTurn` (deg).
- n3f: the 15 deg lower aim for every body touch, the pat too (tester: "do it for both hands too").
- n3f tested (tester): body touch "looks good" (Hand and pat 15 deg lower). Beer bottles and energy drinks "still aren't
  rotating; they should rotate to the side every single time". Probe (3 armed pickups): the grip axis at the grab
  pointed 25-75 deg down (`PullGripZ` -0.42..-0.96), so lining the bottle up with it kept it steep.
- n3g: the target axis is the view's sideways axis, flat (camera right without its Z), sign nearer the item's long
  axis: every elongated item ends lying sideways across the view.
- n3g tested (tester): "beer is still broken, it stands straight up". Probe: `PullElong` true, but the long axis's Z
  (-0.12..+0.45) changed WITHIN one pull: the pull read `ItemXf` / `ItemMesh` live, and the tracking step (2) rewrites
  them every tick with the item now under the crosshair (after the pickup: the next bottle of the group, or nothing
  related), so the copy turned toward garbage. This bug predates n3a (every pull since build 26 read them live).
- n3h: `FlyXf` / `FlyMesh` frozen when the copy is spawned; the pull's bounds, centre, how-it-lay and elongation read
  those.
- n3h tested (tester): "niceeee". n3i (tester: "make all items move slightly up in the palm so it overlaps the fingers
  a bit"): the held point (palm with empty hands, `jnt_l_weapon` with a weapon) 2 cm on toward the fingers along the
  wrist -> middle knuckle line.
- n3i tested (tester): "grabbing items looks perfect". n3j (tester: "for both hands looting a body move them a bit more
  to the left, they should be centered"): the pat's two goals centred on the target (left -13 cm, right +13 cm in
  component Y; the left hand was on the target and the right 26 cm to its right). Pat table rebuilt (patscan: largest
  step 44 deg, bh bin 20 (up-left) right forearm on the way back; others <= 32).
- n3k (tester: stashes too, "yes"): every touch bin 15 deg below the target (bodies and stashes).

## 2026-10-17 — after v1.3.1: standing empty-hands pickup
- Tester (1.3.1, standing, empty hands): "reach too low". Scan of the 1.3.0 table (FK, base pose): looking steeply
  down the hand ended far off (elev -80: hand point at az -159), elsewhere ~as 1.2.0. Cause: follow_pitch keyed only
  the shoulder's ROTATION but solved the arm as if the joint swung about jnt_spine_03. Rebuilt with the real joint:
  FK matched 1.2.0 within 1-2 deg, but in game "janky: the arm stretches (EMPERORTECH's sleeve again), the item too
  high in the palm (a finger in front of it), the hand way off to the side looking down". The standing look turns the
  spine with the view but counter-turns the arms: a turned shoulder in a local-space FullBody additive lands
  unpredictably; the 1.2.0 table only worked through measured aim corrections. Tester: "proper fix".
- v1.3.2 a: standing = the bag's pitch fix (FullBody, frame = view pitch, `PickFix`) + `AS_ImmLoot_GrabBHView` in the
  LeftHand slot (`make_grab_seq.py` PART=bhview, `build_bh_view_table`): built in the view frame on fp_bh_idle_stand,
  25 segments (elevation -45..+15 x azimuth -30..+30 of the item seen from the eye, view axes), the hand's item
  point on the eye -> item line at 0.95 of the arm length from the arm root (FK error 0.00 cm), the vanilla grab's
  fingers, IK off at each segment start. Crouched unchanged (`GrabBHAddCrouch`). The old standing node (`mpb`,
  `AS_ImmLoot_GrabBHAdd`) is unwired (dead; delete at the release cleanup).
- v1.3.2 a, first paste: the LeftHand pickup node's Asset came in EMPTY (the table was made headless with the editor closed; the reopened editor had not registered it when the paste ran): no reach, the copy flew to the resting hand. Re-paste after the editor loaded the asset.
- v1.3.2 b (tester: "do all the fixes we can now", after Nexus reports): (1) keunou96 "door animations distorted when
  holstered": an empty-hands door touch while standing also plays the pitch fix (`PickFix`) before its LeftHand asset;
  (2) SavageAdy "disable fly animation, it's still there" (wanted no item): MCM "Hide items in the hand" (`HideCopy`,
  default off) = no copy (`PendingCopy` false); (3) WieSlav1280 "cursor slows down in the backpack / PDA": menu gate
  at the tick start: PDA open (`PC.IsUsingPDA`) or the player's own inventory (`InvOpen`, `LootKind` 0) with nothing
  of ours under way (touch state, reach, use, bag, pat, pitch fix, door, note, pending reach, copy) -> only the
  loot-window steps run. Not reproduced / not addressed: freshtendrils94 (GPU driver crash, RX 9070, no details),
  SavageAdy "hands like a washing machine after sprinting" (needs a repro), keunou96 light-source interactions (a
  feature).
- v1.3.2 b tested (tester): "hide items in hands as an option? we don't need that"; standing empty hands "still a bit
  of stretching in the arm, particularly looking down, and the hand is too much in the middle of the screen";
  crouched empty hands "it still doesn't fully go into the hand: the fingers in front of the item instead of it
  looking clasped".
- v1.3.2 c: "Hide items in the hand" removed (MCM and actor; `HideCopy` vars left unused); the view table's hand line
  10 deg down and 6 deg left of the item (`BHVIEW_OFF`), reach 0.88 of the arm (was 0.95); empty hands: the copy's
  centre off the palm point by half its thinnest box size + 0.5 cm along the palm normal (wrist -> middle knuckle x
  pinky -> index knuckle, the sign away from the camera).
- v1.3.2 c tested (tester): standing empty-hands grabs "look good"; crouched "still look bad, and now after the item
  is in the hand it pops even higher above the hand". Scan (palmsign): the thumb sits 4.8-4.9 cm on the -n side
  (n = wrist -> middle knuckle x pinky -> index knuckle) in the vanilla grab, the view table and the crouch table;
  the camera-facing sign test flipped as the hand came back up (the item jumped through the hand).
- v1.3.2 d: the palm side is fixed at -n.
- v1.3.2 d, doors (tester: "make the door animation more of a continuous push / wave; I can see the hand stop at the
  end before it goes down; it shouldn't stop"): every door asset's hand path is one cubic Hermite through timed keys
  (`wave_path`, Catmull-Rom tangents, zero only at the ends): push = rest -> near the door -> the door -> a
  follow-through 3 cm on / 2 cm down (`DOOR_FOLLOW`) -> rest, pull = rest -> handle -> drawn back -> rest (the handle
  hold dropped); with a weapon through the arcs' midpoints (the arc under the weapon kept). The Blueprint no longer
  holds a door touch at its touch frame (`bhold` skips `DoorTouch`): the asset plays out in one go. PART=doorwave.
- v1.3.2 d tested (tester): crouched empty hands "still not truly in the palm, I can see the full hand in front of it,
  the fingers too"; the backpack on a stash "way up on the left of the screen" (screenshot: standing, looking down at
  a backpack stash on a seat, no window).
- v1.3.2 e: crouched empty-hands pickups = `AS_ImmLoot_GrabBHViewCrouch` (PART=bhviewcrouch: the view-frame table on
  fp_bh_idle_crouch as a FullBody local-space additive; the crouched look turns the arms with the view, so no pitch
  fix), segment from the view-relative bins as standing; the body-frame crouch table (`mpbc`) unwired.
- v1.3.2 e, first paste: "Exec output pin cannot have more than one connection": the standing chain's link to the reach steps looked up the last "count (probe)" node, now the crouched one (linked twice). Fixed with explicit lookups; check_paste.py now reports exec outputs with more than one link.
- v1.3.2 e tested (tester): crouched pickups "the hand is too high off the screen"; the backpack the same. The probe
  logged nothing (it had latched onto the main-menu world's actor: fixed, it now prefers an actor outside
  MainMenuMap and drops one whose tick count stops).
- v1.3.2 f: crouched, the arms stay in the body frame (build 48: a crouched segment lands at index - view pitch - 37),
  so the view-frame crouch table aimed at the view elevation sent the hand up and off the screen when looking down.
  `AS_ImmLoot_GrabBHViewCrouch` rebuilt on the body-frame elevations (-80..+25, 8 rows x the 5 touch azimuths = 40
  segments, the same reach / hand-line offset as standing); the Blueprint picks its segment from the item's mesh-frame
  elevation / azimuth from the camera bone (`_el` / `_az`, as the old crouch table). The bag stays a probe run.
- v1.3.2 g (tester: "no logger-only runs, include a fix"), the backpack on a stash with empty hands: the pose table
  (`AS_ImmLoot_BagPitchFix`) is a FullBody dynamic montage; any other FullBodyGroup montage stops it and
  `PitchFixMont` stays a valid object, so the per-tick frame set (gated on IsValid only) went to a stopped montage and
  the arms stayed level (looking down = the bag high up on the left). Heal (`_sqpf` then_7): bag out, `BagWeapon`
  false, the pose table not `Montage_IsActive`? played again paused from the view's frame (`NPitchHeal`);
  `PitchFixAlive` now = valid AND active. Same cook as v1.3.2 f (crouched body-frame table).
- v1.3.2 f/g tested (tester): crouched "still doesn't really look like it is in the hand" (screenshot: the can lies
  right of and below the fingers; standing looks better); backpack "no change, goes top left, the right arm clips into
  the view". Probe (stash, standing, pitch -49): the pose table WAS active all along at the frame of the view pitch
  (PitchFixAlive true, PitchFixPos 1.64, NPitchHeal 0): g's guess was wrong. The window opens on the bag's first tick
  (In hidden behind it, the In reaches the Idle while the window is open), so the tester sees only the close (Idle ->
  Out -> held at 0.6 s -> gone 0.67 s after the close). Bag assets / pitch table unchanged since checkpoint-bag.
- v1.3.2 h: crouched, the held copy's build 48 "+5 cm to the camera's right" (a correction for the old crouch table)
  is 0. Bag probe (no behaviour change): the bag, both hands and jnt_camera in view axes (`BagV*`, `RHandV*`,
  `LHandV*`, `CamBoneV*`), the pose table's real montage position (`PitchFixReal`), which bag montage is active.
- v1.3.2 i (REVERTED, tester: "don't change the functionality of the animation"; was: "try and fix the backpack; it works in the release, so it is something we are doing here"): the
  generator diff to 1.3.1 leaves the bag path itself unchanged (only the shared pitch-fix upkeep: `PickFix` added to
  the frame-set OR and the stop's NOT, and the heal). Screenshot (v1.3.2 d): the bag huge at the top left, its strap
  across the view, no window = the In's first part (the bag off the back over the left shoulder). Since 1.3.1 the
  stash window opens on the bag's first tick; the bag showed from its 3rd tick under the window's fade in / out. Now
  `_bsh` also needs `InvOpen` false: hidden while the loot window is open, shown at the close (Idle) before the Out.
- Full paste diff 1.3.1 -> now (node class / function / comment / pin defaults): every 1.3.1 node is still there
  unchanged except build h's crouched +5 cm select; the 208 added nodes are the pickup / door pitch fix, the crouched
  table, the menu gate, the heal and probes. No bag node, bag asset, montage or pitch table changed.
- Control test (tester: "let's try the control test"): the v1.3.1 release paks installed as the test pak (dev build backed up in the session scratchpad), logger off.
- v1.3.2 h cooked and installed (dev build back in place of the 1.3.1 control; control result: 1.3.1 shows the same backpack fault at the crane-cabin stash). Logger on.
- v1.3.2 h tested (tester): crouched pickups "ok but sometimes too low", "the hand needs to be rotated clockwise so the
  bottle items look actually held"; backpack still wrong standing ("the right arm clips into the backpack as if it is
  too high"), "looks better when crouching". Probe (bag in view axes fwd / right / up, PCM camera = jnt_camera):
  standing -59 Idle (45, -28, +17); standing -32 In end (29, -27, +9); crouched -25 Idle (41, -16, -26) = the game's
  own (39, -17, -26). The pose table turned the arms ~87% with the view between -32 and -59: the standing error is a
  constant ~50 deg (the bag's arm keys on the upright bare-hands stance), not the pitch fix.
- v1.3.2 j: standing empty-hands bag = `AS_ImmLoot_BagPitchFixStand` (make_bag_seq PART=pitchstand: the pose table
  with the arms turned down a further `BAG_STAND_LOWER` 55 deg, the spine's own look turn, about the shoulders; extra
  last frame 91 = the uncorrected frame 0 as the additive's reference), chosen at the bag start when the camera is
  130 cm+ above the feet; crouched keeps `AS_ImmLoot_BagPitchFix`. g's heal removed. Crouched pickup table: hand line
  3 deg under the item (was 10), hand rolled 30 deg clockwise about the reach (`BHVIEW_OFF_CROUCH`, `BHVIEW_ROLL_CROUCH`).
- v1.3.2 j bug (found building k, never cooked into a test the tester ran... j was pasted but not cooked): the lowering
  quaternion in `build_pitch_fix` was named `lq`, the same name as the per-bone local rotation in the frame loop, so
  from frame 1 on the "lowering" was the last arm bone's local rotation. Renamed (`lowq`).
- v1.3.2 k (tester: "can you give me a dev debug menu in MCM to tune the values myself?"): MCM mod id
  "Immersive Looting DEV" (its own menu entry; dropped before a release) with three dropdowns on BP_ImmLootMCM ->
  actor: "Backpack arm lowering (standing)" 0..90 in 5s (`DevBagLower`, default 55): `AS_ImmLoot_BagPitchFixStand` =
  19 blocks x 91 frames + the reference (frame = block x 91 + pitch; `StandFixMont` marks it for the frame step);
  "Crouched pickup hand roll" 0/15/30/45/60 (`DevCrouchRoll`, default 30): `AS_ImmLoot_GrabBHViewCrouch` = 5 roll
  blocks x 40 segments; "Crouched pickup reach height" -15..+15 in 5s (`DevCrouchElev`, default 0): a bias on the
  item's elevation before the 15 deg row binning. Table checks: block k's shoulder 5k deg from block 0, ref = block 0
  frame 0.
- v1.3.2 k cooked and installed (actor + MCM pasted; MCM compile notes = the usual interface-to-self infos).
- v1.3.2 k tested (tester): "backpack was too high no matter what setting"; "give me full control over every axis
  with sliders"; crouched "the rotation was only in one axis"; "the fingers rotate backwards when picking up an item
  crouched, they look broken". Probe: the k lowering was applied (PitchFixReal = block x 91 + pitch) and moved the
  bag UP and BEHIND the camera (block 11: Idle at (-44, -27, +36); block 18: (-12, -27, +46)): the spine's look turn
  used as "down" turns the arms up about the shoulders. Slot groups (all player montages): DefaultGroup = DefaultSlot,
  LeftHand, RightHand, CameraSlot, WeaponSlot, DeathSlot; ActionGroup = MainActionSlot, SecondaryActionSlot, Gadget*;
  UpperGroup = UpperBody; FullBodyGroup = FullBody; PreActionGroup = PreActionFullbodySlot; CutsceneGroup = CutsceneSlot.
  MCM float / int / vector / rotator settings are spin boxes (WBP_MCM_SettingFloat / Rotator: SpinBox).
- v1.3.2 l: the k tables reverted (standing bag = the plain pose table; crouched table one block). Live DEV offsets
  (`make_dev_offsets.py`): local-space additive grids `AS_ImmLoot_DevArmRot` (both shoulders, spine frame, 25^3 at 5
  deg), `DevArmPos` (21^3 at 1.5 cm), `DevHandRot` (left hand, own axes, 25^3 at 7.5 deg), played through montage
  assets `AM_ImmLoot_Dev*` in FullBody (Montage_Play without stopping others, after the pose table's dynamic montage),
  paused, the frame from the MCM values every tick (fastest axis continuous). MCM DEV: rotator / vector / float spin
  boxes for the standing and crouched bag arms, the crouched hand, the crouched reach height. Crouched fingers: the
  vanilla grab's change from its own first frame on the game's fingers (was its absolute pose as an additive).
- v1.3.2 m (tester: "give me bigger ranges, way bigger"): the DEV grids keep their frame counts (the montages keep
  their length) with exponentially spaced values: rotations 0, 2, 4.7, 8.2, 12.9, 19, 27.5, 39, 53, 73, 99, 134, 180
  deg each way (A 6.054235, B 1.330347), positions 0, 0.5, 1.2, 2.3, 3.9, 6.3, 9.8, 14.9, 22.5, 33.6, 50 cm (A
  1.054993, B 1.473937); the Blueprint's index = sign(v) ln(|v| / A + 1) / ln B. The montages were still DefaultSlot
  after the tester's "done" (slot change not saved).
- v1.3.2 m cooked and installed (montage slots FullBody verified, actor + MCM pasted clean).
- v1.3.2 m tested (tester): "the crouch pickup animation doesn't play"; MCM "doesn't have sliders, no labels, axis,
  min-max, defaults"; asked for a ZST-style custom live menu, dev only. Probe: PitchFixAlive false through all four
  bags and the crouched pickups showed nothing: **Montage_Play of a montage asset in FullBody (bStopAllMontages false)
  stopped our paused dynamic FullBody pose table in the same group** (one montage per slot group, whatever the flag):
  the l DEV offsets broke the tables. Tester chose the panel + a post-process pose layer.
- v1.3.2 n (DEV only, `IMMLOOT_DEV=1`): l's montage offsets removed (the `AS/AM_ImmLoot_Dev*` assets are unused now),
  MCM DEV entries removed. New `/ImmersiveLooting/Dev/`: `ABP_ImmLootDevPose` (post-process, parent AnimInstancePlayer;
  Transform (Modify) Bone on both shoulders and the left hand, rotation / translation added in WORLD space, bound to
  ArmRot / ArmPos / HandRot / ArmAlpha / HandAlpha; graph from `gen_abp_devpose.py`, Input / Output pose wired by hand),
  `W_ImmLootDev` (designer paste from `dev_panel.py`: Python cannot edit a widget tree and UWidget has
  DontUseGenericSpawnObject, so no runtime Construct; an AssetExportTask with ObjectExporterT3D on transient widgets
  writes the designer's clipboard format). Actor (`gen_actor_dev.py`): the layer attached once ~2 s in (mesh-swap
  path, never Reinit), F7 panel (17 sliders, `dev_params.py`: bag standing / crouched arm turn + move, crouched hand
  turn, reach height, time scale; labels show range, default, live value), F8 reset, F9 backpack preview (the real
  bag path, held at its Idle). Values turned from view axes to world space each tick. ImmersiveDialogue (its own
  post-process layer) must be off while the dev pak is in.
- v1.3.2 n cooked and installed (panel, pose layer, actor, MCM pasted clean).
- v1.3.2 n tested (tester): "crashed loading into a save" (twice, 15:38 / 15:40). Log: AV reading 0x0 in game code;
  the probe's last line NTicks=121 = the tick our DEV attach ran (NTicks > 120): the mesh swap with
  `ABP_ImmLootDevPose` parented to AnimInstancePlayer crashed at load. ImmersiveDialogue's layer of the same parent is
  a full copy of AnimBP_Player fed the main instance's data; a bare AnimInstancePlayer subclass is not safe.
- v1.3.2 n2: `ABP_ImmLootDevPose` reparented to plain AnimInstance (Campfires installed a plain-AnimInstance layer
  while standing without a crash; its crashes came with native sits). No paste; cooked.
- v1.3.2 n2 tested: still crashed "at the loading screen, before I even get into the save": same address
  (0x7ff604463993, AV 0x0) on the tick NTicks passed 120: the actor ticks during the loading screen; parent class not
  the cause. n3: the layer attaches at the first F7 press (`DevWantAttach`), in play.
- 2026-10-30: game updated to 2.1 (exe 10-30; Zone Kit still the 2026-09 build). The n2 dev pak (crashes at load) parked in the scratchpad (devpak_n2); the v1.3.1 release installed as the test pak for a 2.1 compatibility check; logger off. n3 (attach on F7) generated, not pasted.
- 2026-10-30 (tester): on 2.1 every other mod works, ImmersiveDialogue does not; 1.3.1 shows the known unarmed / crouched grab issues (expected: the 1.3.2 fixes are not in it).
- 2026-10-30: the Zone Kit updated too (ProjectVersion 2.1.0, 15:18-15:39). A second agent (ImmersiveDialogue) works on
  this PC in parallel: harness coordination board added (`harness/tools/coord.ps1`, `docs/coordination.md`, c69d11a).
  Our n3 cook waits behind its cook (Wait-UatFree); its game run goes first.
- n3 cooked and installed (16:10). The unused l / j assets (AS/AM_ImmLoot_Dev*, AS_ImmLoot_BagPitchFixStand) had fallen into the override pak once off the NewPackages list: deleted from the kit and the repo mirror.
- 2026-10-30 (tester: "the mods must be compatible, I am testing both at the same time; the harness should know
  this"): harness rule added (coordination.md: one run tests every agent's build, merged test lists; dev tools may
  not take an exclusive resource another installed mod uses). Player AnimBP order (AnimBP_Player AnimGraph): ... ->
  FullBody -> LayeredBoneBlend -> BlendListByBool -> DeathSlot -> CutsceneSlot -> CacheBlend -> ControlRig -> Root.
- v1.3.2 o: the F7 panel's backend moved off the post-process layer (ImmersiveDialogue owns it) to a paused DYNAMIC
  montage in CutsceneSlot (CutsceneGroup: nothing else plays there outside cutscenes; only after F7 was pressed once):
  `AS_ImmLoot_DevArmRot` (both shoulders, 25^3 exponential grid, while the bag is out with empty hands; standing /
  crouched values by camera height) or `AS_ImmLoot_DevHandRot` (left hand, while an empty-handed crouched pickup plays),
  one at a time (`DevMont`, `DevMontKind`). Arm translation dropped (one table at a time). Panel: 11 sliders.
  `ABP_ImmLootDevPose` no longer cooked or attached.
- Combined run (ImmersiveDialogue agent's merged list, n3 dev pak, no F7; tester): "unarmed looting fixed" (standing
  view-frame pickup confirmed on 2.1); "crouch unarmed the fingers look like spaghetti"; ImmersiveDialogue fixed
  (its agent cuts that release).
- v1.3.2 p: crouched table fingers = the vanilla grab's curl in each finger joint's own frame
  (rest * g0^-1 * gf; l had it in the parent's frame). Table rebuilt (PART=bhviewcrouch), no paste.
- o / p cooked and installed (actor pasted clean after an editor crash on the first delete; panel 11 sliders).
- o / p tested (tester): F7 panel shows, but "my mouse doesn't appear, I have to pause the game" (bShowMouseCursor +
  SetInputMode_GameAndUIEx have no effect in this game); "F9 seems broken completely, we don't need it, I can trigger
  it myself".
- v1.3.2 q: F9 preview and the cursor / input-mode nodes removed; the numpad drives the shown panel: 8 / 2 select the
  row (">> " on its label), 4 / 6 lower / raise (per tick 0.25 x step x speed, speed 1 + held ticks / 20, max 6x),
  5 = the row's default, F8 = all defaults (`DevSel`, `DevHoldTicks`, `DevN8/2/5Prev`). The panel's help line still
  says F9 (widget unchanged).
- q paste: the editor crashed again deleting the old graph (Ctrl+A, Delete). Log: "Ran out of memory allocating 3.7 MiB
  ... paging file is too small", PeakUsedVirtual 117.9 GiB (this PC: 128 GB RAM + 16 GB page file = 143.6 GB commit).
  Deleting the ~3,700-node / 14,000-pin actor graph in one go balloons the editor. Earlier this session the same
  delete at 3,409 nodes went through. Tester: crouched fingers still "going backwards and breaking" with p.
- v1.3.2 r: crouched table leaves the fingers alone (rest pose; no curl added). Not built yet (editor down).
- No more deleting the big graph in the editor: the old actor renamed aside (`BP_ImmLootActor_Old`, no redirector
  was written: its two referencers, MCM provider and subsystem, were not loaded and still point at the original path),
  a fresh `BP_ImmLootActor` made by setup_assets.py (all variables and defaults) at the original path, the tester
  pastes into its empty graph. Backups of the three uassets in the session scratchpad (actor_backup). r crouched table
  built (fingers untouched).
- The tester pasted into `BP_ImmLootActor_Old` (its delete went through this time): the empty fresh asset deleted,
  `_Old` renamed back to `BP_ImmLootActor` (graph 3990 = generated, no compile messages); MCM provider and subsystem
  still point at the path (checked in their exports), recompiled. q / r cooked and installed. Next time: the
  fresh-asset path (no delete in the editor).
- q / r tested (tester): "F7 isn't doing anything when I use it while looting a body" (the loot window takes the keys
  and covers the bag; the bag shows only in its Out). q's F9 "broken" = F9 is the game's quick load.
- v1.3.2 s: backpack preview back on Num 0 (panel shown). Paste via the fresh-asset path (old renamed `_Old`, fresh
  `BP_ImmLootActor` from setup_assets.py).
- s pasted into _Old again (open tab followed the rename): swapped back, DevN0Prev added by setup_assets, compiled clean, cooked and installed.
- s tested (tester, game 2.1): backpack with empty hands "looks totally fixed", WITHOUT the panel ever opened (no DEV
  table played). Our bag path is unchanged since 1.3.1 (control test on 2.0.x showed it broken), so game 2.1 most
  likely changed what the bag's arm keys land on. Crouched pickup still wonky (screenshot: hand from the far left,
  palm down, wrist bent, bottle pinched in the fingertips): to be tuned with the panel.
- Panel time scale: with it lowered "the hand animation does not play, only the item floats" (the item's pull runs
  on undilated time, the hand on dilated). Tester: "just try and fix the animation yourself".
- v1.3.2 t (table only, no paste): crouched hand pitch = 60% of the reach elevation (no bent wrist), no left offset
  (was 6 deg), fingers = the vanilla grab's closed grip (frame 14) at 70% over frames 8-38, never its opening phase
  (the opening from the rifle grip is what bent the crouched fingers back in k / l / p). Cooked and installed.
- t tested (tester): backpack "broken again" (standing looking down and crouched; in s it was "fully working" in every
  stance with the panel never opened); crouched hand "still not quite right" (screenshot: fingers spread open, hand
  palm down left of the bottle). Between s and t only the crouched table changed, but the panel had been opened (time
  scale attempt): with the panel opened, the CutsceneSlot DEV tables play during the bag / crouched pickup, and the
  time-scale run already showed a crouched pickup losing its hand animation then. Reading: a montage in CutsceneSlot
  breaks the arm animation (CutsceneSlot is not a safe host).
- v1.3.2 u: the DEV tools off (`IMMLOOT_DEV=0`; the F7 panel, its tables and keys gone from the actor graph). Paste
  via the fresh-asset swap (old renamed `_Old`; the tester closes the old tab first).
- Tester: when the backpack looked fixed he had a weapon out. So: armed right, empty hands wrong (as always).
  Postures (frame 0, component space): rifle idle spine_03 25.5 deg bent forward and 10 cm forward of the bare-hands
  one, shoulders 20 cm forward / 6 cm lower (crouched 23 deg / 24 cm). The bag's arm keys hang from spine_03.
- v1.3.2 v: `AS_ImmLoot_BagSpine` (make_bag_seq PART=spine: local additive on jnt_spine_03 only, frame 1 standing /
  2 crouched = onto the rifle idle's spine_03) played paused in UpperBody while the bag is out with empty hands
  (`BagSpineMont`, out 0.3 s when the bag is gone). With u (DEV off) in one paste.
- u / v pasted (into _Old again), swapped back, compiled clean, cooked and installed (AS_ImmLoot_BagSpine in the pak).
- v tested (tester): empty hands standing "it makes me crouch and the backpack goes above my head (I can see the
  shadow doing the animation)"; crouched "it makes me stand up and my head exits my body". The spine_03 local
  additive in UpperBody moved the whole body / camera (UpperBody is not a safe additive host for this). Armed: right.
- v1.3.2 w: v removed (`AS_ImmLoot_BagSpine` deleted). Empty-hands bag pose tables instead of the plain pitch fix:
  `AS_ImmLoot_BagPitchFixBH` (standing, frame = pitch) / `...BHCrouch` (crouched, frame 0): make_bag_seq PART=posture:
  hips / spine_01-03 turned in mesh space to the rifle idle's (stand 19 / 3 / 18 / 25.5 deg, crouch 30 / 28 / 39 / 23)
  and the arms turned with spine_03 on top of the pitch fix; extra last frame = no change (reference). Chosen at the
  bag start by camera height. Direct paste (graph ~3,400 nodes).
- w pasted directly (delete went through), compiled clean, cooked and installed (both BH bag tables in the pak).
- w tested (tester): empty hands standing "the backpack is too high, I can't see it, it's off screen"; crouched "in
  your face, basically clipping through"; crouched pickup "regressed since I last saw it: the hand is higher and still
  not holding things, bottles clip through the hand" (t's table).
- v1.3.2 x: t's crouched table reverted (hand pitch = the full reach elevation, 6 deg left offset back, the game's
  crouched fingers: the s / r state). w's posture tables deleted. The empty-hands bag is servoed:
  `AS_ImmLoot_BagServo` (make_bag_seq PART=servo: the pitch fix x the arms turned about the shoulders by L = -60..+60
  deg in 5s, L the fast axis: frame = pitch row x 25 + (L + 60) / 5, so a fractional position blends two L). While the
  bag's Idle plays, each tick L -= 0.15 x sign x (the bag's elevation in view axes + 34 deg; the game's own bag sits
  at -34); one L per stance (`BagLowerS` default -25, `BagLowerC` 0), kept across bags; `BagServoSign` flips if L hits
  an end with the bag still off. Why a servo: the table's math (component space, +X forward: toes ahead of the feet)
  says a positive L / a forward spine lowers a forward-held arm, but in game both k's positive lowering and w's
  forward spine lifted the bag; the cause of the inversion is not found, so the sign is learned in game.
- v1.3.2 x, crouched pickup (tester: "you just reverted to a build that still had issues?"): cause of every crouched
  finger failure found: the game's crouched fingers are the STANDING rest's (build 44: the 1.1.0-1.3.1 crouch table
  took `finger_base` = fp_bh_idle_stand); `GrabBHViewCrouch` used fp_bh_idle_crouch's fingers as its additive
  reference (10-33 deg off per joint), so k / l / p / t's curls landed on the wrong base. Now its finger reference is
  the standing rest and the fingers get the standing table's recipe (vanilla grab fingers frame by frame; checked: frame
  0 = standing rest, grab frame identical to `GrabBHView`). j's 30 deg clockwise hand roll back (`CROUCH_ROLLS`; l had
  set 0 for the DEV hand turn, gone since u). t's 0.6 hand pitch / zero azimuth offset reverted. Table only (no paste).
- x pasted (direct delete went through), cooked and installed (BagServo + the new crouched table in the pak).
- x tested (tester): "the game crashes when loading into a save" (twice, 19:02 / 19:04). Both: AV (0x18, 0x0) with only
  UE4SS.dll frames on top (none of the game's code). UE4SS.log: ImmLootProbe was still enabled in mods.txt (the
  logger "off" since 2.1 was only the probe's own variable list; Vortex's mods.txt kept `ImmLootProbe : 1`), and during
  the load hitch (our actor ticked 11 times in 2 s) its 50 ms LoopAsync queued dozens of ExecuteInGameThread reads that
  ran in one burst on the world actor; the crash followed (the probe's known save-load crash family, 2026-10-11 / 12).
  Probe set to 0 in mods.txt.
- x tested (probe off; tester): backpack "still too high, crouched or standing"; crouched pickup "garbage, make it look
  the same as standing" (screenshots: standing = the arm straight in from the lower left, back of the hand up, the can
  in the palm: "perfect"; crouched = the hand in from the left, turned on its side, the bread pinched in the fingers).
- v1.3.2 y (table only): crouched, the game's look turns the spine with the view and counter-turns the arms (they stay in
  the body frame, f), so the LOCAL-space table's shoulder delta was turned by the spine's pitch (reach and hand rotated
  with the view: the sideways hand). `GrabBHViewCrouch` is now a MESH-space rotation additive (as the pitch fix; all
  110 crouch-rest tracks keyed so the cook's mesh space is the crouch body's): the arm's mesh rotations go from the rest
  to the solved ones whatever the spine does. Offsets and roll as standing (-10 / -6 deg, no roll). Bag: no change;
  ImmLootProbe back on, hardened (no reads for 20 s after the actor is found, a queued callback < 40 ms after the last
  is dropped) and reading BagServo / BagLowerS / BagLowerC / BagServoSign, to see whether the servo runs and where L goes.
- y cooked and installed.
- y tested (probe on, loaded fine; tester): backpack "still goes above the screen: I see nothing until I close it, then
  the arms come down from above"; crouched pickup "still wrong" (screenshot: the arm in from the far left, level, the
  hand round the bottle from the side). Probe (one body loot, BodyMode 2, camera below 130 cm, window open 1.1 s):
  the servo never ran (the In never reached the Idle: BagIdleOn never true; the window closed during the In). During
  the In both hands went UP and BACK: left hand (-25, -24, -12) cm in view axes (at the shoulder), right hand (-16, -8,
  +7), while AS_ImmLoot_BagIn has the left hand at (47, -18, -8) from the camera from 0.3 s on; then the Out started
  from there ("arms come down from above"). The pose table was at frame 12 (row 0, L 0 = no change in the data).
  Crouched pickups: resting left hand (32, -27.6, -20.8) in view at every pitch -32..-51 = fp_bh_idle_lowcrouch's
  (30.0, -27.0, -21.4) from the camera: the tester's crouch is the LOW crouch and its look turns the arms rigidly with
  the view. The reach (segment 12: body elevation -50) sent the hand 20 cm forward and 17 cm UP.
- Reading: every pose table referenced on an extra LAST frame (j, k, w, x) put the arms up and back in game (k: "up and
  behind the camera", w "too high off screen", x: hands at the shoulders on a no-change frame); the ones referenced on
  frame 0 (the plain pitch fix, the pickup tables) behave. The table's own data was checked (the last frame = the rest).
- v1.3.2 z: (1) `AS_ImmLoot_BagServo` with the reference on frame 0, the data from frame 1 (Blueprint frame + 1); the
  servo also runs from 0.4 s into the In (its hand is at the Idle's place from 0.3 s); BagServoSign -1 (the math's sign:
  a positive L lowers a forward arm), standing L starts at +25. (2) Crouched pickup = the standing recipe in the VIEW
  frame on fp_bh_idle_lowcrouch (25 segments, view bins `_vel` / `_vaz`, the low-crouch fingers), local-space
  additive in FullBody (y's mesh space and x's standing fingers dropped).
- z pasted, cooked and installed (probe on).

- 2026-10-31: Noah plays build z for fun, no test run: ImmLootProbe set to 0 in the game's ue4ss mods.txt (set back to 1 before the next logged run).
- Open Nexus reports (from 2026-10-30, not yet worked on): GutsFromBerserk: the Limited Edition NON STOP turns into the
  normal blue can in the hand (the copy takes the item's mesh but not its materials); GutsFromBerserk / wrigi /
  SavageAdy: knife equipped, the arms distort and the hands spin, "washing machine" hands after sprinting; Ls5555: the
  bag should be the player's own (pre-order) backpack; SavageAdy: "disable item fly" still flies (b's "Hide items in
  the hand" answered it and was removed at the tester's call); wrigi: doors feel odd (has the toggle, nothing to fix).
- 2026-11-03 Nexus (thetrueShubNiggurathFFS): spoiled canned food turns into regular canned food at the pickup, Spark
  armor into Duty armor (screenshot). Tester: the unarmed backpack still too high; "fix every single issue in one go",
  with an adversarial review by a fresh agent.
- v1.3.2 aa: (1) the bag simulator (`zonekit/research/bag/sim`, the bh WeaponLayer order from the strafe research:
  slots RightHand / LeftHand (local) -> look additive (mesh space) -> CopyBone jnt_camera := VB jnt_camera -> FullBody)
  reproduces the h probe (standing -32: sim (29, -27, 11) / probe (29, -27, 9); crouched -25: (40, -16, -25) / (41,
  -16, -26)). Why every table missed: the bag sequences key the shoulders from a body leaning far forward (shoulders
  4.5 cm ahead of the camera, 29 cm below), the slots put those locals on the upright bare-hands chest (shoulders 28 cm
  behind the camera), and the standing look additive turns the arms and moves the forearm's local translation (31 cm
  at -60: the "stretched sleeve"). Standing at -45 the bag sat 32 cm above the view centre. `AS_ImmLoot_BagFix`
  (58 frames, `gen_bagfix.py`): every arm bone to the anim's orientation relative to the camera, arm translations back,
  shoulders moved to the anim's (21 cm standing, 0.5 cm low crouch): sim = the vanilla framing (39, -17, -26) at every
  pitch; one correction for every bag time (Out to frame 16 within 4.5 cm; the table stays full while the Out's slot
  blends out, both hands leave downward). The servo and its update removed. (2) The copy takes the item's materials
  (`ItemMats` from `MeshComponent.GetMaterials` at tracking, `SetMaterial` per slot on the copy): MeshPrototypes.cfg
  variants share a mesh (`Energetic_Limited` = SM_cns_energy_drink + MI_egg_energy_drink_limited, scale 1.2;
  `SpoiledCannedFood` = MI_cns_canned_food_02). (3) Knife / grenade / bolt in hand (MainHandEquipmentType 4-6): skip
  "handitem" = vanilla (Nexus: arms distort, hands spin with the knife). (4) The player's own backpack: while his own
  inventory is open, the pawn's skeletal meshes are searched for `SK_bpa_pla*` (`BagMeshPC`), used for our bag (a
  non-default one wins; materials stay the mesh's own first-person ones).
- v1.3.2 aa adversarial review (fresh agent, 3 rounds): no blockers. Applied: the stance block latched at the bag
  start (`BagBlock`), then kept with a 10 cm hysteresis (switches 10 cm past 145 / 115 cm); the backpack scan only in
  the first 1.5 s of each opening; `PitchFixPos` logs the position really set. Accepted risks (test list): the
  shoulders moved 21 cm (standing) / 28 cm (crouch) could stretch skin near the view looking straight down; the
  standing correction rests on probe points within 2 and 8.6 cm; the own-backpack scan is unverified (no pre-order
  mesh in the kit); knife / grenade / bolt now vanilla for touches, pat, bag and doors too.

- 2026-11-04 aa pasted by Noah, compiled and saved; `AS_ImmLoot_BagServo` deleted (kit + mirror, no referencers);
  mirrored, cooked (BagFix in the cook) and installed. Probe on. Waiting on Noah's test run.
- aa tested (tester): backpack with empty hands "the closest we've ever been": right most of the time; at a pile of
  bodies "sometimes too high, but not as high as before, I can still see the bottom of the backpack"; bodies in the
  pile flicker in and out of view near it (physics stays; "only this build"); knife / bolt "now don't have any
  animation, they should: the left hand is totally free, the same as unarmed, just for the left hand"; doors good with
  empty hands and a pistol, rifle "looks the same as before, as if nothing changed"; everything else good; no
  pre-order backpack to test. Probe (10 bags): standing / low crouch blocks 0 / 38 put the bag at (39.0, -17.5, -26.0)
  = the simulator exactly; bags 3, 4, 7 ran block 19 (crouch) while standing: bag (31..36, -20..-23, +21..+24) = the
  simulator's standing pose with the crouch correction (30.5, -23.2, 25.2). The stance test (camera height in the mesh
  frame, 145 / 115 cm + 10 cm hysteresis) read a crouch on the pile (the legs' IK lowers the body on uneven ground).
  Knife / bolt (simulator, `research/bag/sim/dump_hand.py`, `handsim*.py`): their layer = fp_ar_idle_stand + the
  item's mesh-space idle additive (AS_fp_knife_idle_add / AS_fp_bolt_idle_add) + the rifle look; the free left hand
  rests at (40, -24, -18..-20) cm from the eye in view axes at every pitch, standing / crouched / low crouched (probe
  (40.2, -23.7, -21.0)); knife and bolt within 1.3 cm. Rifle vs pistol doors (released vs current paths): both moved
  by the same <= 7 cm in d; the rifle stance's door point is 5 cm further out, at the arm's full reach.
- v1.3.2 ab: (1) the stance from the game's anim state (`StateData.bLowCrouching` / `bCrouching` -> `StanceBlk` 38 /
  19 / 0, every tick), the bag table's block = StanceBlk (camera-height test and hysteresis gone). (2) Knife (4) and
  bolt (6) back in, one "kn" family built on the knife layer's pose (make_grab_seq PART=knife; the pose baked in
  `AS_ImmLoot_KnStance` for the build, deleted after): pickups = `AS_ImmLoot_GrabKnView` (the empty-hands view-frame
  recipe, FullBody local-space additive, 25 segments from the view bins, the item into the palm), body / stash
  touches `AS_ImmLoot_TouchKn0..24`, doors `AS_ImmLoot_DoorPush/PullKn`; no HandIK-on notify in any kn asset (no grip:
  IK on would pull the free hand to the held item's socket); the both-hands pat with the pistol family (the pat
  montage's slot tracks are hand-set, its table stays 75 segments). Grenade (5) stays vanilla. (3) Rifle doors aim at
  the pistol's door point from the eye (`DOOR_POINT_FROM`): the arm no longer locks straight at the door, the
  follow-through shows. (4) Probe: BagCamZ, StanceBlk, BagBlock, EquipType, GrabPos. Flicker: nothing in the graph
  touches other actors' visibility (every SetVisibility / SetHiddenInGame / SetMaterial target checked: our copy,
  our bag, the held weapon, the hold-to-use item); not reproduced.
- v1.3.2 ab adversarial review round 1 (fresh agent): no wiring / pin defect; applied: AimStand and the plain pitch
  fix's crouch test from StanceBlk too (the pile fooled them like the bag); no "hand back on the grip" montage
  (`bgr`, `br4b`: it switches the left-hand IK on) with the knife / bolt; kn touches / doors start and end on the free
  hand (no TOUCH_END_OFF: no IK takes it home); the armed branches (pickup, doors, pat) also take kn_q (the bolt's
  HasItemInMainHand unverified); the kn pat = the rifle family (the knife layer is the rifle body). Kn assets rebuilt.
- ab review round 2 (fresh agent): the remaining HasItemInMainHand-only tests made consistent for the knife / bolt
  (in case the bolt reports false): the empty-hands door pitch fix (`_bdbh`) and the bag's armed test (`_bbw`) take
  kn_q, no bare-hands hands-up after a kn bag (`_bnat`), no equip replay after a kn bag / pat (`_beq2`, `_peq`: the
  remembered equip may be another weapon's, with both hands' IK on; the item is shown again by `_bwd`). Probe
  `HasItemMH`. Round 3 started.
- ab review round 3 (fresh agent): paste integrity clean (6 known dead execs, no exec linked twice). Applied: round 2's
  "no equip replay for the knife / bolt" made the item pop in at its idle place before the hands came back; now the
  equip's item type is remembered with it (`LastEquipType`) and a knife / bolt bag or pat replays the equip when it
  was made with the same item type (the knife's own draw), else the item is just shown again. Accepted risks (test
  list): the bag Out's left-hand IK-on notify and the pat's lack of an IK-on are left as for weapons (whether the knife
  layer applies left-hand IK is unverified); stop after 3 rounds.
- ab pasted (second paste: the first lost the 28 kn asset references, not loaded at paste time), cooked (the 28 kn assets in the cook) and installed 2026-11-05 09:04; probe on.
- ab tested (tester): empty-hands bag "mostly works, sort of janky when standing: when first invoked it kinda jumps,
  almost as if for a single frame it is in the top left"; bodies still flicker near the screen edge, single bodies too.
  Cause of the jump: AM_ImmLoot_BagIn blends in at once (0.0 s), the BagFix table over 0.15 s: frames 1-3 of the In
  ran 22-67 % corrected, the bag 15-23 cm above where the anim holds it (sim `research/bag/sim/inblend.py`; full table
  from frame 0: within 6 cm all through the In). Flicker: since 2026-11-01 PiPScopes (UE4SS, a second scene view
  rendered every frame, "second view ... render target 1040" in its log) is installed; edge-of-screen popping of
  skinned meshes is a culling / visibility-history symptom of an extra view; our graph touches no other actor's
  rendering.
- v1.3.2 ac: the bag table (`_mpf` / `_mpfc`) blends in at once (0.0 s, was 0.15), as the In.
- ac first paste: the table's BlendInTime 0.0 came back as the C++ default 0.25 (the known pasted-0.0 trap); 0.001 instead.
- ac second paste: the editor crashed again deleting the whole graph (the second delete in a session). Tester: "let's
  build the split up version right now".
- v1.3.2 ad: the actor graph is split over 7 event graph pages (`bp_graph.paginate`, harness): EventGraph (tick head,
  the menu gate, steps 0 / 1 / 4 / 5, the old dead nodes) 667 nodes, Doors 539, Touch 518, LootWindow 201, Reach 793,
  EndAndBag 641, HoldToUse 501 (the bound montage event with its bind). Exec links between pages = calls to custom
  events `IL_<page>_<n>` (10 events, 13 calls; synchronous, order unchanged); 87 shared pure nodes cloned per page; no
  data link crosses pages. `gen_actor_looting.py <dir>` writes `zonekit/paste/BP_ImmLootActor/<n>_<page>.txt` +
  `pages.json` (digests without names / ids); `harness/tools/paste_pages.ps1` = the tester's copy window (changed pages
  only, `pasted.json` = the last confirmed state). The single-file paste is retired. Content = ac (bag table blend-in
  0.001).
- ad pasted page by page (all 7 pages complete, 10/10 cross-page events resolved, kn links, blend-in 0.001), cooked (28 kn assets) and installed 2026-11-05 09:52; probe on.
- ad tested (tester): the backpack "looks totally fixed"; bodies still flicker with PiPScopes uninstalled; the rifle
  door "still doesn't look as good as pistol or unarmed"; nothing else tested. Probe (one door, a long gun in the
  secondary slot): its left hand rests at (38.3, 4.4, -24.2) cm from the eye (view axes); the Ar door asset starts / ends
  at the rifle stand idle's grip (47.3, 3.9, -14.0): the blend-in threw the hand 5 cm forward first (42.6, 2.4, -20.2),
  then back (30, -13, -14), out to the door (52, -26, -24) and home to (44.7, 2.3, -18.8), the IK finishing the last
  10 cm. Flicker: our test pak parked (`_parked_mods/2026-11-05_1000`), the tester loads once without the mod.
- v1.3.2 ae: `AS_ImmLoot_DoorPush/PullArNear` (make_grab_seq PART=doorarn: the Ar door with its ends at the measured
  grip + TOUCH_END_OFF, the pistol's door point): picked when LHandVX < 43 cm (the Doors page only). page_digest now
  ignores positions / box sizes (the Touch page differed by one comment box's height).
- Flicker: the tester loaded without Immersive Looting: the bodies still flicker = not this mod (closed).
- ae: Doors page pasted (verified), cooked (ArNear in the cook), installed 2026-11-05 10:06 (the mod back on); probe on.
- ae tested (tester, screenshot: a door hinged on the left, closing with a pistol: the hand at the lower left): "door
  open looks good. close looks bad no matter if armed or not ... the hinge is on the left, you can't pull it there to
  close it". Kit: a door leaf's mesh pivot is its hinge (SM_cit_out_door_a_04 0..104 cm, SM_cit_in_door_bb_01 -3..103,
  cupboards -51..0; 35 of 70 sampled door meshes edge-pivoted, the centred ones are frames / door boxes).
- v1.3.2 af: a pull reaches for the leaf's free edge: `_door_right` = (2 x the leaf's bounds centre - its origin) right
  of the view centre -> `AS_ImmLoot_DoorPull{Ar,ArNear,Pt,Kn,BH}R` (make_grab_seq PART=doorpullr: the pulls mirrored,
  +22 deg / bare hands +30; the knife takes the pistol's point, its own solve to the right failed). Pages: Doors and
  EventGraph (bp_graph.paginate now drops pure nodes nobody reads: 64 unused ones left the main page).
- af pasted (Doors + EventGraph, verified: 7 pages complete, 10/10 events, 5 PullR links), cooked, installed 2026-11-05 10:29; probe on.
- af tested (tester): the close "acknowledges the direction now, but on the right of the screen it is kinda janky: under
  the rifle and not far enough forward away from the camera, and the hand could use a bit of work". Also found: af's
  `DoorPullKnR` was built without the knife stance (deleted after ab's build): a frozen arm.
- v1.3.2 ag (assets only, no paste): the right-hand pulls with a weapon go to (46, 12, -3) cm from the eye (right of
  and above the weapon; the arm reaches ~44), cross OVER the grip both ways (`DOOR_OVER` (4, 6, 17) from the path's
  end), the shoulder turns forward up to 25 deg with the reach (`DOOR_PROTRACT`), the draw back 0.55 x the stroke and
  half the drop, the palm faces left (mirrored); PART=doorpullr builds the knife stance first.
- ag tested (tester, screenshot: the left forearm across the screen over the rifle, the back of the hand to the
  camera): "this looks way worse. big regression". Rolled back.
- v1.3.2 ah (assets only): the right-hand pulls = af's (mirrored pistol point, under the weapon) with the knife's now
  built on its stance (af's was frozen). The ag code stays in make_grab_seq behind DOOR_RIGHT (off).
- ah installed (10:50). Tester's choice for the armed right-edge close (asked: keep af / none / short touch left of the
  gun / same as the left close): "short touch left of the gun".
- v1.3.2 ai (assets only): `DoorPull{Ar,ArNear,Pt}R` = a short tug on the leaf left of the gun (`DOOR_TUG`: elevation
  -16, azimuth -10 deg from the eye, draw 10 cm, drop 5; hand to (49, -12, -16) cm, back to ~(40, -10, -18)); the
  knife / bolt and bare hands keep the mirrored reach. Installed 2026-11-05.
- ai tested (tester): "better. but rotate the hand during door close so the thumb is pointing down, clockwise 180 deg,
  so the hand looks like it is clasping the edge of the door and pulling it in".
- v1.3.2 aj (assets only, PART=pulls: every close): weapon families' close hand turned -180 deg about the reach
  (`DOOR_PULL_ROLL`: thumb 4-6 cm below the hand at the grip, was +5 above), the turn over frames 5-13 (it whipped round
  in 5: 38-53 deg a frame; now <= 35) and back over 22-33 (before the IK); bare hands -90 (`DOOR_PULL_ROLL_BH`: their
  close already had the thumb low; scan of 0 / +-90 / +-135 / -180: -90 lowest, -5.8 / -6.8 cm).
- aj tested (tester): "you rotated the hand counter clockwise when i specifically said clockwise". Cause: the 180 deg
  roll was baked into the target orientation and the slerp chose the way round (counter-clockwise).
- v1.3.2 ak (assets only): the close roll applied on top of the turn by its weight (`hl` = roll(reach, DOOR_PULL_ROLL x
  wv) x the turn; bare hands roll(vf, DOOR_PULL_ROLL_BH x the leg weight)): the thumb now goes up -> right -> down on
  screen (scan: +160..+241 deg clockwise for the weapon closes, +60 for bare hands). In UE axes a negative angle about
  the forward reach is clockwise seen from behind.
- ak tested (tester): "the hand looks correct in terms of its rotation, but it's still not following the door's arc ...
  make it look like the hand is following the edge of the door as it closes". Knife / bolt pickups work like the
  crouched one, "but the left hand is always in view: it grabs, comes back, and the item just disappears out of the
  hand. It needs to go off screen for a second and come back, as if putting the thing away" (crouched too).
- v1.3.2 al (assets only, PART=al): every close's draw (frames 9-22, bare hands 9-24) follows the circle of a leaf's
  free edge about its hinge (`door_edge`: radius 30 cm, 50 -> 10 deg open, drop 4; bare hands 0.75 of it; the armed
  right-edge tug 0.55 with 0.3 of the sideways part, it must not cross the gun): back and outward (away from the hinge)
  curving to straight back, e.g. rifle left edge (49, -24, -22) -> (32, -33, -25) cm from the eye; the hand turns with
  the leaf (0.6 of its 40 deg about the vertical), unwound with the roll. Crouched / knife / bolt pickups
  (`GrabBHViewCrouch`, `GrabKnView`): after the grab the hand goes down to (18..20, -15..-17, -51..-57) cm from the eye
  (elevation -65 deg, below the screen) by frame 26, stays to 34, comes back up to rest 34-44; the item is removed at
  1.2 s (frame 36, hand at -63 deg), the fingers open after it. Standing bare hands unchanged.
- al tested (tester): "i think it's good! we did it! let's cut a new release finally." Released as v1.3.2: the al paks
  unchanged (`zonekit/builds/v1.3.2/`). Shipped leftovers (harmless, all in every tested build): the unreferenced DEV
  assets (`Dev/W_ImmLootDev` via the actor's `DevPanel` variable, `Dev/ABP_ImmLootDevPose`,
  `AS_ImmLoot_DevArmRot` / `DevHandRot`), probe variables, `DOOR_RIGHT` / `DOOR_PROTRACT` code paths (off).
- Release cleanup (tester: "cleanup all the dev stuff now for this release"): `gen_actor_looting.py` now strips (unless
  `IMMLOOT_PROBES=1`) every exec node no event reaches (28: the old hold-to-use catch, the unwired 1.2 grabs and use
  pose) and every write to a variable the graph never reads (137 writes of 123 probe variables; spliced out of their
  exec chains, their value trees dropped by paginate), list in `zonekit/paste/stripped_vars.json`: 3,913 -> 3,316
  nodes. All 7 pages pasted by Noah (verified: node counts, 10/10 page events, no empty asset pins, no compiler
  message). `remove_unused_variables`: actor 160 (incl. `DevPanel`), MCM 10 (the DEV settings); MCM keeps its 14 usual
  infos. Deleted (kit, mirror, NewPackages): `Dev/W_ImmLootDev`, `Dev/ABP_ImmLootDevPose`, `AS_ImmLoot_DevArmRot` /
  `DevHandRot`, the intermediate `AS_ImmLoot_Grab`, `AS_ImmLoot_GrabBHAdd` / `GrabBHAddCrouch` / `PickPose` (only the
  dead nodes used them). The override pak had carried the unclassified DEV assets (614 KB -> 1 KB: now only the
  WorldSubsystemData); NewContent 7.6 -> 4.8 MB. `setup_assets.py` ACTOR_VARS pruned to the graph's variables (153).
  The UE4SS probe has nothing left to read (its values are gone); probe off.
- Cleanup build tested (tester): "everything works but unarmed door closing is off, I can only see a bit of my arm on
  the right side of the screen". Cause (al, not the cleanup): the bare-hands circle took the hand from 25 cm ahead to
  12 cm ahead and 50-61 deg to the side (off screen); the right-edge close (af) stretched the left arm across the body
  to its full reach (need 51.8 of 52.4 cm), the hand short of its point.
- v1.3.2 am (assets only, PART=bhpull): the bare-hands closes aim at their own point (`DOOR_BH_PULL`: elevation -15,
  azimuth -/+15 deg from the eye, at 0.9 of the arm from its root: left (31, -8, -9), right (25, 7, -7) cm) with a
  smaller circle (`DOOR_BH_EDGE`: 0.5, half sideways): the draw stays within -15..-26 deg elevation and 15..30 deg
  azimuth (on screen). The push is unchanged. (am's first run solved from the base pose's arm root, not the one the
  solve uses: the point came out 14 cm ahead; fixed.)
- am tested (tester, screenshot: empty hands, the forearm big in the lower middle, the wrist bent down, fingers to the
  floor): "the hand looks totally broken on close". And: "the hand twist on close is only needed when the door hinge
  is on the left of the screen: we close with the left hand, it needs to rotate if the hinge is on the left; if the
  hinge is on the right the hand should look upright, grabbing the open door edge".
- v1.3.2 an (assets only, PART=pulls): the clockwise turn to thumb down only in the right-edge closes ("R" = hinge
  left), every family; the left-edge closes keep the upright hand (palm toward the leaf, thumb up: the pre-aj hand).
  Bare hands: the closing hand is built per frame from the solved forearm (fingers along it, palm = up x forearm,
  thumb up; first try "palm right" ran along the forearm on the right-edge close: 48-71 deg of wrist bend), blended
  in by the door weight; wrist bend now 0 at the edge, up to 20 deg from the leaf's turn.
- an tested (tester, screenshot: right-edge close, empty hands, back of the hand to the camera, thumb down): "much
  better, but the index and middle finger look broken"; and "it is not choosing open or close correctly: sometimes it
  pushes when it should pull" (no details yet; the decision probe variables were stripped in the cleanup).
- v1.3.2 ao (assets only, PART=pulls): the closes' fist = the vanilla grab's frame 17, a pinch with the index lifted
  back at the knuckle (proximal phalanx -0.27 toward the back of the hand, middle -0.03; ring +0.09, curl +0.55):
  `door_fingers(hook=True)` gives the index and middle the ring finger's curl: at the edge all four fingers flex
  (+0.52..0.55 curl, +0.08..0.12 at the knuckle). Every close (weapon families and bare hands).
- ao tested (tester): hand animations good. Push / pull: "I open the door from one side (a push), go to the other side
  and close it: it does a pull when it should do a push, because I've gone to the other side." Cause: seen from the
  side it swung to, an open leaf lies along the view; closing, its pressed point first moves sideways across the view
  and slightly NEARER (the camera-ray test, first order ~0, read a pull) while the door as a whole swings away.
- v1.3.2 ap (paste: Doors + Touch): an open door (|DoorYaw| > 10) is decided at the press from the whole swing: free
  edge now (2 x bounds centre - hinge) vs that edge turned back by -yaw about the vertical (closed): nearer the camera
  when closed = a pull, else a push; the T7 movement test only decides closed doors (opening: the motion is along the
  view ray there, first order).
- ap pasted (Doors + Touch; verified: node counts, 8/8 page events, no empty asset pins, no compiler message), cooked and installed.
- ap tested (tester): "yeahhhhhh fuck yes. update the release". v1.3.2 re-cut from the ap build (zip, tag and GitHub release replaced).
