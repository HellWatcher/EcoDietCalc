# Project Status

Last updated: 2026-02-07

## Current State

Phase 2 (Python Polish) complete. 98 tests, mypy clean. All interface modules now tested.
Phase 3 (C# Mod) started — scaffold and read-only chat commands in place.

## Test Coverage

| Module                     | Coverage | Notes                                    |
| -------------------------- | -------- | ---------------------------------------- |
| `calculations.py`          | Good     | 11 tests covering SP, bonuses, variety   |
| `planner.py`               | Good     | 21 tests for ranking functions           |
| `integration`              | Good     | 16 tests for full planning pipeline      |
| `config.py`                | Good     | 9 tests for load, validation, merging    |
| `interface/cli.py`         | Good     | 7 tests for parser subcommands and flags |
| `interface/persistence.py` | Good     | 11 tests for read/save/log/load          |
| `interface/prompts.py`     | Good     | 13 tests for all prompt functions        |
| `interface/render.py`      | Good     | 4 tests for display_meal_plan            |
| `main.py (cmd_predict)`    | Good     | 5 tests for predict subcommand           |
| `food_state_manager.py`    | Partial  | Used in integration tests                |

## Recent Changes (2026-02-07) — C# Mod Scaffold

### Added

- `mod/EcoDietMod/` — C# class library targeting net9.0 with `Eco.ReferenceAssemblies` NuGet package
- `mod/EcoDietMod/DietCommands.cs` — 5 read-only chat commands (`/diet stomach`, `/diet nutrients`, `/diet cravings`, `/diet taste`, `/diet multipliers`)
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
- [ ] `tune/tuner.py` has no type annotations (annotation-unchecked warning)
- [ ] `food_state_manager.py` only tested indirectly via integration tests

## Feature Ideas

- **"Next bite" real-time mode**: Mod reads live stomach state and suggests what to eat next — natural fit for in-game integration since the mod has direct access to stomach contents via `Stomach.Contents` and events like `GlobalFoodEatenEvent`
- **Export game state to JSON**: Mod writes stomach/nutrient/craving data to JSON for the Python planner to consume — bridge approach before full C# port

## Architecture Notes

- Entry: `main.py` dispatches to `cmd_plan`, `cmd_predict`, `cmd_reset`, `cmd_rate_unknowns`
- Config: `config.py` loads YAML, `constants.py` re-exports for backward compatibility
- Core: `planner.py` (bite selection) + `calculations.py` (SP math)
- Models: `Food` and `MealPlanItem` in `models/`
- State: `FoodStateManager` handles stomach, availability, persistence

## Session Log

- 2026-02-07: C# mod scaffold — created mod/EcoDietMod with read-only chat commands, explored Eco API surface
- 2026-02-07: Craving cleanup — removed eligibility system (can*be_craving, CRAVING_MIN*\*, per-bite match bonus), kept satisfied frac and planner flow
- 2026-02-07: Phase 2 Python Polish — 2 bug fixes, 6 new test files (49 tests), type annotations, test helper consolidation
- 2026-02-06: Rewrote README — fixed project name to EcoDietCalc, added full usage/config/layout docs
- 2026-02-06: Cleaned up gitignore, CLAUDE.md, added CHANGELOG.md (previous sessions)
- 2026-02-01: Added planner tests, integration tests, config file system
- 2026-02-01: Created STATUS.md for efficient context loading
