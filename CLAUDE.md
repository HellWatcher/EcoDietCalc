# Eco Diet Maker (Rust)

A meal planning CLI that optimizes food selection for nutrition, variety, and taste — designed for the game Eco.

**Lineage:** Rust port of [EcoDietCalc](https://github.com/HellWatcher/EcoDietCalc) (Python original at `~/Projects/EcoDietMaker/`)

## Purpose

Helps players plan their in-game diet by:
- Selecting foods to maximize SP (skill points) gain
- Balancing nutritional variety (carbs, protein, fats, vitamins)
- Respecting calorie budgets and personal taste preferences
- Tracking "stomach" state (recently eaten foods) to avoid repetition

## Architecture

```
src/
├── main.rs          # CLI entry point, commands
├── lib.rs           # Public API exports
├── cli.rs           # Clap argument definitions
├── error.rs         # Custom error types
├── models/          # Data structures
│   ├── food.rs      # Food item with nutrients
│   └── plan.rs      # MealPlanItem for results
├── planner/         # Core optimization logic
│   ├── calculations.rs  # SP, variety, taste scoring
│   ├── constants.rs     # Tunable weights/thresholds
│   └── ranking.rs       # Greedy food selection algorithm
├── state/           # Food state persistence
├── interface/       # User prompts (dialoguer)
├── tuner/           # Hyperparameter optimization
│   ├── knobs.rs     # Tunable parameters
│   ├── search.rs    # Random search over knob space
│   └── evaluation.rs # Scoring configurations
└── bin/
    └── tuner.rs     # Tuner binary entry point
```

## Key Concepts

- **SP (Skill Points)**: Calculated from balanced nutrient intake
- **Stomach**: Tracks what you've eaten recently (affects variety bonus)
- **Tastiness**: User rating 1-5 (99 = unknown)
- **Variety Bonus**: Reward for eating different food types
- **Tuner**: Finds optimal scoring weights via random search

## Commands

```bash
# Generate a meal plan
cargo run -- plan

# Rate foods you haven't tried
cargo run -- rate-unknowns

# Reset state
cargo run -- reset --stomach      # Clear recent food history
cargo run -- reset --availability # Reset all availability
cargo run -- reset --tastiness    # Mark all as unrated

# Run the parameter tuner
cargo run --bin tuner
```

## Data Files

| File | Purpose |
|------|---------|
| `food_state.json` | All foods with nutrients, availability, tastiness |
| `tuner_best.json` | Best-found tuner configuration |
| `tuner_results.csv` | All tuner trial results |

## Development

```bash
cargo test           # Run tests
cargo run -- plan    # Test the planner
cargo run --bin tuner # Tune parameters
```

## Goal

**Final vision**: Convert this CLI into a mod for Eco itself — in-game diet planning instead of an external tool.

### Milestones

1. **Complete CLI** — Finish core features, stabilize the planner
   - [ ] Finalize SP/variety/taste scoring
   - [ ] Polish user interface
   - [ ] Comprehensive tests

2. **Research Eco Modding** — Understand the platform
   - [ ] Review Eco modding docs/API
   - [ ] Identify language (C#? Lua? other?)
   - [ ] Study existing diet/food mods for patterns
   - [ ] Determine if Rust FFI is viable or if full port needed

   **Resources:**
   - [Eco Docs](https://docs.play.eco/)
   - [Client API](https://docs.play.eco/api/client/index.html)
   - [Server API](https://docs.play.eco/api/server/index.html)
   - [Remote API](https://docs.play.eco/api/remote/index.html)

   **Reference Mod:**
   - [OpenNutriView](https://github.com/BeanHeaDza/OpenNutriView) — C# nutrition viewer plugin
     - Shows this will need to be C# (not Rust FFI)
     - Study its plugin structure, food item extensions, command handling

3. **Design Mod Architecture** — Plan the integration
   - [ ] Define how mod reads player's food inventory
   - [ ] Design in-game UI (overlay? menu? chat command?)
   - [ ] Map CLI features to mod equivalents

4. **Implement Mod** — Build it
   - [ ] Port or wrap core algorithm
   - [ ] Create in-game interface
   - [ ] Hook into Eco's food/nutrition systems

5. **Release** — Ship it
   - [ ] Test on live server
   - [ ] Package for mod distribution
   - [ ] Write player-facing docs
