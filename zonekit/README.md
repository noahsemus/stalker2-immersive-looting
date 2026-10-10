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
