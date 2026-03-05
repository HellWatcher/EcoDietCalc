# EcoDietMaker Specification

## Overview

EcoDietMaker is an SP (Skill Point) optimization tool for the video game **Eco**. It calculates optimal food consumption sequences to maximize skill point gain based on the game's nutrition mechanics: variety bonuses, tastiness modifiers, cravings, and nutrient density.

**Target audience:** Eco community players seeking to optimize their diet for maximum SP efficiency.

## Project Structure

### Two-Phase Architecture

1. **Python Prototype (Current)** - Algorithm R&D environment
   - Rapid iteration on SP calculation formulas
   - Hyperparameter tuning (variety bias, calorie penalties, etc.)
   - In-game validation before porting

2. **C# Eco Mod** - Final deliverable
   - Uses `Eco.ReferenceAssemblies` NuGet package (v0.12.0.6-beta, net8.0+)
   - Chat commands for reading stomach, nutrients, cravings, taste, SP multipliers
   - In-game meal planner — full algorithm port with live game state integration
   - Multi-source food discovery (backpack, authorized storage containers, nearby shops)
   - Live stomach tooltip with interactive UILinks and auto-replan
   - Per-player config via single-window ViewEditor (compact, sources, tags, radius, currencies)
   - JSON export for Python prototype consumption

The Python codebase serves as the canonical algorithm reference. The C# mod implements the full planning algorithm with live game state, discovering food from the player's backpack, authorized storage containers, and nearby shops.

---

## Core Algorithm

### SP Calculation Components

The algorithm optimizes for total Skill Points gained per meal, considering:

| Component              | Description                                                                                                           | Status                                                              |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Base SP**            | Fixed base (12) + per-nutrient averages across stomach. Formula: `12 + avg(C) + avg(P) + avg(F) + avg(V)`             | Verified                                                            |
| **Variety Bonus**      | Asymptotic bonus: `55% × (1 - 0.5^(food_count/20))`. Requires ≥2000cal per food, 24hr decay per bite.                 | Formula needs testing (continuous vs discrete at 20-food intervals) |
| **Tastiness Modifier** | Per-food rating (-3 to +3), maps to ±10% per point. Randomized per save.                                              | Verified                                                            |
| **Craving Bonus**      | +10% per satisfied craving (max 3 cravings, +30% total). One bite satisfies. Bonus persists while food is in stomach. | Verified                                                            |

### Selection Algorithm

For each bite, the planner:

1. **Filters** by calorie budget (remaining calories >= food calories)
2. **Computes** raw SP delta for each candidate food
3. **Applies** penalties:
   - Low-calorie penalty (quadratic below 395 cal/unit)
   - Repetition penalty (excessive same-food consumption)
4. **Applies** biases (ranking only, not displayed SP):
   - Soft-variety bias (favors foods improving variety count)
   - Proximity bias (favors reaching 2000cal threshold per food)
   - Balance bias (favors foods improving nutrient ratio)
5. **Selects** highest-ranked food, with tie-breaking by proximity

### Craving-First Strategy

If a craving is satisfiable within the calorie budget, it takes priority over the ranked selection to maximize craving bonuses early.

---

## Remaining Work

### Python

- [x] Algorithm validation against in-game SP (blocked: needs testing)
- [ ] Documentation of formulas with game citations

### C# Mod

- [x] Display SP breakdown (variety %, tastiness %, craving status)
- [x] In-game UI panel (minimal, non-intrusive)
- [ ] Community release (workshop page, feedback loop)

---

## Out of Scope (V1)

| Feature                     | Reason                            |
| --------------------------- | --------------------------------- |
| Recipe crafting suggestions | Focus on eating optimization only |
| Multi-day planning          | Single meal/day scope for v1      |
| Multiplayer plan sharing    | Solo optimization first           |
| Food price/economy factors  | Complexity; defer to v2           |

---

## Technical Design

### C# Mod Architecture

```
mod/EcoDietMod/
├── EcoDietMod.csproj              # net8.0, Eco.ReferenceAssemblies NuGet
├── DietCommands.cs                # Chat commands (/ed plan, /ed config, /ed export)
├── GameStateExporter.cs           # JSON export for Python planner
├── Algorithm/
│   ├── SpCalculator.cs            # SP formulas (ported from calculations.py)
│   ├── BiteSelector.cs            # Ranking pipeline (ported from planner.py)
│   └── MealPlanner.cs             # Plan loop with craving-first strategy
├── Config/
│   ├── PlannerConfig.cs           # Algorithm constants + Default static instance
│   ├── DisplayConfig.cs           # Per-player display prefs (ConcurrentDictionary cache)
│   ├── DisplayConfigViewModel.cs  # ViewEditor ViewModel ([SyncToView] properties)
│   └── ConfigEditor.cs            # Config UI wiring (ViewEditor.Edit)
├── Discovery/
│   ├── StomachSnapshot.cs         # Read User.Stomach into planner dicts
│   ├── FoodDiscovery.cs           # Orchestrate backpack + storage + shop discovery
│   ├── StorageDiscovery.cs        # Authorized storage containers within range
│   ├── ShopDiscovery.cs           # Nearby shops with currency/cost filtering
│   ├── ShopFilter.cs              # Shop filter criteria (record)
│   └── DiscoveryMerger.cs         # Merge multi-source DiscoveryResults
├── Models/
│   ├── FoodCandidate.cs           # Immutable food record (equality by name)
│   ├── MealPlanItem.cs            # Single planned bite (sealed record)
│   ├── MealPlanResult.cs          # Full plan + summary stats (sealed record)
│   ├── SourceInfo.cs              # Source metadata (kind, label, distance, WorldObj)
│   ├── SourceEntry.cs             # Source + quantity pair (sealed record)
│   ├── DiscoveryResult.cs         # Combined discovery with cached HasMultipleSources
│   ├── ItemGroup.cs               # Grouped items for rendering
│   └── PlanStatus.cs              # Plan status enum
├── Rendering/
│   ├── EcoDietTooltipLibrary.cs   # Stomach tooltip registration
│   ├── TooltipRenderer.cs         # UILink tooltip rendering (LocStringBuilder)
│   ├── ItemGrouping.cs            # Shared grouping/formatting utilities
│   └── RichText.cs                # TMP color/style constants
└── Tracking/
    ├── PlanTracker.cs             # In-memory plan cache, fresh plan computation
    ├── ReplanDetector.cs          # Stomach diff + replan reason detection
    └── EcoDietEventHandler.cs     # GlobalFoodEatenEvent → plan invalidation
```

**Integration points:**

- `[ChatCommandHandler]` + `[ChatCommand]`/`[ChatSubCommand]` for chat commands
- `[TooltipLibrary]` + `[NewTooltip]` extension methods for Stomach tooltip sections
- `User.Stomach` → `Contents`, `Nutrients`, `TasteBuds`, `Cravings`, SP multipliers
- `Stomach.GlobalFoodEatenEvent` — invalidates cached plan when player eats
- `IModInit` — registers event handlers at server startup
- `User.MsgLocStr()` for player messaging

### Tooltip System

The mod adds a foldable "EcoDiet" section to the Stomach tooltip showing remaining planned bites with interactive UILinks (food names are clickable with hover tooltips, source names link to stores/containers):

```
--- EcoDiet: 4 bites → +5.63 SP ---
--- From [backpack] ---
  → Huckleberry Extract x2 (+2.88 SP)
  · Beet (+1.12 SP)
--- From [Refrigerator @ 15m] ---
  · Corn (+0.75 SP)
```

**How it works:**

1. `EcoDietTooltipLibrary` registers as a `[TooltipLibrary]` with `CacheAs.Disabled` — tooltip recalculates on every hover
2. `PlanTracker` caches the active plan per player and detects state changes:
   - **On-plan progress**: Player eats food that was next in the plan → filters eaten items from remaining list
   - **Off-plan eating**: Player eats food not in the plan → triggers full replan from current state
   - **Calorie drain**: Player burns calories (crafting, activity) → replans with updated budget
3. `EcoDietEventHandler` subscribes to `Stomach.GlobalFoodEatenEvent` via `IModInit` to mark plans as stale when food is eaten
4. `TooltipRenderer.RenderRemainingPlanTooltip()` formats the countdown as a `LocString` with UILinks and edge states:
   - No food in inventory → `"EcoDiet: No food available"`
   - Stomach full → `"EcoDiet: Stomach full"`
   - All items eaten → `"EcoDiet: Plan complete — 28.4 SP"`

---

## Resolved Mechanics

### Variety Formula

- **Rolling stomach window**: Each bite has an individual 24 real-life hour timer, then leaves stomach
- **Unique food threshold**: Each food name counts once toward variety percentage after eating ≥2000 cal of it
- **No daily reset**: Variety is purely based on what's currently in stomach

### Craving Mechanics

- **Appearance**: Random, roughly every ~2 hours
- **Persistence**: Cravings save with character state (persist across logout/login)
- **Satisfaction**: One bite of craved food satisfies the craving
- **Bonus**: +10% per satisfied craving, max 3 = +30% total. Persists while food is in stomach

### Server Multipliers

- **Global SP multiplier**: Server-wide scaling factor configured by admin
- **Optimization impact**: None — just a final scaling factor, doesn't change which foods are optimal
- **Implementation**: Read server rate and apply to displayed SP values

### Dinner Party Bonus

- **Trigger**: Freshly prepared meal shared on a table between players (social coordination required)
- **Bonus**: +100% SP multiplier
- **Decay**: Bonus decays over 1 real-life week
- **Scope for v1**: Read-only awareness — mod should read current bonus state when calculating SP, but doesn't plan for triggering it

### Stomach Decay

- **Per-bite timers**: Each individual bite has its own 24 real-life hour decay timer
- **Effect on variety**: A food contributes to variety only while at least one of its bites remains in stomach

---

## Success Criteria

V1 is complete when:

1. **Algorithm accuracy**: Predicted SP matches in-game SP within 5% for common meal scenarios
2. **Mod functionality**: C# mod reads inventory, generates plan, displays breakdown in-game
3. **Community usability**: At least 5 Eco players successfully use the mod and provide feedback

---

## Appendix: Current Hyperparameters

From `tuner_best.json` (last tuned 2026-01-27):

| Parameter                            | Value | Description                        |
| ------------------------------------ | ----- | ---------------------------------- |
| `soft_variety_bias_strength`         | 3.61  | Soft-variety ranking bias strength |
| `tiebreak_score_window_sp`           | 0.449 | Tie-break window (SP)              |
| `proximity_approach_weight`          | 0.977 | Proximity weight toward 2000cal    |
| `proximity_overshoot_penalty`        | 0.076 | Overshoot malus                    |
| `balanced_diet_improvement_strength` | 1.91  | Nutrient balance bonus             |
| `repetition_penalty_strength`        | 1.25  | Same-food repetition penalty       |
| `low_calorie_threshold`              | 395   | Low-calorie penalty threshold      |
| `low_calorie_penalty_strength`       | 2.48  | Low-calorie penalty strength       |
| `variety_bonus_cap_pp`               | 55.0  | Max variety bonus (pp)             |
