# EcoDietMaker

Python CLI for generating environmentally-conscious diet plans.
Project scope @/home/hellwatcher/Projects/EcoDietMaker

## Commands

```bash
# Run
python main.py

# Test
pytest

# Type check
mypy .
```

## Structure

- `main.py` — entry point
- `interface/` — CLI, persistence, prompts, render
- `models/` — domain models (food, plan)
- `planner.py`, `calculations.py` — core logic
- `tests/` — pytest suite

## Conventions

- Type hints on all functions
- Tests mirror source structure in `tests/`
- Conventional commits: feat:, fix:, refactor:, test:

## Naming Conventions

### Variables
- No single-letter variables except loop indices (`i`, `j`, `k`)
- No abbreviations unless standard (`exc` for exception, `cal` for calories)
- Use descriptive suffixes: `_count`, `_weight`, `_delta`, `_before`/`_after`
- Boolean variables: `is_`, `has_`, `can_`, `should_` prefixes
- Width variables: use `_width` not `_w`

### Constants
- `_STRENGTH` for tunable coefficients (not `_GAMMA`)
- `_THRESHOLD` for cutoff values (not `_FLOOR`)
- `_WEIGHT` for multiplicative factors
- `_PENALTY`/`_BONUS` to indicate direction
- Group with common prefix (`CRAVING_*`, `VARIETY_*`, `TIEBREAK_*`, `PROXIMITY_*`)
