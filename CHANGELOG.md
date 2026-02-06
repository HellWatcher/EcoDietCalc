# Changelog

All notable changes to EcoDietMaker are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
