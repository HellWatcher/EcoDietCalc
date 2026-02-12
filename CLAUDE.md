# EcoDietMaker

SP optimization tool for the video game **Eco** — calculates optimal food consumption sequences to maximize skill point gain.

## Session Start

1. Read `STATUS.md` — current state, gaps, next steps
2. Update `STATUS.md` at session end with changes and discoveries

## Commands

```bash
# Plan a meal
python main.py plan

# Plan with custom config
python main.py --config my_config.yml plan

# Other subcommands
python main.py predict       # Validate SP for a specific food
python main.py reset         # Reset parts of state
python main.py rate-unknowns # Rate unknown tastiness

# Verbose output
python main.py -v plan       # INFO level
python main.py -vv plan      # DEBUG level

# Test & type check
pytest
mypy .
```

## Structure

### Python (algorithm prototype)

```
main.py                  — entry point, dispatches subcommands
planner.py               — bite selection algorithm
calculations.py          — SP math and scoring
config.py                — YAML config loader with dataclasses
config.default.yml       — default tunable constants
constants.py             — re-exports config values for backward compat
food_state_manager.py    — stomach state, availability, persistence
interface/               — CLI (cli.py), prompts, render, persistence
models/                  — Food (food.py), MealPlanItem (plan.py)
tune/                    — algorithm parameter tuner
logs/                    — logging utilities
tests/                   — pytest suite mirroring source structure
```

### C# Mod (in-game integration)

```
mod/EcoDietMod/
├── DietCommands.cs              — /ed plan, /ed config, /ed export chat commands
├── GameStateExporter.cs         — JSON export for Python planner
├── Algorithm/                   — SP math + bite selection (ported from Python)
│   ├── SpCalculator.cs          — SP formulas, variety, tastiness, bonuses
│   ├── BiteSelector.cs          — ranking pipeline (biases, penalties)
│   └── MealPlanner.cs           — plan loop with craving-first strategy
├── Config/
│   └── PlannerConfig.cs         — algorithm constants
├── Discovery/
│   ├── StomachSnapshot.cs       — read User.Stomach into planner dicts
│   └── FoodDiscovery.cs         — enumerate food from player backpack
├── Models/
│   ├── FoodCandidate.cs         — immutable food record (equality by name)
│   ├── MealPlanItem.cs          — single planned bite with scoring
│   └── MealPlanResult.cs        — full plan + summary stats
├── Rendering/
│   ├── EcoDietTooltipLibrary.cs — stomach tooltip (live plan countdown)
│   └── PlanRenderer.cs          — format plan for chat + tooltip
└── Tracking/
    ├── PlanTracker.cs           — in-memory plan cache, progress detection
    └── EcoDietEventHandler.cs   — GlobalFoodEatenEvent → plan invalidation
```

Build: `dotnet build mod/EcoDietMod/EcoDietMod.csproj`

## Key Docs

- `SPEC.md` — full specification and game mechanics
- `STATUS.md` — session continuity and known gaps
- `CHANGELOG.md` — release history (update on releases)
- `docs/FORMULAS.md` — SP calculation formulas
- `docs/TEST_PROTOCOL.md` — testing approach

## Naming Conventions

### Variables

- No single-letter variables except loop indices (`i`, `j`, `k`)
- No abbreviations unless standard (`exc` for exception, `cal` for calories)
- Descriptive suffixes: `_count`, `_weight`, `_delta`, `_before`/`_after`
- Booleans: `is_`, `has_`, `can_`, `should_` prefixes
- Width: `_width` not `_w`

### Constants

- `_STRENGTH` for tunable coefficients (not `_GAMMA`)
- `_THRESHOLD` for cutoff values (not `_FLOOR`)
- `_WEIGHT` for multiplicative factors
- `_PENALTY`/`_BONUS` to indicate direction
- Group with common prefix (`CRAVING_*`, `VARIETY_*`, `TIEBREAK_*`, `PROXIMITY_*`)

## Session End

Update `STATUS.md` with:

- Changes made (files modified, features added)
- Test results if tests were run
- New gaps or issues discovered
- Next steps if work is incomplete

Update `CHANGELOG.md` if a version milestone was reached.
