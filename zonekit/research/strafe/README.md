# Strafe swing during an empty-hands pickup: research and the planned fix (2026-10-11)

Status: designed and reviewed ("go with changes"), **not built**. v1.1.1 ships with the old strafe experiments switched
off (`sqhx.then_7` unlinked in `zonekit/tools/gen_actor_looting.py`).

## The bug
Strafing (A/D) during an empty-hands pickup, the reaching hand swings 38-106 cm across the screen. The camera does not
turn; Skif's upper body does, and the arm with it.

## Why every earlier fix failed (builds 47-55)
- Strafing turns the whole body about 90 deg around the camera's vertical axis: bh walk/run additives
  (`AS_fp_bh_walk_left_add` ...) are mesh-space rotation offsets on hips, spine, shoulders and arms.
- **The camera rides the chest.** In `AnimBP_player_bh`, `CopyBone_2` copies `VB jnt_camera` (a virtual bone whose
  source is `jnt_spine_03`) onto `jnt_camera`; it is active (AlphaInputType Bool, enabled). The strafe additive's VB
  channel is what keeps the view still. Anything that turns spine_03 against the animation turns or moves the camera.
- Simulated (`sim/`, validated against UE's own evaluation to 0.001 deg): spine twist turns the camera 61-95 deg; a
  MainActionSlot idle hold turns it 76-94 deg; the curve `AdditiveMovingUpperBody` = 1 moves it 11-39 cm; a plain
  LeftHand-slot idle hold leaves the arm 90 deg off. All rejected.
- Crouched movement (LowCrouch, `BS_fp_bh_lowcrouch`) does not turn the upper body: no fix needed there.

## The plan ("U1")
A non-additive sequence in the **LeftHand** slot (bh `LBB_4`, `left_hand_blend_mask`, local blend, weight 1): all 36
mask bones at `fp_bh_idle_stand` frame 0, except `jnt_l_shoulder` (parent `jnt_spine_03`), whose local transform puts
the shoulder where it sits at rest relative to the camera. The FullBody grab tables stay unchanged. Played paused;
the actor sets the frame every tick from a direct index (no search):

- `Ts` = `GetSocketTransform(jnt_spine_03, RTS_Component)`, `Tc` = same for `jnt_camera`.
- `P = InverseTransformLocation(Tc, Ts.Location)`, `F = InverseTransformDirection(Tc, -GetRightVector(Ts.Rotation))`.
- `yaw = Atan2Deg(F.Y, F.X)`, `pitch = AsinDeg(F.Z) + 6.873`, `theta = Atan2Deg(P.Y, -P.X)` (rest: 0, 0, 1.7).
- Moving (pawn speed >= 10 cm/s): `row = itheta*7 + ip`, `itheta = clamp(round((theta+100)/10), 0, 20)`,
  `ip = clamp(round((pitch+24)/6), 0, 6)`, `u = clamp((yaw+100)/10, 0, 20)`; time = `(row*21 + u)/30`.
- Idle (< 10 cm/s): time = `(3087 + clamp(round((pitch+10)/2), 0, 7)*21 + u)/30`.
- Data: `review/U1_table.json` (jnt_l_shoulder local per frame, layout, key strings). Built by `review/agrid.py`.

Simulated: worst case while moving ~10 cm (vanilla 80-106), 95th percentile 6-8 cm, standing 1.7-2.7 cm (vanilla
3.9-6.5), camera 0. Reversing A<->D blends for a few frames (20-40 cm, every variant). One frame of lag is inherent.

## Required with it (reviewer)
1. Speed-gated idle block (above), else standing pickups get worse.
2. Start only if no DefaultGroup slot is active (LeftHand, DefaultSlot, CameraSlot, RightHand, WeaponSlot): it would
   cut flashlight / NVG / injector / landing montages. Never restart it after the game stops it.
3. Exclude the table montage from the mod's own LeftHand checks (the "lefthand" skip; spam pickups during blend-out).
   Hold-to-use: the table must be fully off before the game's use montage resumes (LBB_4 is after MainActionSlot).
4. LoopCount 1,000,000, rate 0.0001 (a pasted 0.0 reverts to 1.0), start at the computed frame, blend in 0.1 s, blend
   out 0.2 s only after the grab's return (arm off screen).
5. A rest frame at time 0 carrying `AnimNotify_HandIK` (LeftHand off), as checkpoint-b11 did; start there.
6. Standing only (crouched rest locals are wrong; LowCrouch needs nothing).
7. Asset: non-additive, linear, no root motion, no frame stripping, the 36 mask bones keyed.
8. Probe: table frame, yaw/pitch/theta, speed, `Montage_IsActive(table)`, `IsSlotActive(LeftHand)`,
   `HandsIKData.LeftHand.Alpha`, hand relative to the camera.

Expected side effect: the hand stays fixed in view while strafing, so the item copy slides across the screen into it.
Stretched left-shoulder skin was checked on 7 player meshes: never inside a 110x72 deg view (closest 3.4 deg outside).

## Files
- `strafe_context.md`, `strafe_plan_f.md`: the brief given to the research / review agents.
- `sim/`: the pose simulator (`dump_poses.py` runs read-only in the editor and writes `simdump.json`, ~30 MB, not
  committed; `simcore.py` the pose maths; `sim.py` / `sim3.py` scenarios; `*_out_*.txt` results).
- `review/`: table construction and checks (`agrid.py`, `grid.py`, `common.py`; `r*.py` lag / blend / idle /
  frame-jump checks; `gl*.py` / `ed_*.py` skin visibility). Large pickles and glTF exports were not committed.
- `simcam.py`, `simtable.py`, `strafe_study.py`: the first agent's camera model and table sketch.
