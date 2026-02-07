# Changelog

All notable changes to EcoDietMaker are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- C# mod scaffold (`mod/EcoDietMod/`) targeting net8.0 with `Eco.ReferenceAssemblies` v0.12.0.6-beta
- Read-only chat commands: `/ecodiet stomach`, `/ecodiet nutrients`, `/ecodiet cravings`, `/ecodiet taste`, `/ecodiet multipliers`
- 49 new tests across config, CLI, persistence, prompts, render, and cmd_predict (101 total)
- Type annotations on `Food.__init__`, `prompts.py`, and all test methods
- Shared `make_food()` helper consolidated in `conftest.py`

### Fixed

- Mod target framework net9.0 → net8.0 to match Eco 0.12 runtime (was causing `ReflectionTypeLoadException`)
- Chat command renamed `/diet` → `/ecodiet` to avoid collision with Eco's built-in `/diet` command
- Escaped `\n` literal in `persistence.py` `log_data_issues()` (was printing backslash-n instead of newline)
- Mutable default argument in `food_state_manager.py`

### Removed

- Craving eligibility system (`can_be_craving()`, `normalized_cravings()`, per-bite craving match bonus) — game provides craving info directly, making prediction unnecessary

## [0.3.0] - 2026-02-01

### Added

- Unit tests for planner ranking functions (21 tests)
- Integration tests for full meal planning pipeline (16 tests)
- YAML config file system (`config.py`, `config.default.yml`)
- `--config` CLI flag for custom configuration
- `STATUS.md` for session continuity

### Changed

- Constants externalized from code to `config.default.yml`
- `constants.py` now re-exports from config for backward compatibility

## [0.2.0] - 2026-02-01

### Added

- `skip_prompts` parameter for non-interactive mode

### Changed

- Variable and constant naming improved for clarity (`_STRENGTH`, `_THRESHOLD`, `_WEIGHT` conventions)
- Backported improvements from Rust implementation

## [0.1.0] - Initial

### Added

- Core meal planning algorithm (`planner.py`, `calculations.py`)
- Food and MealPlanItem models
- CLI interface with plan, predict, reset, rate-unknowns subcommands
- FoodStateManager for stomach state and persistence
- SP math and scoring calculations
- Logging utilities
