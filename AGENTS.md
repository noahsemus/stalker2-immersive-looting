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
Follow `harness/docs/pipeline.md` § Release. Nexus page: _(record the mod id here once it exists)_.
