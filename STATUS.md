# Project Status

Last updated: 2026-02-01

## Current State

Core meal planning algorithm is complete and working. Recent work focused on:
- Added comprehensive unit tests for planner ranking functions
- Added integration tests for full meal planning pipeline
- Externalized tunable constants to YAML config file

## Test Coverage

| Module | Coverage | Notes |
|--------|----------|-------|
| `calculations.py` | Good | 14 tests covering SP, bonuses, variety |
| `planner.py` | Good | 21 tests for ranking functions |
| `integration` | Good | 16 tests for full planning pipeline |
| `interface/*` | None | CLI, prompts, persistence, render untested |
| `food_state_manager.py` | Partial | Used in integration tests |

## Recent Changes (2026-02-01)

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

- [ ] `cmd_predict` untested (useful for validation)
- [ ] Interface modules (`interface/*`) have no tests
- [ ] No edge case tests for config validation errors

## Feature Ideas

- **Multi-meal planning**: Daily/weekly plans with nutrient targets
- **Export formats**: CSV/JSON output for meal plans
- **Food categories**: Breakfast/lunch/dinner/snack classification

## Architecture Notes

- Entry: `main.py` dispatches to `cmd_plan`, `cmd_predict`, `cmd_reset`, `cmd_rate_unknowns`
- Config: `config.py` loads YAML, `constants.py` re-exports for backward compatibility
- Core: `planner.py` (bite selection) + `calculations.py` (SP math)
- Models: `Food` and `MealPlanItem` in `models/`
- State: `FoodStateManager` handles stomach, availability, persistence

## Session Log

- 2026-02-01: Added planner tests, integration tests, config file system
- 2026-02-01: Created STATUS.md for efficient context loading
