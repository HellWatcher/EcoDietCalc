# Project Status

Last updated: 2026-02-09

## Current State

Phase 2 (Python Polish) complete. 150 tests, mypy clean. All modules now directly tested.
Phase 3 (C# Mod) — scaffold, read-only chat commands, JSON export, and **in-game meal planner** (Phase 1+2 of plan) implemented.
Domain naming standardized to match Eco game API (`fat`, `tastiness_*`, `balanced_diet_*`, TastePreference labels).

## Test Coverage

| Module                     | Coverage | Notes                                    |
| -------------------------- | -------- | ---------------------------------------- |
| `calculations.py`          | Good     | 11 tests covering SP, bonuses, variety   |
| `planner.py`               | Good     | 21 tests for ranking functions           |
| `integration`              | Good     | 16 tests for full planning pipeline      |
| `config.py`                | Good     | 9 tests for load, validation, merging    |
| `interface/cli.py`         | Good     | 7 tests for parser subcommands and flags |
| `interface/persistence.py` | Good     | 11+26 tests (load/save/log + import)     |
| `interface/prompts.py`     | Good     | 13 tests for all prompt functions        |
| `interface/render.py`      | Good     | 4 tests for display_meal_plan            |
| `main.py (cmd_predict)`    | Good     | 5 tests for predict subcommand           |
| `food_state_manager.py`    | Good     | 26 direct unit tests                     |

## Recent Changes (2026-02-09) — In-Game Meal Planner (C# Port)

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
- `/ecodiet config` command
- Tooltip/notification enhancement (Phase 4, needs API research)
- Suggested features: whatif, variety, exclude, auto-suggest, cost display

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

- **"Next bite" real-time mode**: Mod reads live stomach state and suggests what to eat next — natural fit for in-game integration since the mod has direct access to stomach contents via `Stomach.Contents` and events like `GlobalFoodEatenEvent`
- ~~**Export game state to JSON**~~: ✅ Implemented — `/ecodiet export` writes JSON, `python main.py plan --import <file>` consumes it

## Architecture Notes

- Entry: `main.py` dispatches to `cmd_plan`, `cmd_predict`, `cmd_reset`, `cmd_rate_unknowns`
- Config: `config.py` loads YAML, `constants.py` re-exports for backward compatibility
- Core: `planner.py` (bite selection) + `calculations.py` (SP math)
- Models: `Food` and `MealPlanItem` in `models/`
- State: `FoodStateManager` handles stomach, availability, persistence

## Session Log

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
