# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Add missing foods (Pineapple, Pumpkin, etc.)
- Server skill gain multiplier input
- Dinner Party multiplier input
- Integration tests against known game outcomes

## [0.1.0] - 2026-01-26

### Added
- **Core Planner**
  - Greedy food selection algorithm
  - SP calculation with multiplicative bonuses
  - Balance multiplier (0.5x - 2.0x)
  - Variety multiplier (up to 1.55x)
  - Taste multiplier (0.7x - 1.3x)
  - Craving bonus support

- **Tuner System**
  - Random search optimization (configurable iterations)
  - Pareto frontier multi-objective optimization
  - Hill climbing refinement for local optima
  - Balanced selection (normalized distance to ideal)
  - 8 tunable knobs:
    - `soft_bias_gamma` - Soft-variety ranking bias
    - `tie_alpha` - Proximity weight to variety threshold
    - `tie_beta` - Overshoot penalty
    - `tie_epsilon` - Tie-break window
    - `cal_floor` - Minimum calories before penalty
    - `cal_penalty_gamma` - Low-calorie penalty strength
    - `balance_bias_gamma` - Balance improvement bonus
    - `repetition_penalty_gamma` - Repetition penalty

- **CLI Commands**
  - `plan` - Generate optimal meal plan
  - `rate-unknowns` - Rate untried foods
  - `reset` - Reset stomach/availability/tastiness

- **State Management**
  - JSON-based food state persistence
  - Stomach tracking (24-hour food history)
  - Availability and tastiness per food

- **Data**
  - 110 foods from Eco game with nutrients

### Technical
- Rust port of [EcoDietCalc](https://github.com/HellWatcher/EcoDietCalc) Python original
- 48 unit tests
- Truncated tuner output (3 decimal precision)

[Unreleased]: https://github.com/HellWatcher/EcoDietCalc/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HellWatcher/EcoDietCalc/releases/tag/v0.1.0
