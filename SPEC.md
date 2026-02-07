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

2. **C# Eco Mod (Future)** - Final deliverable
   - Native integration with Eco's Unity/C# architecture
   - Real-time food inventory sync
   - In-game UI for meal planning

The Python codebase serves as the canonical algorithm reference. Once validated against actual gameplay, logic will be manually ported to C#.

---

## Core Algorithm

### SP Calculation Components

The algorithm optimizes for total Skill Points gained per meal, considering:

| Component | Description | Status |
|-----------|-------------|--------|
| **Base SP** | Fixed base (12) + per-nutrient averages across stomach. Formula: `12 + avg(C) + avg(P) + avg(F) + avg(V)` | Verified |
| **Variety Bonus** | Asymptotic bonus: `55% × (1 - 0.5^(food_count/20))`. Requires ≥2000cal per food, 24hr decay per bite. | Formula needs testing (continuous vs discrete at 20-food intervals) |
| **Tastiness Modifier** | Per-food rating (-3 to +3), maps to ±10% per point. Randomized per save. | Verified |
| **Craving Bonus** | +10% per satisfied craving (max 3 cravings, +30% total). One bite satisfies. Bonus persists while food is in stomach. | Verified |

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

## V1 Features (In Scope)

### Python Prototype

- [x] CLI interface with `plan`, `rate-unknowns`, `reset` subcommands
- [x] Food state persistence (JSON)
- [x] Interactive constraint collection (cravings, satisfied count, remaining calories)
- [x] Meal plan generation with per-bite breakdown
- [x] Tastiness rating system (-3 to +3 scale)
- [x] Hyperparameter tuning infrastructure (`tune/`, `tuner_best.json`)
- [ ] Algorithm validation against in-game SP (blocked: needs testing)
- [ ] Comprehensive test suite for edge cases
- [ ] Documentation of formulas with citations

### C# Mod (Future)

- [ ] Read player's food inventory from game data
- [ ] Generate optimized meal plan for remaining daily calories
- [ ] Display SP breakdown (variety %, tastiness %, craving status)
- [ ] In-game UI panel (minimal, non-intrusive)
- [ ] Auto-update food database from game's internal data

---

## Out of Scope (V1)

| Feature | Reason |
|---------|--------|
| Recipe crafting suggestions | Focus on eating optimization only |
| Multi-day planning | Single meal/day scope for v1 |
| Multiplayer plan sharing | Solo optimization first |
| Food price/economy factors | Complexity; defer to v2 |
| "Next bite" real-time mode | Full meal planning is higher value |

---

## Technical Design

### Python Codebase

```
EcoDietMaker/
├── main.py              # CLI entry point
├── planner.py           # Bite selection algorithm
├── calculations.py      # SP formulas and bonuses
├── constants.py         # Tuned hyperparameters
├── food_state_manager.py # State container
├── interface/           # CLI, persistence, rendering
├── models/              # Food, MealPlanItem dataclasses
├── tune/                # Hyperparameter optimization
└── tests/               # pytest suite
```

**Key dependencies:**
- Python 3.13+
- No external ML libraries (pure algorithmic)

### C# Mod Architecture (Planned)

```
EcoDietMakerMod/
├── EcoDietMakerMod.cs   # Mod entry point
├── Planner.cs           # Ported selection algorithm
├── SPCalculator.cs      # Ported SP formulas
├── FoodInventoryReader.cs # Game data integration
└── UI/                  # In-game panel
```

**Integration points:**
- Eco's `IServerPlugin` interface for mod loading
- `FoodItem` and `Stomach` game objects for data access
- `UIManager` for custom panel rendering

---

## Data Model

### Food

```python
@dataclass
class Food:
    name: str
    calories: int
    carbs: float      # 0-1 nutrient density
    protein: float
    fats: float
    vitamins: float
    tastiness: int    # -3 to +3, 99 = unknown
```

### Stomach State

```python
stomach: dict[Food, int]  # Food -> bite count (today)
```

### Meal Plan Output

```python
@dataclass
class MealPlanItem:
    name: str
    calories: int
    sp_gain: float
    new_sp: float
    craving: bool
    variety_delta_pp: float
    taste_delta_pp: float
```

---

## Verification Strategy

### SP Formula

```
total_sp = ((nutrient_avg × (1 + balance% + variety% + tastiness% + craving%)) + 12) × server_mult

Where:
- nutrient_avg = avg(carbs) + avg(protein) + avg(fats) + avg(vitamins)
- balance% = (min/max nutrient ratio × 100 - 50) / 100  (range: -50% to +50%)
- variety% = 55% × (1 - 0.5^(qualifying_foods / 20)), capped at 55%
- tastiness% = tastiness × 10%  (range: -30% to +30%)
- craving% = satisfied_cravings × 10%  (max 3 = 30%)
```

### Phase 1: Manual In-Game Testing

**Environment:** Fresh singleplayer world, default settings (1x SP multiplier)

#### Test Case 1: Base + Nutrients

**Goal:** Verify base constant (12) and nutrient averaging

- Fresh stomach, 0 satisfied cravings, no variety
- Eat 1 bite of known food (e.g., Charred Fish: P:12, F:8, T:+1)
- Expected: `(12 + 20) × 1.10 = 35.2 SP`
- **Pass if:** Actual delta within ±5%

#### Test Case 2: Tastiness Modifier

**Goal:** Verify tastiness% = tastiness × 10%

- Fresh stomach, 0 cravings, no variety
- Test with one positive and one negative tastiness food
- Calculate expected using: `(12 + nutrients) × (1 + T×10%)`
- **Pass if:** Both directions match (±5%)
- **Note:** Tastiness is randomized per save — check in-game first

#### Test Case 3: Craving Bonus

**Goal:** Verify craving% = satisfied_cravings × 10%, max 30%

- Wait for craving to appear
- Note satisfied count before eating
- Eat 1 bite of craved food
- Expected: `(12 + nutrients) × (1 + tastiness% + satisfied×10%)`
- **Pass if:** SP matches at 0, 1, 2, 3 satisfaction levels (±5%)

#### Test Case 4: Variety Bonus

**Goal:** Verify variety% = 55% × (1 - 0.5^(food_count/20))

- Eat ≥2000 cal of one food type (e.g., 4× Charred Fish)
- That food now counts toward variety
- Eat 1 bite of different food, measure SP
- At 1 qualifying food: variety% ≈ 1.9%
- At 20 qualifying foods: variety% ≈ 27.5%
- **Open question:** Continuous or discrete at 20-food intervals?

### Phase 2: Automated Regression

Once formulas are validated:
- Encode test cases as `pytest` fixtures
- Run on every commit to prevent regressions
- Add edge cases as discovered

### Phase 3: Community Validation (Post-Release)

- Share mod with Eco community
- Collect feedback on accuracy
- Iterate based on edge case reports

---

## Phased Roadmap

### Phase 1: Algorithm Validation (Current Priority)
- [x] Document current formula assumptions
- [x] Create in-game test protocol
- [ ] Run validation tests, record results
- [ ] Adjust constants/formulas as needed
- [ ] Achieve <5% SP prediction error

### Phase 2: Python Polish
- [ ] Add missing unit tests
- [ ] Improve error handling and edge cases
- [ ] Clean up code for porting readability
- [ ] Document all formulas with game citations

### Phase 3: C# Mod Prototype
- [ ] Learn Eco modding basics (tutorials, sample mods)
- [ ] Create minimal "hello world" Eco mod
- [ ] Implement food inventory reading
- [ ] Port core SP calculation
- [ ] Basic console output of meal plan

### Phase 4: C# Mod UI
- [ ] Design in-game panel mockup
- [ ] Implement UI rendering
- [ ] Add interactivity (craving input, plan generation)
- [ ] Polish and test

### Phase 5: Community Release
- [ ] Write installation instructions
- [ ] Create mod workshop page
- [ ] Gather feedback and iterate

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

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SOFT_BIAS_GAMMA` | 3.61 | Soft-variety ranking bias strength |
| `TIE_EPSILON` | 0.449 | Tie-break window (SP) |
| `TIE_ALPHA` | 0.977 | Proximity weight toward 2000cal |
| `TIE_BETA` | 0.076 | Overshoot malus |
| `BALANCE_BIAS_GAMMA` | 1.91 | Nutrient balance bonus |
| `REPETITION_PENALTY_GAMMA` | 1.25 | Same-food repetition penalty |
| `CAL_FLOOR` | 395 | Low-calorie penalty threshold |
| `CAL_PENALTY_GAMMA` | 2.48 | Low-calorie penalty strength |
| `VARIETY_BONUS_CAP_PP` | 55.0 | Max variety bonus (pp) |
