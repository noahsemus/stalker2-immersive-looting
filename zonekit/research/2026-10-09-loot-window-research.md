# Loot window (corpse / stash) detection research (2026-10-09)

Kit only (headless T3D exports of the inventory widgets, IMCs, IAs, container BPs and the pawn). D2 =
`<kit>\bp_api_dump2.txt`, GD = `<kit>\Stalker2\Content\GameLite\GameData\`.

## The view
- Corpse search, world stashes, the player's own stash and the I-key backpack all use one view:
  `W_Inventory` (`/Game/GameLite/FPS_Game/UIRemaster/Inventory/W_Inventory`, parent native `InventoryNew` D2:3851 →
  `ViewBaseExtended` → `ViewBase` D2:7286; GD `CoreVariables.cfg:933` `InventoryWidgetClass`). `W_InventoryNew` is a
  redirector. Its event graph is empty (PreConstruct / Construct / Tick disabled): open, close, take, take all,
  drag and drop are native.
- Widget tree: `LootOverlay` → `LootGridWidget` (`W_ExpandableLoot_C`, `ExpandableCustomGrid`), `InventoryWidget`
  (`W_PlayerGrid_C`, `CustomGrid` D2:2415), each grid with `WeightBar` (`W_WeightBar_C`) → `CurrentWeightText` /
  `MaxWeightText` (`W_Text_C`, native `TextWidget` with `GetText` D2:6893; one decimal). Player grid also
  `OwnerMoney`. `UUserWidget::GetWidgetFromName` is not a UFUNCTION in 5.5 and the native parents' widget members
  are not BP-visible, so the mod finds the texts by `GetPathName` among all `W_Text_C` widgets (path
  `...W_Inventory_C_n.WidgetTree.InventoryWidget.WidgetTree.WeightBar.WidgetTree.CurrentWeightText`).
- Traders: `W_Trade` (`TradeView : InventoryNew`, D2:6969, CoreVariables:946) with `IMC_Trade`.
- `PC.open_loot_menu` / `close_loot_menu` (D2:5313 / 5161) are native calls; the pawn BP implements neither.

## Signals
- Open: `EnhancedInputLocalPlayerSubsystem.HasMappingContext(IMC_Inventory)` (BlueprintCallable const in 5.5,
  `EnhancedInputSubsystemInterface.h:314`); `IMC_Inventory` = `EMappingContext::Inventory`, Exclusive
  (`InputMappingContextPrototypes.cfg:18-22`). Stack-split / right-click popups have their own Exclusive contexts and
  may drop it briefly: cross-check the view (`IsInViewport`, `IsVisible`).
- Backpack vs loot: `PC.IsUsingBackpack` (D2:5223); expected true only for the I key (to confirm in game).
- Corpse: target casts to `DeadBody` (D2:2514). Stash: owner is a stash BP (`BP_StashBackpack`, `BP_StashBag` →
  `BP_StaticItemContainer_C`; `BP_StashBigSafe` → `BP_SkeletalItemContainer_C`; `BP_IntChestItemContainer` →
  `BP_AnimatedItemContainer_C`), i.e. an `InteractableItemContainer`. Own stash: native `PlayerStash` (D2:5797), not
  an item container. Mutant: `MutantLootInteractionComponent`, no window by default.
- Taken: no BP weight / item count on `PC` / `Obj`; `CppMediator.get_items_count_in_inventory` needs a fixed SID.
  Weight texts (player up / loot down) cover click, drag, Take All, gamepad and partial stacks; money via
  `Obj.GetMoney` (D2:4901). `IA_UI_Inventory_LootTakeItem` / `TakeAllItems` bindings would miss drag and drop.

## To confirm in game (probe fields in `tools/probe/ImmLootProbe`)
IMC presence across backpack / loot / trade / popups, `IsUsingBackpack` in each, whether the target is still
valid after the window opens, one persistent `W_Inventory_C` or a new one per open, the raw weight texts per
action, whether the actor keeps ticking with the window open, money behaviour on corpses.
