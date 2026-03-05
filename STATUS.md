# Project Status

Last updated: 2026-03-05

## Current State

Phase 2 (Python Polish) complete. 165 tests, mypy clean. All modules now directly tested.
Phase 3 (C# Mod) — scaffold, read-only chat commands, JSON export, **in-game meal planner**, **live stomach tooltip**, and **multi-source food discovery** implemented.
Domain naming standardized to match Eco game API (`fat`, `tastiness_*`, `balanced_diet_*`, TastePreference labels).
Balance-improvement bias added to planner — fixes zero-nutrient food selection bug.
Stomach tooltip now uses **native UILinks** — food names and store/container names are interactive (hover shows tooltip, click navigates). Falls back to styled text when references unavailable.
Multi-source discovery: backpack + authorized storage containers + nearby shops with currency/cost filtering.

## Test Coverage

| Module                     | Coverage | Notes                                    |
| -------------------------- | -------- | ---------------------------------------- |
| `calculations.py`          | Good     | 11 tests covering SP, bonuses, variety   |
| `planner.py`               | Good     | 26 tests for ranking functions           |
| `integration`              | Good     | 21 tests for full planning pipeline      |
| `config.py`                | Good     | 9 tests for load, validation, merging    |
| `interface/cli.py`         | Good     | 7 tests for parser subcommands and flags |
| `interface/persistence.py` | Good     | 11+26 tests (load/save/log + import)     |
| `interface/prompts.py`     | Good     | 13 tests for all prompt functions        |
| `interface/render.py`      | Good     | 4 tests for display_meal_plan            |
| `main.py (cmd_predict)`    | Good     | 5 tests for predict subcommand           |
| `food_state_manager.py`    | Good     | 26 direct unit tests                     |

## Recent Changes (2026-03-05) — Prebuilt DLL in GitHub Releases

### Added

- **GitHub Actions release workflow** — builds `EcoDietMod.dll` in Release config and uploads it as a release asset on `release` publish events
- **Un-gitignored `Eco.ModKit.dll`** (36KB) — allows CI to build without the full 14MB ModKit directory
- **`scripts/release-upload.sh`** — local fallback script for manual DLL build + upload
- **README install option** — "Download prebuilt DLL" added as recommended installation method

### Files

- `.github/workflows/release.yml` — new CI workflow
- `scripts/release-upload.sh` — new local script
- `mod/.gitignore` — negation pattern for `Eco.ModKit.dll`
- `README.md` — added prebuilt DLL install instructions

## Previous Changes (2026-03-05) — Fix First-Item UILink & Source Tracking

### Fixed

- **First backpack item loses UILink and source tracking** — `MealPlanner.PlanMeal()` mutated `discovery.Available` directly (decrementing counts, removing exhausted foods). Single-quantity foods removed during planning were missing from the dictionary at render time, causing `ResolveFoodLink` and `AssignToSourceGroups` to fail lookups. Fix: copy the `Available` dictionary before passing to the planner, preserving original discovery data for rendering.

### Changed

- `PlanTracker.cs` — `ComputeFreshPlan` now passes `new Dictionary<FoodCandidate, int>(discovery.Available)` instead of `discovery.Available` directly

### Build

- `dotnet build` clean with 0 errors (1 pre-existing CS0067 warning)

### Verification (in-game)

1. Hover stomach tooltip with single-quantity foods — first item shows UILink (icon + clickable name)
2. Move food from backpack to container → replan → source updates correctly
3. All items show correct source groups (not stuck under backpack)

## Previous Changes (2026-03-05) — C# Mod Code Rework

### Phase 1: Dead Code Removal (~400 lines deleted)

- Removed 10 dead methods from `PlanRenderer.cs` — `RenderPlan`, `RenderSourceGrouped`, `RenderFlat`, `RenderCompactSuggestion`, `RenderRemainingPlan` (string-based), `RenderRemainingItems`, `RenderSourceGroupedCompact`, `BuildTags`, `BuildColoredItemTags`, `BuildItemTags`
- Removed dead `Source` property from `MealPlanItem`

### Phase 2: PlanRenderer Restructure

- `PlanRenderer.cs` (698 lines) → split into 3 files:
  - `Rendering/TooltipRenderer.cs` (238 lines) — UILink tooltip rendering, renamed class
  - `Rendering/ItemGrouping.cs` (89 lines) — shared grouping/formatting utilities
  - `Models/ItemGroup.cs` (29 lines) — extracted data model
- Updated `EcoDietTooltipLibrary.cs` → `TooltipRenderer`
- Deleted `PlanRenderer.cs`

### Phase 3: PlanTracker Split

- Extracted `PlanStatus` enum → `Models/PlanStatus.cs` (13 lines)
- Extracted replan detection → `Tracking/ReplanDetector.cs` (165 lines)
- `PlanTracker.cs` reduced from 392 → 236 lines

### Phase 4: Model Modernization

- `MealPlanItem` → `sealed record` (positional constructor)
- `MealPlanResult` → `sealed record` (init properties, computed `SpGainTotal`)
- `SourceEntry` → `sealed record` (extracted to own file)
- `ShopFilter` → `sealed record` (extracted from `ShopDiscovery.cs`)
- `NutrientDensity` → `readonly record struct` with `.Sum` property
- Updated all callers (MealPlanner, FoodDiscovery, StorageDiscovery, ShopDiscovery)

### Phase 5: Thread Safety & Caching

- `DisplayConfig.Cache` → `ConcurrentDictionary` with `GetOrAdd` pattern
- `DiscoveryResult.HasMultipleSources` — cached after first access
- Added `PlannerConfig.Default` static instance, updated all callers

### Phase 6: Error Handling

- Added `Log.WriteWarningLineLocStr` (`Eco.Shared.Logging`) to 6 silent catch blocks:
  - `ShopDiscovery` (outer + inner), `StorageDiscovery` (outer), `DisplayConfig.Load`, `TooltipRenderer.ResolveSourceLink`, `TooltipRenderer.ResolveFoodLink`
- Kept `EcoDietTooltipLibrary` and `StorageDiscovery.IsAuthorized` catches silent (expected failure modes)

### Build

- `dotnet build` clean with 0 errors, 0 warnings
- 165 Python tests still pass
- All files under 300-line limit (max: SpCalculator.cs at 299)
- Total: 3,137 lines across 27 source files (down from 3,468 across 22)

### Verification (in-game)

1. Hover stomach tooltip — food/source UILinks render correctly (same behavior, new file structure)
2. Eat food → plan updates (ReplanDetector extracted correctly)
3. Config change → plan clears and recomputes
4. Multi-source tooltip → source group headers display

## Previous Changes (2026-03-04) — Rich Tooltip Links (UILink)

### Added

- **Native UILinks in stomach tooltip** — food names and source (store/container) names are now interactive inline links. Hovering shows the item/object tooltip, clicking navigates to it.
- `FoodCandidate.FoodType` — stores `System.Type` for food UILink resolution at render time via `Item.Get(type).UILink()`
- `SourceInfo.WorldObj` — stores `WorldObject?` reference for source UILink resolution via `worldObject.UILink()`
- `PlanRenderer.RenderRemainingPlanTooltip()` — new public entry point returning `LocString` with UILinks (parallel to existing TMP string path)
- `ResolveFoodLink()` / `ResolveSourceLink()` — UILink resolution helpers with graceful fallback to styled text

### Changed

- `StomachSnapshot.FoodItemToCandidate()` — passes `foodItem.GetType()` as `FoodType`
- `StorageDiscovery` / `ShopDiscovery` — pass `WorldObject` reference through to `SourceInfo`
- `EcoDietTooltipLibrary` — calls `RenderRemainingPlanTooltip()` (LocString) instead of `RenderRemainingPlan()` (string), passes content directly to `TooltipSection` without `Localizer.DoStr()` wrapping

### Build

- `dotnet build` clean with 0 errors (1 pre-existing CS0067 warning)
- 165 Python tests still pass

### Verification (in-game)

1. Hover stomach tooltip — food names show as interactive UILinks (icon + clickable name)
2. Hover stomach tooltip (multi-source) — store/container names show as UILinks, "backpack" as plain text
3. Click a food UILink — opens food item tooltip
4. Click a store UILink — opens store/world object tooltip
5. Edge cases (no food, full, complete) — styled status messages, no crashes
6. Fallback: foods/sources without Eco object references render as styled plain text

## Previous Changes (2026-03-01) — Fix Boolean ViewEditor Persistence

### Fixed

- **Boolean config settings (Compact, Sources, Tags) now persist** — `[Autogen]` IL weaver generates a client-only checkbox for `bool` that never fires `[AutoRPC]` RPCs. Workaround: expose booleans as `int` (0/1) properties to force text-input widgets that do fire RPCs. Convenience `bool` accessors maintain clean usage in code.
- **Discovery radius server cap removed** — player-configurable radius used directly.

### Changed

- `DisplayConfigViewModel.cs` — `bool` → `int` (0/1) for Compact/Sources/Tags; added `[Serialized]` on class, `INotifyPropertyChanged`
- `PlannerConfig.cs` — `DiscoveryRadiusMeters` default 100→99999, `PositionReplanThresholdMeters` default 20→1
- `FoodDiscovery.cs` — removed `Math.Min` server cap on radius
- `.gitignore` — exclude decompiled API reference

### Build

- `dotnet build` clean with 0 warnings, 0 errors (1 expected CS0067 warning for unused event)

### Failed approaches (logged in learned skills)

1. `[Autogen, AutoRPC]` auto-property — renders, doesn't persist
2. `[Serialized, Autogen, AutoRPC]` — renders, doesn't persist
3. ChatSettings pattern (no `[Autogen]`) — doesn't render
4. `[Autogen]` + explicit `[RPC] Set*` methods — renders, doesn't persist
5. `enum Toggle { Off, On }` — broken picker widget
6. **`int` (0/1) ✓** — renders as text input, persists via RPC

## Previous Changes (2026-02-27) — Config Booleans Cleanup & Meaningful Compact Mode

### Removed

- **AutoPlan dead stub** — deleted `AutoPlan` property from `DisplayConfig.cs`, `DisplayConfigViewModel.cs`, `ConfigEditor.cs`, and `DietCommands.cs` CLI switch. Zero references remain.

### Changed

- **Tags default → false** — `DisplayConfig.Tags` no longer defaults to `true`; new players start without scoring tags
- **Meaningful compact mode** — `compact=true` now strips SP gain, running SP total, and all tags from every render path (chat flat, chat source-grouped, tooltip flat, tooltip source-grouped). Lines show only `{Name} x{Count} ({Cal} cal)`. Summary footer still hidden too.
- `PlanRenderer.cs` — added `compact` parameter to `RenderFlat`, `RenderSourceGrouped`, `RenderSourceGroupedCompact`, `RenderRemainingPlan`, `RenderRemainingItems`; when true, emits short `name (cal)` lines
- `EcoDietTooltipLibrary.cs` — passes `displayConfig.Compact` to `RenderRemainingPlan`
- `DietCommands.cs` — removed `autoplan` from CLI help text and valid keys list

### Build

- `dotnet build` clean with 0 warnings, 0 errors

### Verification (in-game)

1. `/ed plan` → should NOT show tags by default (Tags=false)
2. `/ed config compact true` → `/ed plan` → per-bite lines show only food + calories
3. `/ed config compact false` → `/ed plan` → full output with SP + summary
4. `/ed config autoplan true` → should be unrecognized (removed)
5. Hover stomach with compact=true → tooltip shows short lines

## Previous Changes (2026-02-27) — Fix Tooltip Freeze After Config Save

### Fixed

- **Tooltip freeze after config save** — `InvalidatePlan` sets `IsStale=true`, but `DetectReplanReason` requires a stomach diff to proceed; config changes produce no diff, so the plan stayed frozen forever. Added `PlanTracker.ClearPlan(User)` which removes the cached plan entirely, forcing a fresh compute on next tooltip render.
- **Misleading "closed without saving" message** — `onClose` callback fires on ALL window-close paths including after save; `saved` flag race wasn't reliable. Removed `onClose` and `saved` flag entirely. `onBack` still handles explicit cancel.
- **No save confirmation** — added `"Settings saved."` message after successful config persist.

### Changed

- `PlanTracker.cs` — added `ClearPlan(User)` method (removes cached plan via `Plans.Remove`)
- `ConfigEditor.cs` — replaced `InvalidatePlan` → `ClearPlan`; removed `onClose`/`saved` flag; added success message

### Build

- `dotnet build` clean with 0 warnings, 0 errors

### Verification (in-game)

1. `/ed config` → toggle Compact → Save → "Settings saved." in chat, NO misleading close message
2. Hover stomach → tooltip reflects new setting immediately (fresh plan)
3. `/ed config` → close via X → no message (correct — X is neither save nor cancel)
4. Eat a food → plan updates normally (`InvalidatePlan` still works for food events)

## Previous Changes (2026-02-26) — Config Editor Fix: Save, Cancel, Currencies, Tooltips, Radius

### Changed

- `DisplayConfigViewModel.cs` — replaced auto-properties with backing fields + manual `PropertyChanged?.Invoke()` (Fody doesn't run on mod assemblies). Replaced `Currencies` string with `GamePickerList` currency picker. Updated all `LocDescription` tooltips with explanatory text.
- `ConfigEditor.cs` — added `onClose` and `onBack` callbacks for cancel feedback. Updated `CreateViewModel` to populate `GamePickerList` from saved currency names via `CurrencyManager.GetClosestCurrency`. Updated `ApplyAndSave` to extract currencies via `GetObjects<Currency>()` and removed discovery radius server cap (only clamp minimum to 1).
- `FoodDiscovery.cs` — removed `Math.Min` server cap on discovery radius; player-configurable radius is now used directly.
- `DietCommands.cs` — removed server cap from `/ed config maxdistance` CLI path; validates > 0 only.
- `PlannerConfig.cs` — `DiscoveryRadiusMeters` default changed from 100f to 99999f (effectively unlimited).
- `DisplayConfig.cs` — `MaxDiscoveryRadius` default changed from 100f to 99999f.

### Build

- `dotnet build` clean with 0 warnings, 0 errors

### Verification (in-game)

1. `/ed config` → opens single window, tooltips are descriptive
2. Toggle Compact → Save → `/ed config compact` confirms value persisted
3. Currency picker → shows game currencies → select → Save → next `/ed plan` filters
4. Close via X → "Config editor closed without saving." message
5. `/ed config maxdistance 500` → accepted without cap message
6. `/ed config compact true` → CLI mode still works

## Previous Changes (2026-02-26) — Single-Window Config Editor (ViewEditor)

### Added

- `mod/EcoDietMod/Config/DisplayConfigViewModel.cs` (~41 lines) — transient IController ViewModel with [SyncToView] attributed properties
  - `Compact`, `Sources`, `Tags`, `AutoPlan` (bool), `Currencies` (string, comma-separated), `MaxCostPer1000Cal`, `MaxDiscoveryRadius` (float)
  - `List<string> ShopCurrencyFilter` flattened to comma-separated string — ViewEditor has no native List\<string\> control

### Changed

- `mod/EcoDietMod/Config/ConfigEditor.cs` (~85 lines, down from ~190) — rewrote to use ViewEditor single-window API
  - `EditInteractive(User)` — creates ViewModel, calls `ViewEditor.Edit` (fire-and-forget)
  - `CreateViewModel(DisplayConfig)` — populate ViewModel from config
  - `ApplyAndSave(ViewModel, Config, User)` — onSubmit: validate, copy back, persist
  - Validation: booleans pass-through, currencies split/trim, cost clamped to 0+, radius clamped to [1, serverCap]
- `DietCommands.cs` — `Config()` changed from `async Task` back to `void` (ViewEditor.Edit is fire-and-forget)
  - Removed `using System.Threading.Tasks`
  - `/ed config <key> <value>` CLI mode preserved unchanged

### Build

- `dotnet build` clean with 0 warnings, 0 errors
- 165 Python tests still pass

### Eco APIs Used

- `ViewEditor.Edit(User, IController, onSubmit, buttonText, overrideTitle, windowType)` — single-window property editor
- `IController` : `IViewController`, `IHasUniversalID` — interface for editable objects
- `[SyncToView]`, `[Autogen]` (`Eco.Core.Controller`) — marks property as visible in editor
- `[AutogenClass]` (`Eco.Core.Controller`) — auto-generates UI for class
- `[LocDisplayName]`, `[LocDescription]` (`Eco.Shared.Localization`) — field label and tooltip

### Superseded: Multi-window OptionBox loop

Previous approach (OptionBox menu → per-setting popup → back) rejected after in-game testing — too many windows. ViewEditor.Edit renders all settings in one panel.

### Risks (to verify in-game)

- ViewEditor may not render mod IController types — may need additional attributes or registration
- If `WindowType.Small` is too cramped for 7 fields, switch to `WindowType.Simple`
- If Fody doesn't inject PropertyChanged for mod types, add manual raising in setters

## Previous Changes (2026-02-26) — Source-Grouped Tooltip Rendering

### Changed

- `PlanTracker.cs` — store `DiscoveryResult` in `ActivePlan`; extracted `GetRemainingItemsInternal`; added `GetRemainingPlanContext` for tooltip callers needing source data
- `PlanRenderer.cs` — extracted `AssignToSourceGroups` shared helper from `RenderSourceGrouped`; added `RenderSourceGroupedCompact` for tooltip; `RenderRemainingPlan` now accepts optional `discovery`/`showSources`/`showTags` and dispatches to source-grouped or enhanced flat rendering
- `EcoDietTooltipLibrary.cs` — loads `DisplayConfig` for player preferences; calls `GetRemainingPlanContext` and passes source/tag preferences to renderer

### Tooltip format (multi-source)

```
--- EcoDiet: 5 bites → +8.50 SP ---
--- From [backpack] ---
  → Corn x2 (300 cal) +3.20 SP → 18.40  [variety +2pp]
  · Tomato (150 cal) +1.80 SP → 20.20
--- From [Refrigerator @ 15m] ---
  · Beet x2 (240 cal) +3.50 SP → 23.70  [craving]
```

### Tooltip format (single-source, enhanced)

```
--- EcoDiet: 3 bites → +5.00 SP ---
  → Corn x2 (300 cal) +3.20 SP → 18.40  [variety +2pp]
  · Tomato (150 cal) +1.80 SP → 20.20
```

### Build

- `dotnet build` clean with 0 warnings, 0 errors
- In-game verified: tooltip renders source groups, updates on eat, updates on player movement (20m+ threshold)

## Previous Changes (2026-02-25) — Multi-Source Food Discovery

### Added

- `mod/EcoDietMod/Discovery/ShopDiscovery.cs` — discovers food for sale at nearby shops, filtered by distance, currency, and cost-per-calorie
- `mod/EcoDietMod/Discovery/StorageDiscovery.cs` — discovers food from authorized storage containers within range
- `mod/EcoDietMod/Discovery/DiscoveryMerger.cs` — merges multiple DiscoveryResult sources
- `mod/EcoDietMod/Models/DiscoveryResult.cs` — food availability + source tracking container
- `mod/EcoDietMod/Models/SourceInfo.cs` — source metadata (kind, name, distance, price, currency)
- `DisplayConfig.MaxDiscoveryRadius` — player-configurable discovery radius (capped by server PlannerConfig)
- `/ed config maxdistance <meters>` command
- PlannerConfig: `EnableStorageDiscovery`, `EnableShopDiscovery`, `DiscoveryRadiusMeters`, `PositionReplanThresholdMeters`
- PlanTracker: player movement detection triggers replan when food sources may have changed

### Fixed (build errors from previous session)

- `StoreComponent` namespace: `Eco.Gameplay.Components.Store` (not `.Components` alone)
- `StorageComponent` namespace: `Eco.Gameplay.Components.Storage`
- `Vector3` source: `System.Numerics` (not `Eco.Shared.Math`)
- `WorldObjectManager.GetWorldObjectsWithComponent<T>()` doesn't exist → rewrote to `WorldObjectManager.ForEach()` with `GetComponent<T>()` filtering
- `AuthManager.IsAuthorized()` static call → `worldObject.Auth?.IsAuthorizedConsumerAccess(user.Player)` via AuthComponent
- `TradeOffer.Currency` doesn't exist → use `StoreComponent.CurrencyName` (currency is per-store)
- `WorldObject.DisplayName` returns `LocString` not `string` → added `.ToString()` conversion

### Build

- `dotnet build` clean with 0 warnings, 0 errors (both Debug and Release)
- 165 Python tests still pass

### Known Gaps

- ~~**Tooltip needs source groupings and distances**~~ ✅ Fixed — tooltip now shows source-grouped items with calories, running SP, and tags
- ~~**Tooltip tag display (polish)**~~ ✅ Fixed — variety/taste/craving tags shown in tooltip, controlled by `DisplayConfig.Tags`

## Previous Changes (2026-02-12) — Live Stomach Tooltip

### Added

- `mod/EcoDietMod/Tracking/PlanTracker.cs` — in-memory plan cache per player with progress detection (on-plan filtering, off-plan replan, calorie drain replan)
- `mod/EcoDietMod/Tracking/EcoDietEventHandler.cs` — `IModInit` subscribing to `Stomach.GlobalFoodEatenEvent` to invalidate plans on eat
- `PlanRenderer.RenderRemainingPlan()` — tooltip countdown format with `→`/`·` markers and edge states (no food, stomach full, plan complete)

### Changed

- `EcoDietTooltipLibrary.cs` — fixed tooltip registration: extension method pattern (`this Stomach`), `CacheAs.Disabled`, wired to PlanTracker → PlanRenderer pipeline
- `PlanRenderer.GroupItems` + `ItemGroup` visibility changed from `private` to `internal` for reuse
- `SPEC.md` — updated C# architecture section with Tracking/ directory and tooltip system docs
- `CLAUDE.md` — added C# mod structure section

### Build

- `dotnet build` clean with 0 warnings, 0 errors
- 165 Python tests still pass

## Previous Changes (2026-02-12) — Balance Improvement Bias

### Added

- `_balance_improvement_bias()` in `planner.py` — positive nudge for foods that improve the balanced-diet ratio, wired into Pass 1 and Pass 3 of `_choose_next_bite()`
- `BalanceImprovementBias()` in C# `BiteSelector.cs` + `BalancedDietImprovementStrength` in `PlannerConfig.cs`
- 5 unit tests (`TestBalanceImprovementBias`) + 5 integration tests (`TestBalanceImprovementIntegration`) parametrized over all four nutrients
- 165 tests pass, mypy clean, C# build 0 warnings

### Fixed

- Zero-nutrient food selection bug: when stomach had a zeroed-out nutrient (e.g., fat=0 from eating only Pumpkins), planner picked more zero-nutrient foods instead of balance-fixing ones. Root cause: `_low_calorie_penalty` overwhelmed the genuine SP benefit of balance-fixing foods.

### Removed

- `repro_zero_nutrient.py` — replaced by proper test coverage

## Previous Changes (2026-02-11) — SP Calculation Fix

### Fixed

- **Balanced diet ratio included zeros**: `calculate_balanced_diet_ratio` now uses `min(nutrients)` instead of `min_nonzero(nutrients)`. A zero nutrient (e.g. fat=0 in Pumpkin) was being excluded, making the diet look more balanced than the game calculates. Fixed in both Python (`calculations.py`) and C# (`SpCalculator.cs`).
- **Float truncation in C# mod**: `FoodCandidate` nutrients and calories changed from `int` to `float` to match Eco API precision. Removed `(int)` casts in `StomachSnapshot.FoodItemToCandidate()` and `GameStateExporter`.

### Verified

- Pumpkin scenario (6 pumpkins, fat=0): mod now calculates SP=16.0, matching game's `NutrientSkillRate=16`
- Game's `BalancedDietMult=0.5` corresponds to ratio=0, pp=-50, multiplier=0.5

### Added

- 5 new tests: `test_balanced_diet_ratio_includes_zero_nutrients`, `test_balanced_diet_bonus_with_zero_nutrient`, `test_balanced_diet_ratio_all_equal`, `test_balanced_diet_ratio_all_zero`, `test_sp_matches_game_pumpkin_scenario`
- 155 tests pass, mypy clean, C# build 0 warnings

### Open Questions

- **Variety multiplier**: Game shows Variety=1.0 (no bonus) with 1 food type at 2040 cal, but our formula gives a small bonus (1.9 pp) for 1 qualifying food. Needs investigation — game may require 2+ foods or use remaining stomach calories for threshold.
- **Balance range**: Our formula gives [-50, +50] pp. Game max might be [0.5, 1.0] multiplier (i.e., no positive bonus for perfect balance). Needs testing with balanced diet.

## Previous Changes (2026-02-09) — In-Game Meal Planner (C# Port)

### Added

- `mod/EcoDietMod/Models/FoodCandidate.cs` — immutable food record with equality by name
- `mod/EcoDietMod/Models/MealPlanItem.cs` — single planned bite with scoring details
- `mod/EcoDietMod/Models/MealPlanResult.cs` — full plan result with summary stats
- `mod/EcoDietMod/Config/PlannerConfig.cs` — algorithm constants (defaults from config.default.yml)
- `mod/EcoDietMod/Algorithm/SpCalculator.cs` — port of calculations.py (SP math, bonuses, variety, tastiness)
- `mod/EcoDietMod/Algorithm/BiteSelector.cs` — port of planner.py ranking pipeline (biases, penalties, bite selection)
- `mod/EcoDietMod/Algorithm/MealPlanner.cs` — port of plan_meal loop with craving-first strategy
- `mod/EcoDietMod/Discovery/StomachSnapshot.cs` — reads User.Stomach into FoodCandidate dicts
- `mod/EcoDietMod/Discovery/FoodDiscovery.cs` — enumerates food from player backpack
- `mod/EcoDietMod/Rendering/PlanRenderer.cs` — formats plan for chat output

### Changed

- `mod/EcoDietMod/DietCommands.cs` — added `/ecodiet plan [calories]` and `/ecodiet fullplan` subcommands

### Build

- `dotnet build` clean with 0 warnings, 0 errors
- 150 Python tests still pass

### Architecture Decisions

- No FoodStateManager in C# — planner takes `Dictionary<FoodCandidate, int>` directly from live API
- PlannerConfig passed explicitly — no static globals
- FoodCandidate is immutable — counts in separate dictionaries
- JSON config (System.Text.Json) — no new NuGet dependencies

### Not Yet Implemented (Phase 3+4 from plan)

- Extended food discovery (authorized storage, nearby shops)
- Per-player JSON config persistence (ConfigStore, PlayerConfig)
- ~~Tooltip/notification enhancement~~ ✅ Live stomach tooltip with plan countdown
- Suggested features: whatif, variety, exclude, cost display

## Previous Changes (2026-02-08) — Type Annotations + Unit Tests

### Added

- `tests/test_food_state_manager.py` — 26 direct unit tests covering all FoodStateManager methods (get_food, consume, can_consume, unique_variety_foods, all_available, reset_stomach, reset_availability, reset_tastiness, to_json_ready, get_current_sp)

### Changed

- `tune/tuner.py` — added type annotations to 7 unannotated functions (`override_constants`, `suppress_interactive_prompts`, `_always_no`, `_filtered_print`, `reload_deps`, `sample_theta`/`samp`, `main`); removed stale `# type: ignore` on persistence import
- 150 tests pass, mypy clean

## Previous Changes (2026-02-08) — Naming Standardization

### Changed

- Renamed all domain terms to match Eco game API: `fats` → `fat`, `taste_*` → `tastiness_*`, `balance_*` → `balanced_diet_*`
- Tastiness labels aligned with `TastePreference` enum: `"hated"` → `"worst"`, `"neutral"` → `"ok"`, `"great"` → `"delicious"`
- Updated all Python files (models, calculations, planner, config, constants, main, interface, tests), C# mod export, food_state.json, and docs
- Backward-compatible JSON loading: `Food.from_dict()` accepts both `"Fat"` and `"Fats"` keys
- 124 tests pass, mypy clean

## Previous Changes (2026-02-07) — JSON Export Pipeline

### Added

- `mod/EcoDietMod/GameStateExporter.cs` — exports player diet state (foods, stomach, cravings, multipliers, calories) to JSON using `System.Text.Json`
- `/ecodiet export [note]` chat subcommand — writes timestamped JSON to `Mods/EcoDietMod/exports/`
- `load_game_state_export()` in `interface/persistence.py` — reads mod-exported JSON into `FoodStateManager` + cravings/calories/multipliers
- `--import` flag on `plan` subcommand — bypasses interactive prompts, uses mod-exported game state
- `tests/test_import.py` — 26 tests covering import pipeline, cravings parsing, tastiness mapping, error cases

### Discovered (Eco API)

- `TastePreference` is a **nested enum** inside `ItemTaste` struct (not a standalone type): `ItemTaste.TastePreference`
- Actual enum values: `Worst`, `Horrible`, `Bad`, `Ok`, `Good`, `Delicious`, `Favorite` (not Terrible/Great as documented elsewhere)

## Previous Changes (2026-02-07) — Mod Runtime Fixes

### Fixed

- Target framework `net9.0` → `net8.0` — Eco 0.12 runs on .NET 8.0, net9.0 caused `ReflectionTypeLoadException`
- Chat command alias `diet` → `ecodiet` — Eco has a built-in `/diet` command, duplicate key crashed `ChatCommandService`
- Method name `EcoDiet` → `EcoDietRoot` — Eco registers both method name and alias as keys; same name (case-insensitive) caused duplicate key

### Confirmed Working

- Mod loads on Eco 0.12 server without errors
- Commands available as `/ecodiet stomach`, `/ecodiet nutrients`, `/ecodiet cravings`, `/ecodiet taste`, `/ecodiet multipliers`

## Previous Changes (2026-02-07) — C# Mod Scaffold

### Added

- `mod/EcoDietMod/` — C# class library targeting net8.0 with `Eco.ReferenceAssemblies` NuGet package
- `mod/EcoDietMod/DietCommands.cs` — 5 read-only chat commands (`/ecodiet stomach`, `/ecodiet nutrients`, `/ecodiet cravings`, `/ecodiet taste`, `/ecodiet multipliers`)
- `mod/.gitignore` — excludes build artifacts
- Serena memory `eco-mod-api-surface.md` — documents Eco API types for food/diet

### Discovered (Eco API Surface)

- `User.Stomach` provides direct access to `Contents`, `Nutrients`, `Calories`, all SP multipliers
- `StomachEntry` has `Food` (FoodItem) and `TimeEaten` (double)
- `TasteBuds.FoodToTaste` maps food types to `ItemTaste` (7-level preference enum + multiplier)
- `Cravings` class has `GetMult()`, `IsCravingFood()`, config statics
- `Stomach` has events (`GlobalFoodEatenEvent`, `CravingSatisfiedEvent`) useful for future real-time mode
- Chat command pattern: `[ChatCommandHandler]` class + `[ChatCommand]`/`[ChatSubCommand]` methods

## Previous Changes (2026-02-07) — Craving System Cleanup

### Removed

- `can_be_craving()` and `normalized_cravings()` from `calculations.py` — game provides craving info directly
- Per-bite craving match bonus (`CRAVING_BONUS_PP`, `CRAVING_MAX_COUNT`) from calculations, constants, config
- `CRAVING_MIN_CALORIES`, `CRAVING_MIN_TASTINESS`, `CRAVING_MIN_NUTRIENT_SUM` from constants, config, config.default.yml
- 3 tests for removed craving match logic (`test_calculations.py`)
- Craving match display from `cmd_predict` output (`main.py`)

### Kept

- `CRAVING_SATISFIED_FRAC` (10% per satisfied craving) — still used in SP formula
- Planner craving prioritization flow (`_pick_feasible_craving`, `update_cravings`)
- `MealPlanItem.craving` field for plan output

### Updated

- `SPEC.md`, `docs/FORMULAS.md`, `docs/TEST_PROTOCOL.md` — removed craving eligibility docs, renumbered tests (T1-T9)
- `.gitignore` — added `.ruff_cache/`

## Previous Changes (2026-02-07) — Phase 2: Python Polish

### Bug Fixes

- Fixed escaped `\\n` (literal backslash-n) in `interface/persistence.py:log_data_issues()` — 8 f-string writes now use real newlines
- Fixed mutable default argument `cravings: list[str] = []` → `cravings: list[str] | None = None` in `food_state_manager.py:get_current_sp()`

### Test Infrastructure

- Consolidated `make_food()` helper from `test_planner.py` and `test_integration.py` into `tests/conftest.py`

### New Test Files

- `tests/test_config.py` — 9 tests for config loading, validation, merging, missing files
- `tests/test_cli.py` — 7 tests for CLI argument parser
- `tests/test_persistence.py` — 11 tests for JSON I/O, data integrity logging, load_food_state
- `tests/test_prompts.py` — 13 tests for interactive prompt functions
- `tests/test_render.py` — 4 tests for meal plan display
- `tests/test_cmd_predict.py` — 5 tests for predict subcommand

### Type Annotations

- Added type hints to `Food.__init__` parameters
- Added return types to `prompts.py` functions (`prompt_for_cravings_satisfied`, `prompt_for_tastiness`, `collect_user_constraints`)
- Added `-> None` return types to all test methods in `test_planner.py` and `test_integration.py`
- Fixed type error in `prompt_for_tastiness` (variable shadowing `str`/`int`)

## Previous Changes (2026-02-01)

### New Files

- `tests/test_planner.py` — Unit tests for `_low_calorie_penalty`, `_soft_variety_bias`, `_proximity_bias`, `_choose_next_bite`
- `tests/test_integration.py` — Integration tests for full plan generation, availability limits, multipliers, edge cases
- `config.py` — Config loader with dataclasses and YAML support
- `config.default.yml` — Default configuration with all tunable constants

### Modified Files

- `constants.py` — Now loads values from config file
- `interface/cli.py` — Added `--config` flag for custom config
- `main.py` — Early config detection for CLI `--config` flag
- `planner.py` — Added type annotation for `meal_plan`

## Configuration

Constants are now externalized to `config.default.yml`. To customize:

```bash
# Use defaults
python main.py plan

# Use custom config
python main.py --config my_config.yml plan
```

Config structure:

- `algorithm.*` — Tuner-derived ranking parameters
- `game_rules.*` — Game mechanics constants (variety threshold, cravings)
- `safety.*` — Iteration limits, base SP
- `display.*` — Rendering thresholds

## Known Gaps

- [x] ~~`cmd_predict` untested~~ — 5 tests added
- [x] ~~Interface modules (`interface/*`) have no tests~~ — all covered
- [x] ~~No edge case tests for config validation errors~~ — 9 tests added
- [x] ~~`tune/tuner.py` has no type annotations~~ — 7 functions annotated
- [x] ~~`food_state_manager.py` only tested indirectly~~ — 26 direct unit tests

## Feature Ideas

- ~~**"Next bite" real-time mode**~~: ✅ Implemented — stomach tooltip shows remaining plan, auto-replans on eat and calorie drain
- ~~**Export game state to JSON**~~: ✅ Implemented — `/ecodiet export` writes JSON, `python main.py plan --import <file>` consumes it

## Architecture Notes

- Entry: `main.py` dispatches to `cmd_plan`, `cmd_predict`, `cmd_reset`, `cmd_rate_unknowns`
- Config: `config.py` loads YAML, `constants.py` re-exports for backward compatibility
- Core: `planner.py` (bite selection) + `calculations.py` (SP math)
- Models: `Food` and `MealPlanItem` in `models/`
- State: `FoodStateManager` handles stomach, availability, persistence

## Session Log

- 2026-03-05: Prebuilt DLL releases — GitHub Actions workflow builds and uploads EcoDietMod.dll on release; un-gitignored Eco.ModKit.dll for CI; local release-upload.sh script; README install instructions
- 2026-03-05: Fix first-item UILink/source tracking — copy Available dict before planner mutation preserves discovery data for rendering
- 2026-03-05: C# mod code rework — dead code removal, PlanRenderer→TooltipRenderer split, PlanTracker split, model modernization (records), thread safety, error handling logging
- 2026-03-04: Rich tooltip links — food and source names are native UILinks (hover/click), FoodType on FoodCandidate, WorldObj on SourceInfo, new LocString tooltip render path. Released v0.7.0
- 2026-03-01: Fix boolean ViewEditor persistence — [Autogen] bool checkbox never fires RPCs; workaround: expose as int (0/1) for text-input widget. 7 approaches tested, 1 worked. Released v0.6.0
- 2026-02-27: Config booleans cleanup — Tags default false, removed AutoPlan dead stub, meaningful compact mode (strips SP/tags from all render paths)
- 2026-02-27: Fix tooltip freeze after config save — added ClearPlan (removes cached plan), removed onClose/saved flag, added save confirmation message
- 2026-02-26: Single-window config editor — ViewEditor.Edit replaces multi-popup OptionBox loop, DisplayConfigViewModel with [SyncToView] properties, DietCommands.Config() back to void
- 2026-02-26: (superseded) Interactive config popup — ConfigEditor.cs with OptionBox/InputString dialogs, rejected after in-game testing
- 2026-02-26: Source-grouped tooltip — stored DiscoveryResult in ActivePlan, extracted AssignToSourceGroups, added RenderSourceGroupedCompact, tooltip now matches /ed plan format with source headers, calories, running SP, tags
- 2026-02-12: Live stomach tooltip — PlanTracker (plan cache + progress detection), EcoDietEventHandler (food eaten events), RenderRemainingPlan, fixed tooltip registration to extension method pattern
- 2026-02-12: Balance improvement bias — added `_balance_improvement_bias` to planner, C# mirror, 10 new tests, deleted repro script, released v0.5.0
- 2026-02-08: Type annotations + unit tests — tuner.py annotated, 26 new food_state_manager tests, 150 total tests
- 2026-02-08: Naming standardization — aligned all domain naming with Eco game API (fat, tastiness*\*, balanced_diet*\*, TastePreference labels)
- 2026-02-07: JSON export pipeline — GameStateExporter.cs, /ecodiet export command, Python --import flag, 26 new tests
- 2026-02-07: Mod runtime fixes — net8.0 target, /ecodiet command rename, confirmed working on Eco 0.12
- 2026-02-07: C# mod scaffold — created mod/EcoDietMod with read-only chat commands, explored Eco API surface
- 2026-02-07: Craving cleanup — removed eligibility system (can*be_craving, CRAVING_MIN*\*, per-bite match bonus), kept satisfied frac and planner flow
- 2026-02-07: Phase 2 Python Polish — 2 bug fixes, 6 new test files (49 tests), type annotations, test helper consolidation
- 2026-02-06: Rewrote README — fixed project name to EcoDietCalc, added full usage/config/layout docs
- 2026-02-06: Cleaned up gitignore, CLAUDE.md, added CHANGELOG.md (previous sessions)
- 2026-02-01: Added planner tests, integration tests, config file system
- 2026-02-01: Created STATUS.md for efficient context loading
