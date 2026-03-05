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

See SPEC.md for full architecture tree. Build: `dotnet build mod/EcoDietMod/EcoDietMod.csproj`

## Eco API Reference

Decompiled source at `mod/eco-api-decompiled/` (gitignored) for API exploration.

### Key Namespaces

- **Gameplay**: `Eco.Gameplay.Players`, `.Items`, `.Objects`, `.Components.Storage`, `.Components.Store`, `.Economy`, `.Systems.NewTooltip`, `.Systems.TextLinks`, `.Civics.GameValues`
- **Core**: `Eco.Core.Controller`, `.Systems`
- **Shared**: `Eco.Shared.Localization`, `.Logging`, `.Networking`, `.Serialization`, `.View`, `.Utils`

### Integration Patterns

- `[ChatCommandHandler]` + `[ChatCommand]`/`[ChatSubCommand]` — chat commands
- `[TooltipLibrary]` + `[NewTooltip]` extension methods + `CacheAs.Disabled` — stomach tooltip sections
- `IModInit` — register event handlers at server startup
- `Stomach.GlobalFoodEatenEvent` — fired when any player eats
- `User.MsgLocStr()` — send localized chat messages
- `ViewEditor.Edit(user, controller, onSubmit, ...)` — single-window property editor
- `Item.Get(type).UILink()` / `worldObject.UILink()` — interactive inline links in LocStrings

### Known Gotchas

- **Logging**: `Eco.Shared.Logging.Log.WriteWarningLineLocStr()` — NOT `Eco.Shared.Utils.Log`
- **Bool ViewEditor**: `[Autogen]` bool checkbox never fires `[AutoRPC]` RPCs — use `int` (0/1) with text-input widget as workaround
- **World object iteration**: No `WorldObjectManager.GetWorldObjectsWithComponent<T>()` — use `WorldObjectManager.ForEach()` + `GetComponent<T>()`
- **Shop currency**: Per-store via `StoreComponent.CurrencyName` — no `TradeOffer.Currency`
- **Auth check**: `worldObject.Auth?.IsAuthorizedConsumerAccess(user.Player)` — no static `AuthManager`
- **WorldObject.DisplayName**: Returns `LocString` not `string` — add `.ToString()` when needed

## Tooltip Pipeline

`EcoDietTooltipLibrary` → `PlanTracker` → `TooltipRenderer.RenderRemainingPlanTooltip()`

1. `EcoDietTooltipLibrary` registers with `CacheAs.Disabled` — recalculates on every hover
2. `PlanTracker` caches active plan per player, detects state changes:
   - **On-plan**: player eats next planned food → filters eaten items
   - **Off-plan**: player eats unplanned food → full replan
   - **Calorie drain**: calories burned → replans with updated budget
3. `EcoDietEventHandler` subscribes to `GlobalFoodEatenEvent` via `IModInit` to mark plans stale
4. `TooltipRenderer` renders remaining items as `LocString` with UILinks and edge states (no food, stomach full, plan complete)

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
