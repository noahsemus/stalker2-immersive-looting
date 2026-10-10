# Body carry broken: handover (2026-10-10, unresolved)

**Status:** unresolved after ~3 hours and 13 test builds. `main` is back at the v1.0.0 release; all the 1.0.1 work is
on branch `wip/1.0.1-body-carry` (generator, assets, probe, full log in `zonekit/README.md` from "v0.2 corpse /
stash touch" down). Read this before touching the corpse/stash code again.

## The reports
1. **Nexus (discotizer, 10 Oct, right after v1.0.0):** "grabbing dead bodies don't work anymore" = hold F to carry a
   body does not work with Immersive Looting 1.0.0 installed.
2. **Noah, same day, on his own save (test builds):** close to a body the interaction marker stays **a dot**; it
   never turns into the vanilla "hold F" carry prompt (a world-space hint attached to the body, like the loot hint;
   NOT the bottom-centre contextual legend). Holding F does not carry the body.
3. Loose items are fine: their "hold F to use" prompt shows and works (our reach plays, then the use animation).
   Looting bodies / stashes with a tap works (touch, then the window). Noah: other mods are not the cause; carrying
   worked before Immersive Looting.

## What 1.0.0 does around bodies (the shipped code, `main`)
While a corpse (Obj, not alive, has a `DeadBody` component) or a stash is in sight, the actor adds its own
`IMC_ImmLoot` (priority 1000, the player's interact keys copied in with `QueryKeysMappedToAction` + `MapKey`) bound to
`IA_ImmLootInteract` (`consume_input` true) and `auto_receive_input = Player0`. Our action's press plays the touch,
then the actor removes the context and injects `IA_Interact` once (`InjectInputForAction`) = always a TAP. A hold is
therefore never delivered to the game: this alone explains report 1 (hold opens the loot window / no carry).

## Every build and its result (all on Noah's save, rifle / shotgun, test pak only, verified each time)
| Build | Change | Carry | Prompt |
|---|---|---|---|
| 1.0.1a | release key after tap; held 0.4 s = remove context + one injected press | no (hand out/back, then the window) | dot |
| 1.0.1b | held = keep context, inject `IA_Interact` every Triggered tick | no (nothing) | dot |
| 1.0.1c | `IA_ImmLootInteract.consume_input` false; at the press `SetInteractionActive(false)` on the body's `DeadBody` (tap) component, back on after | no | dot |
| 1.0.1d | NO input context, NO input on the actor (`auto_receive_input` off): keys polled with `PC.WasInputKeyJustPressed/Released` | no | dot |
| 1.0.1e | no calls into the game's interaction system at all (`GetInteractedActor` / `GetInteractionTarget` / `GetInteractedComponent` replaced by our own `SphereTraceSingle`) | no | dot |
| 1.0.1f | corpse branch switched off (nothing read from bodies) | no | dot |
| 1.0.1g | actor never ticks (CDO `bStartWithTickEnabled` false): nothing of ours runs | no | dot |
| 1.0.1h | unused `IA_ImmLootInteract` / `IMC_ImmLoot` deleted from the pak; dev probe (UE4SS Lua) removed from the game | no | dot |
| **1.0.1i** | **once per world `PC.ReturnLeftHandOnItemEnded()`** | **YES (Noah: "finally, holding F picks up a body")** | dot |
| 1.0.1j | actor tick off again (so the reset did not run) | no | dot |
| 1.0.1k | reset + `PC.EnableInteractions()` | no | dot |
| 1.0.1l | reset at load + again each time a new body comes into sight (not during an interaction / LeftHand animation); no EnableInteractions | no | dot |

## What this establishes
- With nothing of ours running (1.0.1g) and no input assets (1.0.1h) the carry was still dead on Noah's save, so on
  his save the fault is (also) **persistent state**, not live code.
- The candidate state: two dev builds this morning (the first touch builds, ~10:50-11:20, "patch_touch3") called
  `PC.RemoveLeftHandFromItemEnded()` at every corpse touch and never the matching `ReturnLeftHandOnItemEnded()`
  (its trigger flag was never set). That native call is what the game's own "remove left hand from item" montage
  reports at its end. `PC.IsLeftHandBusy()` read **true at rest** in every probe log after that (but it was only
  logged from that build on: no clean baseline). Carrying a body is a left-hand action.
- `ReturnLeftHandOnItemEnded` restored the carry once (1.0.1i) but the same call did not in 1.0.1k / 1.0.1l. Unknown
  whether 1.0.1i's success was the call, its timing relative to the save being applied, or something else. Not
  reproduced.
- The shipped 1.0.0 never calls `RemoveLeftHandFromItemEnded` (checked: tag and release zip), so report 1 is the key
  capture, report 2 may be Noah's save only. **Not verified** that a clean save with the no-capture code carries.
- The "hold F" prompt stayed a dot in every build, including 1.0.1i where the carry worked.
- The game's interaction prompt widgets (`W_InteractView`, `W_InteractViewDots`, `W_InteractHintInputController`)
  have empty graphs: native. Body = `DeadBody` (SingleClickComponent: search) + `DeadBodyHoldComponent`
  (HoldComponent: carry). `IA_Interact` has no action triggers; `IMC_Interactivity` maps F / gamepad face-left with
  `InputTriggerDown` (0.5); the hold is timed natively (`HoldIPU`, `HoldPreventFromDefaultInteractionPercent` 20 in
  `CoreVariables.cfg`). `PC` has `DisableInteractions` / `EnableInteractions`, `GetInteractLengthType`,
  `IsLeftHandBusy`, `RemoveLeftHandFromItemEnded` / `ReturnLeftHandOnItemEnded`, `ResetInteractionTarget`.
- UE4SS Lua on this setup cannot enumerate class properties (`ForEachProperty` is nil; struct fields unreadable):
  the component state was never read.

## Not tried yet (ordered by information per run; every run must carry a candidate change, Noah does not do
## probe-only or vanilla runs)
1. **Holstered** (no weapon in hand): does the carry / prompt work on Noah's save with the current release? If the
   left-hand state is the cause, empty hands may behave differently.
2. **A brand-new game** (new save, the mod installed) with the no-capture build (`wip` branch, 1.0.1d logic or later):
   separates "save state" from "the mod". If it carries and prompts there, ship the no-capture code + the reset.
3. **`PC.ResetInteractionTarget()` / `SetInteractionTarget(None)`** once at load (Immersive Campfires uses these:
   a stale interaction target from an injected interact could block the hold component's focus and its prompt).
4. **Read the state for real:** C++ UE4SS probe (`dllmain.cpp` pattern from ImmersiveDialogue's probe) to read
   `AnimInstancePlayer.StateData.bIsLeftHandBusy` and the `DeadBodyHoldComponent` fields; or the UE4SS GUI header dump
   (Dumpers tab) for the real field names. Bundle with a candidate change.
5. Compare `IsLeftHandBusy` holstered vs armed at rest on a clean save, to know whether "true at rest" is normal.

## Must-haves for the next release (Noah)
- No key capture (1.0.1d+ polling or simply no interception of the hold); the carry must be pure vanilla, no touch
  animation on a hold.
- Users' saves must be able to carry bodies after updating (keep a state reset if the cause is state).
- The vanilla "hold F" prompt must appear.
- Other 1.0.1 fixes on the wip branch: the press must require a lootable target (the crosshair ray made any press a
  touch); `harness` `layout_tree` fix (promoted) for paste layouts.

## Environment left behind
- `main` = v1.0.0 plugin and tools; the kit still holds the wip assets (deploy `main` with
  `harness/tools/deploy_to_kit.ps1` with the editor CLOSED before any new work, or check out the wip branch).
- Dev test pak removed; Noah re-enables the Vortex 1.0.0 copy. The UE4SS probe is disabled (`mods.txt`
  `ImmLootProbe : 0`, folder removed from the game; source on the wip branch).
- Harness bug seen: `push_harness.ps1`'s sync commit also commits whatever is already staged in the mod repo
  (c75c690 swept in two staged deletions).
