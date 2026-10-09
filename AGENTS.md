# ImmersiveLooting — mod context for the agent

**First read `harness/AGENTS.md`**: the shared rules, tester workflow, pipeline and game knowledge for every
Stalker 2 mod. They apply here. This file holds only what is specific to this mod.

Purpose: Skif reaches out with his left hand and takes the item when you loot, instead of it vanishing instantly.

Repo `noahsemus/stalker2-immersive-looting`, Zone Kit plugin `ImmersiveLooting` (`/ImmersiveLooting/`), asset prefix `ImmLoot`. Created from the
harness on 2026-10-09.

## Current state (one line per checkpoint / release: date, what changed, what the tester confirmed in game)
- 2026-10-09: repo created. Next: the tester picks `ImmersiveLooting` in the editor's toolbar mod selector once
  (GameFeatureData), then kit research for PLAN.md.

## Key facts (verified; cite file:line in the kit)
- _(fill in as research lands)_

## Assets this mod may override
- _(none yet; see harness/docs/compatibility.md before adding any)_

## Files
- `PLAN.md` plan and test matrix · `BUILD.md` every edit asset by asset · `zonekit/README.md` engineering log
  (what each test showed, dead ends) · `zonekit/ImmersiveLooting/` plugin mirror · `zonekit/tools/` mod-specific generators
  and classifier lists · `zonekit/builds/` checkpoint and release paks · `mod.json` names and pak suffixes.
- `CLAUDE.md` / `GEMINI.md` only import `harness/AGENTS.md` and this file, for tools that don't read `AGENTS.md`.

## Release (only when the tester says "cut a release")
Follow `harness/docs/pipeline.md` § Release. Nexus page: _(record the mod id here once it exists)_.
