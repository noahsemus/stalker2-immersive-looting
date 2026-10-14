# Doors: kinds, how they swing, and how we choose push / pull (2026-10-13)

Tester (after v1.2.0): "opening always plays a push and closing always a pull, but doors can be in any state: a
locker is closed and I pull it open toward me. Account for every door-open possibility. The animation is also janky
like the old stash touch: it clips into the weapon on the way back and moves down."

## Kit findings (`zonekit/research/touch/` holds the scripts; this one: `run_headless.ps1` over the asset registry)
- `BP_DoorView` (native `DoorView`, `CoreVariables.cfg` `DoorBlueprint`): the world's ordinary doors. Leaves are
  `StaticMeshComponent`s on `PhysicsConstraintComponent`s with **swing1 limited to 90 deg, both ways** (swing2 / twist
  locked, no angular offset): a leaf can open either way, so the swing direction is decided at run time, not by the
  asset. `is_double_door`; the `Door` component has only `angle_restore_delay` / `angle_restore_speed`. Native
  functions `open_door`, `close_door(close_fast)`, `peek_door`, `peek_close_door`; the interactions are
  `open_door_single_click`, `close_door_single_click`, `peek_door_hold`, `close_peek_door_hold`, `locked_single_click`.
- Closets, cabinets and lockers: `BP_OpeningContainer` children under `GameDesign/InteractiveObjects/OpeningContainer/
  DoorForConteiner/` (`BP_fur_cit_closet_1..4`, `BP_fur_hospital_cabinet_1..2`, `BP_fur_kinder_cabinet_1..3`,
  `BP_fur_liv_wal_closet_1..3`, `BP_fur_sport_cabinet_1..3`, `BP_int_fur_locker_02_door_01`,
  `BP_int_gun_cabinet_door_01`), native `InteractableObject`: animated doors that open toward the player. Before
  build A only names with "Door" were treated as doors (the locker yes, the closets and cabinets no).
- Others, not handled (scripted / quest objects): `BP_BunkerDoor_01..07`, `BP_TrainDoor_01`, `BP_Safe_Big(_Small)`,
  `BP_BunkerHatch_*`, `BP_Arena_Closet`, `BP_Dalins_Safe`; `BP_StashBigSafe` / `BP_StashSmallSafe` are item
  containers (the stash touch).
- Legacy plain-Actor door Blueprints (`BP_Stalker2Door`, `BP_Stalker2PhysicsDoor`, `BP_InteractableDoor(_2)`,
  `BP_Stalker2DoorPhysics1`, `BP_gen_security_door_04`): no components in the CDO; whether any are placed is unknown.

## Choosing push / pull (build A)
Until v1.2.0: "the leaf is turned more than 10 deg from its rest yaw (open) = this press closes it = a pull, else a
push". Wrong whenever the leaf moves toward the player: opening a locker / closet, or closing a door that was opened
away from you.
Build A: the game moves the door at the press, so we measure instead of guessing. At the press we keep the point of
the leaf under the crosshair in the leaf's own frame (`DoorLocal`), its world position (`DoorW0`) and the camera
(`DoorCam0`); each tick we put the point back in the world: once it has moved 0.8 cm, its motion along the
camera-to-point line decides: toward the camera = a pull, away = a push. Not moved within `DoorDecideMax` (0.3 s): the
old rule. The touch starts at the decision (probe: `DoorRadial` cm, `DoorDecideT` s). Works for any door kind, any
state, either side, double doors, peeks.

## The door animation itself (build B, after A is confirmed)
Rebuild `AS_ImmLoot_DoorPush` / `DoorPull` (armed) and `...BH` (empty hands) with the touch recipe
(`zonekit/research/touch/README.md`): family stance (rifle / pistol), solved upper arm / forearm, one-way wrist,
open spread palm for a push, a closing hand for a pull, curved path that rejoins the grip from the left / below, IK
off fast and on near the grip.
