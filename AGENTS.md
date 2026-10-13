# ImmersiveLooting — mod context for the agent

**First read `harness/AGENTS.md`**: the shared rules, tester workflow, pipeline and game knowledge for every
Stalker 2 mod. They apply here. This file holds only what is specific to this mod.

Purpose: Skif reaches out with his left hand and takes the item when you loot, instead of it vanishing instantly.

Repo `noahsemus/stalker2-immersive-looting`, Zone Kit plugin `ImmersiveLooting` (`/ImmersiveLooting/`), asset prefix `ImmLoot`. Created from the
harness on 2026-10-09.

## Current state (one line per checkpoint / release: date, what changed, what the tester confirmed in game)
- 2026-10-09: repo created, kit research done, plan written (`PLAN.md`; research in
  `zonekit/research/2026-10-09-pickup-and-left-hand-research.md`). Waiting on the tester: pick `ImmersiveLooting` in
  the editor's toolbar mod selector once (GameFeatureData), the three decisions in PLAN.md, a preview of
  `MG_fp_ak74_weapon_grab`. Then build 1.
- 2026-10-09: tester: **build the whole feature first, not in parts** (build 1 = everything; fixes one per cook
  afterwards). Generators written (`zonekit/tools/setup_assets.py`, `gen_actor_looting.py`, `gen_subsystem_spawn.py`)
  plus the dev probe `zonekit/tools/probe/ImmLootProbe`. Next: PLAN.md § Making build 1.
- 2026-10-09: tester: corpses and stashes too: one grab after the loot window closes if something was taken.
  Added to the build-1 generator (loot window from `IMC_Inventory`, "taken" from the window's weight texts and
  money; `zonekit/research/2026-10-09-loot-window-research.md`).

- 2026-10-09 checkpoint-b11 (Noah: "this is good, checkpoint it"; paks in `zonekit/builds/checkpoint-b11/`): loose-item
  pickups detected (`PC.GetInteractedActor`, else the interaction target's owner; build 1's `GetInteractionTarget`
  alone never saw loose items), empty hands play `AS_ImmLoot_GrabBH` = 8 view-pitch segments (the arm bones do not
  follow the view pitch) reaching lower left of centre (view frame (40, -28, -16) cm) with the left-hand IK switched
  off at the start (it pulled the hand to the grip point); the copy of the item waits where it lay, is pulled into
  the hand at the grab frame at real size and parented to `jnt_l_weapon`, removed at the pocket frame. Armed: the
  raised rifle grab `AS_ImmLoot_Grab` (not pitch-aware yet, untested since build 4). Corpse / stash reach coded, untested.

- 2026-10-09 checkpoint-b15 = release candidate (Noah: "looks good!!!! checkpoint as possible release"; paks in
  `zonekit/builds/checkpoint-b15/`): empty hands reach TO the item: `AS_ImmLoot_GrabBH` = 120 segments (item elevation
  -80..+25 x distance 30/45/60 x body azimuth -45..+15, from the item's bounds centre in the mesh frame), aimed short by
  an empirical bias (9 ahead, 15 right, 5 up in the view frame; cause still unknown, joint probe values logged), IK-off
  notifies through each segment; item pulled into the hand at the grab frame and parented. Tested: unarmed and with a
  pistol (armed = rifle grab `AS_ImmLoot_Grab`; one hand-recovery fired with the pistol). Not tested yet: PLAN.md test
  matrix (corpses / stashes, long guns, knife / bolt / detector, skips, gamepad, coexistence, save/load).

- 2026-10-10 v0.1.0 beta released (Noah: "cut this as the first release but make it 0.1.0 beta"): the checkpoint-b15
  paks unchanged (`zonekit/builds/v0.1.0/`, GitHub pre-release). Unused `AM_ImmLoot_Grab` and the probe-only nodes
  are still in it (harmless). Nexus page not created yet.

- 2026-10-10 rc-1.0.0 (Noah: "nice. new release candidate, tentative 1.0.0"; paks in `zonekit/builds/rc-1.0.0/`):
  corpse / stash touch: our `IMC_ImmLoot` (the player's own interact keys, copied at runtime) swallows the interact
  while a corpse / stash is in sight; the press plays the touch, holds the hand out at 0.6 s, then injects the game's
  interact (window opens); on close the montage plays on (armed) or back (empty hands). Armed = 25 short assets
  `AS_ImmLoot_Touch0..24` (hand toward the body's pelvis / stash centre, picked by its direction in view axes: with a
  weapon the arm rig follows the view). `AS_ImmLoot_Grab` carries `left_hand_curve` (rifles with an underbarrel idle
  pin the left hand otherwise). Noah confirmed: rifle, pistol, shotgun (body touch + return, loose items); rows 8-9
  (coexistence, save/load) fine, tested alongside the other mods throughout. Not tested yet: bare-hands / knife / bolt
  touch, detector, skips, spam, mutant corpses, take-all / nothing, hold-F drag, walk-away, gamepad / rebinds.

- 2026-10-10 v1.0.0 released (Noah: "tested everything, looks good, cleanup cook and cut a release"): the rc-1.0.0
  build minus the unused `AM_ImmLoot_Grab`, `AS_ImmLoot_GrabAR` and the single `AS_ImmLoot_Touch` (no referencers;
  the Blueprint is unchanged). Full PLAN.md matrix confirmed by Noah (bare hands / pistol / shotgun / rifle, human
  and mutant corpses, stashes, take-all / nothing, hold-F drag, walk-away, skips, spam, artifacts, alongside the
  other mods, save/load). Zip in `zonekit/builds/v1.0.0/`, GitHub release v1.0.0. Nexus page: mod 2972.

- 2026-10-10 rc-1.0.1 (Noah: "carrying bodies fully works. release candidate"; paks in `zonekit/builds/rc-1.0.1/`):
  Nexus reports "can't carry bodies" = 1.0.0's key capture (every hold F became a tap). Fix: no key capture (interact
  keys polled; at a press near a body / stash its tap interaction is switched off, a tap under 0.4 s = touch then
  injected interact, a longer hold = the game's own carry), once-per-world `ReturnLeftHandOnItemEnded`, the press needs
  a lootable target, setting `TouchBodies` (for the MCM toggle). Noah's own saves made after 2026-10-09 ~21:30 cannot
  carry even with the mod removed (his 17:13 save carries; cause unknown, not repaired): test on the 17:13 save.
  Tested there: carry, and carry after loose items / body tap / stash tap / save+reload; loot window opens sooner.
  Next: MCM toggle for the body / stash touch (Nexus: looting slower in combat / radiation). Kit = wip branch.

- 2026-10-10 v1.0.1 released (Noah: "with the faster looting window i don't think we need mcm support. let's cut
  the release"): the rc-1.0.1 paks unchanged; MCM toggle dropped (`TouchBodies` stays, default on, unused). Zip in
  `zonekit/builds/v1.0.1/`, GitHub release v1.0.1, `main` = the former wip branch.

- 2026-10-11 v1.1.0 released (Noah: "looks good. cut the release", a tentative release for the stash fixes): doors
  (push / pull), hold-to-use (checkpoint-holduse), stash / loose-item detection fixes, the new empty-hands pickup
  (FullBody local-additive tables `AS_ImmLoot_GrabBHAdd` / `...Crouch`, aimed standing and crouched, 1.0.0 fingers, item
  in the palm), MCM toggles for body / stash touch and doors (`BP_ImmLootMCM` -> actor `TouchBodies` / `TouchDoors`; header pictures `T_ImmLoot_MCMHeader` / `T_ImmLoot_MCMCatHeader`: the
  example's own were not shipped = white box behind white text). Released actor graph = the build Noah last tested
  (with its strafe counter-turn attempt, no visible effect); `zonekit/paste/BP_ImmLootActor.txt` / the generator already
  hold the untested build 55. Open: the hand swings while strafing during a pickup (fix designed, not built: `zonekit/research/strafe/README.md`).

- 2026-10-11 v1.1.1 released (Noah: "finally. cut the release"): hold-to-use showed no hand in 1.1.0. Cause: build
  28's `SelectString` node named `KismetStringLibrary` (it lives in `KismetMathLibrary`); the paste silently dropped
  it, the per-item use table path was empty and every hold-to-use played `AS_ImmLoot_UseAny`, whose reach lands off
  screen on other items' use poses. Fixed by loading the per-item table directly (checkpoint wiring). Also: the
  pickup-only item-copy changes (builds 26-48) gated off the use reach (`pick_bh`), the strafe experiments block off.

- 2026-10-13 checkpoint-bag (Noah: "bag is perfect, done and delivered", "checkpoint it"; paks in
  `zonekit/builds/checkpoint-bag/`): items used from the loot window get our use reach (the use held on its first
  frame, as hold F); MCM "Bag for bodies and stashes" (default off): the game's inventory bag animation copied
  (`AS_ImmLoot_BagIn/Idle/Out`, montages `AM_ImmLoot_Bag*` in LeftHand + RightHand), both hands' IK off for it, a
  weapon stays in the hands hidden and comes back with the game's last weapon equip; empty hands standing: pitch-fix
  pose table `AS_ImmLoot_BagPitchFix` (FullBody); bag mesh `SK_bpa_pla_01` in the left hand. Next: build r (armed
  grab / touch return spins: blend-out 0.35 s), not tested yet.

## Key facts (kit research 2026-10-09; details and citations in the research file)
- Loose items = `BP_StaticItemContainer_C` / `BP_SkeletalItemContainer_C` (parent `InteractableItemContainer`,
  `CoreVariables.cfg:888-889`), visual in `MeshComponent`; pickup is instant and has no BP-visible "item added" event.
  `PC.GetInteractionTarget` (`bp_api_dump2.txt:5193`) → owner gives the item under the crosshair each tick.
- Pickup key `IA_Interact` lives in `IMC_Interactivity` (`InputMappingContextPrototypes.cfg:229-235`).
- Artifacts and mutant parts are already animated in vanilla; corpses / stashes use the loot window.
- The reach: unused vanilla `MG_fp_ak74_weapon_grab` (`fp_ar_weapon_grab`, 1.667 s, `LeftHand` slot, left arm only,
  HandIK off 0.036 s / on 1.179 s, grab 0.569 s, chest 0.92 s). Every weapon layer has the `LeftHand` slot
  (`left_hand_blend_mask`); left-hand foregrip IK is switched by `AnimNotify_HandIK`, so play a montage asset that
  carries those notifies, not a dynamic montage of the bare sequence.
- Item attach point: bone `jnt_l_weapon` (child of `jnt_l_hand`).

## Assets this mod may override
- None planned. Never weapon `AnimCollection_fp_*` (OXA overrides 38), `BP_StaticItemContainer` (looting mods),
  `AnimBP_Player` (ZST), the pawn (ImmersiveDialogue).

## Files
- `PLAN.md` plan and test matrix · `BUILD.md` every edit asset by asset · `zonekit/README.md` engineering log
  (what each test showed, dead ends) · `zonekit/ImmersiveLooting/` plugin mirror · `zonekit/tools/` mod-specific generators
  and classifier lists · `zonekit/builds/` checkpoint and release paks · `mod.json` names and pak suffixes.
- `CLAUDE.md` / `GEMINI.md` only import `harness/AGENTS.md` and this file, for tools that don't read `AGENTS.md`.

## Release (only when the tester says "cut a release")
Follow `harness/docs/pipeline.md` § Release. Nexus page: mod 2972, https://www.nexusmods.com/stalker2heartofchornobyl/mods/2972.
