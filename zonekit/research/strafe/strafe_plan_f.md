# Plan f (LeftHand re-root table) for the strafe swing — for adversarial review

Context: read `strafe_context.md` (same folder) first. Two independent research agents then established:

## Facts (both agents agree; files in this folder and `sim/`)
- The camera rides the chest: bh WeaponLayer `CopyBone_2` copies `VB jnt_camera` (virtual bone, source jnt_spine_03,
  target jnt_camera) onto jnt_camera, component space, AlphaInputType=Bool, bAlphaBoolEnabled=True (active). The strafe
  additive's VB channel is what keeps the camera still while the body turns ~90 deg about the camera's vertical axis.
- Every LayeredBoneBlend in the bh layer / AnimBP_Player blends in LOCAL space (bMeshSpaceRotationBlend False).
- Masks (BlendMask, listed bones weight 1): legs_blend_mask = hips, spine_01, legs, IK feet, knee VBs;
  left_hand_blend_mask = jnt_l_shoulder ... all left fingers, l_weapon, arm helpers (36 bones), no spine/camera/VB.
- Strafe additive: bh ApplyMeshSpaceAdditive_1 on LinkedInputPose "Moving" (Walk state: lower_body_blend_mask, upper
  part = TwoWayBlend(UpperBody.Walk, Identity) alpha = curve AdditiveMovingUpperBody; BS_fp_bh_walk for both).
  All slots (MainActionSlot, UpperBody, RightHand, LeftHand, CameraSlot, DefaultSlot, FullBody) come after it.
- Crouched movement uses LowCrouch (BS_fp_bh_lowcrouch): no upper-body turn (hand steady within 1.3 cm).
- Simulator (`sim/simcore.py`, validated to <=0.001 deg / 0.000 cm against UE's own evaluation) — hand displacement vs
  standing still, segment 44, t 0.5: none 38-49 cm p-p; twist spine_01: camera turns 61-95 deg; MainActionSlot idle
  hold: camera turns 76-94 deg; LeftHand rest hold (local): 7-30 cm p-p, arm still off by the chest turn; curve
  AdditiveMovingUpperBody = 1: hand still relative to camera but the camera moves 11-39 cm.

## Plan f
- A NON-additive sequence played in the LeftHand slot (bh LBB_4, left_hand_blend_mask, local blend, weight 1). Each
  frame keys every bone of left_hand_blend_mask at its rest (fp_bh_idle_stand frame 0) local value, except
  jnt_l_shoulder, whose local transform (rotation + translation) is chosen so the shoulder sits where it does at rest
  RELATIVE TO THE CAMERA, for one sampled pose of spine_03 relative to jnt_camera.
- ~300 samples: every 6th frame of the bh walk/run left/right strafes (plus diagonals / start-stop to add), at blend
  weights 0.25/0.5/0.75/1. Sim: <=6 cm everywhere incl. unseen moves (forward 5.3 cm vs 27.5 vanilla; half-left
  3.5 vs 31.7); camera 0.00; 1-frame lag: walk <=6, run up to 15 cm at 30 fps.
- Blueprint (actor ticks TG_PostUpdateWork): during an empty-hands standing pickup only, each tick read
  GetSocketTransform(jnt_spine_03, RTS_Component) and (jnt_camera, RTS_Component), compute spine_03 relative to the
  camera, find the nearest sample (key = ?), Montage_SetPosition on the paused LeftHand montage (rate 0.0001; pasted
  0.0 reverts to 1.0 in this kit). Stop it at the pickup end (blend out ~0.2 s).
- Our FullBody grab additive (local, keyed on l_arm / fore_arm / hand / fingers, ref = idle frame 0) unchanged.
- Costs: the left clavicle detaches from the chest by 38-53 cm walking (sim says both ends stay >= 4 cm behind the eye
  in camera space at any pitch); LeftHand (DefaultGroup) montage stops / is stopped by game LeftHand / CameraSlot /
  DefaultSlot montages (flashlight, NVG, antirad injector) during the pickup; walk arm swing and breathing replaced by
  rest.
- Prior BP technique that works in this kit: ImmersiveCampfires plays paused yaw tables and sets the frame every tick
  (`../stalker2-immersive-campfires/zonekit/tools/make_sit_yaw.py`, gen_actor_seated_mode.py).

## Open questions for the reviewer
1. Is LeftHand actually evaluated with OUR montage when hands are empty? (Antirad injector plays there in vanilla.) Any
   bool gating LBB_4 weight? Left-hand IK after it (TwoBoneIK_GSC_2, alpha HandsIKData.LeftHand.Alpha) with bare hands?
2. Does a non-additive LeftHand montage + our FullBody local additive compose as the sim assumes (local blend: the
   held local of jnt_l_shoulder relative to the turned parent clavicle/spine)? What is jnt_l_shoulder's parent?
3. The nearest-sample key: what minimal key (e.g. spine_03 yaw rel camera + spine_03 position rel camera) gives
   <=6 cm, and how to search ~300 samples per tick in Blueprint cheaply (or a 2-D grid indexed directly)?
4. Is the detached clavicle visible: first-person body mesh skinning (chest / shoulder verts weighted to both spine and
   shoulder) stretched across 40-50 cm — would stretched polygons show in view (FOV correction shader scales
   sideways positions; foreground depth scale 0.225)? Shadow mesh separate?
5. Lag: does the actor's PostUpdateWork tick read the CURRENT frame's pose and does Montage_SetPosition take effect
   the next frame? Any better ordering (tick prerequisites on the mesh)?
6. Blend-in: LeftHand montage blend-in time while the slot weight ramps (local blend of the slot node, half-weighted
   shoulder transforms) — artefacts at pickup start/end?
7. Anything that makes f fail in game that the sim does not model (leg IK / foot placement, turn in place, root
   motion, compression of a 300-frame non-additive asset, montage section length, the 0.0001 rate drifting through
   frames, network of other mods overriding AnimBP_Player).
