# Pickup, looting and left-hand animation research (2026-10-09)

Read-only kit research before any build. Keys: D2 = `<kit>\bp_api_dump2.txt`, D1 = `<kit>\bp_api_dump.txt`,
GD = `<kit>\Stalker2\Content\GameLite\GameData\`. Montage numbers come from a headless editor read
(`run_headless.ps1`) of ~200 montages and the player / layer AnimBPs (T3D exports); mesh space, cm, camera at
(0, 0, 160), +X forward, +Y right.

## 1. How a loose item works
- No per-item Blueprint: the game spawns `BP_StaticItemContainer_C` / `BP_SkeletalItemContainer_C`
  (`/Game/GameLite/Blueprints/Interactable/ItemContainers/`, GD `CoreVariables.cfg:888-889`), parent
  `InteractableItemContainer` (D2:3751, only `pause_skeletal_components`).
- Components (name table of the uncooked BP): `MeshComponent` (Static / Skeletal), `ItemContainerHold`
  (`ItemContainerHoldComponent`, `HoldTime`), native `ItemContainerInteractionComponent`, physics and sound
  components. The name `bLeftHandBusy` also appears in it (meaning unknown).
- `InteractionComponent` (D2:3823-3844): `play_single_interact_animation`, `set_interaction_active`,
  `interactable_anim_collection` (RO), `interaction_socket_name`, delegates `on_interacted_event`,
  `on_end_interacted_event`, `on_notify_interact_event` (`InteractSignature`), `on_montage_ended`.
  `HoldComponent` (D2:3553-3557): `is_hold_started`, `on_hold_started/finished/interrupted_event`.
  Whether the delegates are BlueprintAssignable is not known yet.
- `InteractionType` (D1:3329) SINGLE_CLICK / HOLD / MULTI_CLICK / AUTO_INTERACTION / COMBINED / DEAL_DAMAGE;
  `InteractLengthType` (D1:3187) NONE / INSTANT / REGULAR / WITH_ANIM.
- Visual: item cfg `MeshPrototypeSID` → GD `MeshPrototypes.cfg` `MeshPath` + `MeshType` (mostly
  `StaticMesh'/Game/_Stalker_2/items/...'`, 81 skeletal rows: guns, bodies). The item cfg's own `MeshPath` is the
  first-person hand mesh (`Bread`: `SK_bread_fp`, socket `jnt_l_weapon`, `ConsumablePrototypes.cfg:14-28`). From
  Blueprint: `GetComponentByClass(StaticMeshComponent)` → `GetStaticMesh` on the world actor.

## 2. How the player picks up
- `IA_Interact` (`InputActions/Delayable/`, no triggers) is mapped in `IMC_Interactivity` (F, gamepad face-left,
  `InputTriggerDown`, priority High; GD `InputMappingContextPrototypes.cfg:229-235`), not in `IMC_Exploration`.
  Tap vs hold is native (`HoldTime`, `HoldPreventFromDefaultInteractionPercent = 20`, CoreVariables:179).
- `MaxInteractionDistance = 200` (cm), `ItemCollisionEnableDelay = 1.0` (CoreVariables:341-351, 465).
- `PC.get_interaction_target() -> InteractionComponent` (D2:5193), `get_interacted_actor` (5191),
  `get_interacted_component` (5192), `get_interact_length_type` (5190), `is_interaction_in_progress` (5218),
  `play_interaction_in/out/interrupt_animation` (5316-5318), `Obj.is_left_hand_busy` (4950).
- No BP-visible "item added to inventory" event: `ItemManager` has no members, quest `OnPlayerGetItem` needs a fixed
  item SID. The pawn's `on_next_item_to_take_set_bp` etc. need a pawn override (forbidden).
- Hook for a NewContent actor: read `PC.get_interaction_target()` → owner each tick (an owner read, not a scan), cache
  the item actor, its mesh and world transform; the pickup is the cached actor vanishing (`OnDestroyed` / invalid /
  hidden) or our own `IA_Interact` Started.
- Pickup sound `SFX_Item_Pickup` (`PlayerItemsSounds.sfx_pick_up`, D2:5781-5785) is posted natively; not usable as a
  timing signal.

## 3. Which loot paths vanilla already animates
| Path | Vanilla |
|---|---|
| Loose items (F) | Instant, no animation (neither container BP has an `InteractableAnimCollection`) |
| Artifacts | Animated: `BP_Artifact` → `AnimCollection_PickupArtifact` → `MG_FP_Player_AR_ArtifactPickup_01` / `_Det_` (MainActionSlot, both hands / right hand, `AnimNotify_AttachItem PickingUpItem` on `jnt_r_weapon`, forces `AnimBP_Player_TwoHandedItem`) |
| Mutant parts | Animated (`MutantLootInteractionComponent`; `UseMutantLootWithoutWidget = true` → `AnimCollection_Player_MutantLoot_alt` → `MG_fp_bh_creaturestash_looting_common`, FullBody, knife) |
| NPC corpses | Search = loot window only; carry = `MG_fp_dead_body_pickup` (FullBody) |
| Stashes | The prop animates (`BP_StashBigSafe` ...), no player hand animation |

## 4. Left-hand animations
| Asset | Length | Slot | Notes |
|---|---|---|---|
| **`ar/ak74/MG_fp_ak74_weapon_grab`** (= `MG_fp_gp37_weapon_grab`) on sequence `ar/common/grabitem/fp_ar_weapon_grab` | 1.667 s | LeftHand | Full pose (ref `fp_ar_idle_stand` frame 0). HandIK off 0.036 s, `AttachItem PickingUpItem` (`jnt_l_weapon`) 0.569 s, `AttachItem RemoveItemFromHand` 0.803 s, HandIK on 1.179 s, blend out 0.7 s. Hand path: grip (47, 3, 144) → down-left (42, -33, 130) at 0.33 s → forward grab (55, -16, 145) 0.5-0.67 s → chest (18, -8, 118) 0.92 s → grip by ~1.4 s. Right hand 9.9 cm, weapon dips 4.5 cm, spine / camera 0. |
| `Flashlight/Montages/MG_fp_<stance>_flashlight` (ar, pt, bh, knife, bolt, f1, rgd5, detectors...) | 0.967 s | LeftHand (+ WeaponSlot, CameraSlot) | GSC's per-stance template for one left-hand gesture; ar / pt bracket with HandIK off/on |
| `NightVisionGoggles/Montages/MG_FP_Player_*_NVG-SwitchOn/Off_01` | 1.667 s | LeftHand (+ WeaponSlot, CameraSlot) | Same, per stance |
| `ar/common/showhide/lefthand/MG_fp_remove_left_hand_from_item` / `MG_fp_return_left_hand_on_item(_no_ik)` | 0.633 / 0.467 s | LeftHand | Hand off the grip and back; the plain return turns HandIK on at 0.136 s (recovery if our montage is cut) |
| `MG_fp_ar_left_hand_fast_unequip(_03)`, `pt/.../MG_fp_pt_left_hand_fast_unequip` | 0.33-0.5 s | LeftHand | Quick hand-off |
| `Items/Antirad/MG_fp_antirad_use` | 1.7 s | LeftHand | Injector over any weapon |
| Artifact pickup, dead body pickup, creature stash, dialogue take/give item | 1.8-5 s | MainActionSlot / FullBody / UpperBody | Both hands, whole body or right hand: not usable |

- The firearm AnimCollections have a `WeaponAnimations.PickUpItem` montage field; only
  `AnimCollection_fp_AK74_GrenLaunch` and the gp37 GrenLauncher / BuckLauncher collections fill it (with the
  weapon_grab montage). Whether native code plays it on a pickup is untested; filling it for other weapons means
  overriding AnimCollections (OXA overrides 38): not an option.

## 5. Slot path for a left-arm montage
- Every weapon layer has a `LeftHand` slot behind `left_hand_blend_mask` (jnt_l_shoulder down to the fingers,
  local-space rotation), after MainActionSlot / UpperBody, chained RightHand → LeftHand → CameraSlot → DefaultSlot:
  `AnimBP_PlayerWeaponLayer` (all firearms), `AnimBP_player_bh`, `AnimBP_Player_Knife`, `AnimBP_Player_fp_bolt`,
  `AnimBP_Player_fp_F1`, `AnimBP_Player_TwoHandedItem`, `AnimBP_PlayerDetectorLayer` (weighted by
  `DetectorData.bIsLeftHandSlotEnabled`).
- Left-hand IK to the foregrip: `TwoBoneIK_GSC` jnt_l_hand → `jnt_weapon`, alpha `HandsIKData.LeftHand.Alpha`,
  skipped while `StateData.bIsLeftHandBusy`; applied after the LeftHand slot (firearm, knife, bolt, F1 layers and
  `AnimBP_Player`). Montages switch it with `AnimNotify_HandIK` (HandToApply LeftHand; default = off over 0.2 s
  cubic, EndValue 1 = on). So a dynamic montage of the bare sequence (no notifies) would leave the hand glued to the
  grip on rifles / pistols: use a montage asset with the HandIK notifies.
- Slot group of LeftHand = the unnamed default group (with DefaultSlot, WeaponSlot, RightHand, CameraSlot): our
  montage stops / is stopped by flashlight, NVG, detector equip, injector, left-hand bolt throws.
- With a detector in hand its "Additional" pose is masked over the left hand after the slot (bh
  `LayeredBoneBlend_3`, weight `bHasDetectorInHands`): untested.
- Skeleton `SK_stalker_Skeleton`: `jnt_l_shoulder` → `jnt_l_arm` → `jnt_l_fore_arm` → `jnt_l_hand` →
  **`jnt_l_weapon`** (the game's left-hand item point). `LeftHandSocket` (roll -90) exists on `SK_stalker`; not
  confirmed on the first-person mesh. Attach to the bone `jnt_l_weapon`.
- `jnt_spine_03` is the same for ar / pt / knife / bolt (-16.8, -5.3, 125.1), bare hands ~11 cm off: one rifle-made
  reach should fit most stances.

## 6. Other mods (Nexus GraphQL search + installed paks, 2026-10-09)
- No existing pickup / grab animation mod for Stalker 2. Related mods all make looting faster or skip animations
  (Faster Looting 2406, Lootable Zone 1495, Loot Take All Close 2671, Mutant Looting SpeedUp 1916, Fast Mutant loot
  1727, Sota Classic Mutant Loot 1923, No Wasted Movement 2718 (edits 1,407 vanilla montages), Quick Container and
  Inventory 2007, Faster backpack 84). Ultimate Customization Tool 2733 auto-loots with no interaction at all.
  Design consequence: short, never blocking, skipped in combat / sprint, one gesture per pickup burst, never fired by
  inventory changes.
- Installed on the dev box: nobody overrides `AnimBP_player_bh`, `AnimBP_PlayerWeaponLayer`, the mutant loot
  collections, `fp_ar_weapon_grab`, the left-hand show/hide montages. ZST overrides `AnimBP_Player`,
  ImmersiveDialogue the pawn.
- Player Gestures 2.2.1 (1674): NewContent only; plays gestures in `PreActionFullbodySlot`, stances in `WeaponSlot`,
  its own copy of the bonfire sit; hooks the pawn's hand events (`On Return Left Hand On Main Item`, ...). Test our
  reach with its lowered stance and its sit.
