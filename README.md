# EcoDietMaker

SP (Skill Point) optimization tool for the video game **[Eco](https://play.eco/)**. Calculates optimal food consumption sequences to maximize skill point gain based on the game's nutrition mechanics: variety bonuses, tastiness modifiers, cravings, and nutrient density.

Python prototype for algorithm R&D, with a **C# Eco server mod** that provides an in-game meal planner, live stomach tooltip, and multi-source food discovery.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/HellWatcher/EcoDietCalc.git
cd EcoDietMaker
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage (Python Prototype)

```bash
# Plan an optimal meal
python main.py plan

# Plan with custom config
python main.py --config my_config.yml plan

# Plan from mod-exported game state (exported to Mods/EcoDietMod/exports/ on the server)
python main.py plan --import path/to/export.json

# Validate SP prediction for a specific food
python main.py predict

# Reset parts of state (stomach, availability, etc.)
python main.py reset

# Rate unknown tastiness values
python main.py rate-unknowns

# Verbose output
python main.py -v plan     # INFO level
python main.py -vv plan    # DEBUG level
```

## How It Works

For each bite, the planner:

1. Filters candidates by calorie budget
2. Computes raw SP delta (base SP + nutrient averages + variety bonus + tastiness + cravings)
3. Applies penalties (low-calorie, repetition)
4. Applies ranking biases (variety, proximity to 2000cal threshold, nutrient balance)
5. Selects the highest-ranked food, with craving satisfaction prioritized

See [SPEC.md](SPEC.md) for full game mechanics and formulas, or [docs/FORMULAS.md](docs/FORMULAS.md) for SP calculation details.

## Configuration

Tunable constants are externalized to `config.default.yml`. Copy and modify for custom tuning:

```bash
cp config.default.yml my_config.yml
# Edit my_config.yml, then:
python main.py --config my_config.yml plan
```

Config sections: `algorithm` (ranking parameters), `game_rules` (variety threshold, cravings), `safety` (iteration limits), `display` (rendering thresholds).

## Project Layout

```
main.py                  Entry point, dispatches subcommands
planner.py               Bite selection algorithm
calculations.py          SP math and scoring
config.py                YAML config loader
config.default.yml       Default tunable constants
constants.py             Re-exports config values for backward compat
food_state_manager.py    Stomach state, availability, persistence
interface/               CLI, prompts, rendering, persistence
models/                  Food and MealPlanItem domain models
tune/                    Algorithm parameter tuner
tests/                   Pytest suite mirroring source structure
mod/EcoDietMod/          C# Eco server mod (see below)
```

## Eco Mod

The `mod/EcoDietMod/` directory contains a C# Eco server mod with a full in-game meal planner, live stomach tooltip, per-player config, and multi-source food discovery (backpack, storage containers, nearby shops). Compatible with Eco 0.12.x.

### Features

- **Meal planning** — optimized bite sequence from available food, displayed in chat or as a live stomach tooltip
- **Live stomach tooltip** — hoverable "EcoDiet" section shows remaining planned bites with interactive UILinks (food icons + clickable names), auto-replans when you eat or move
- **Multi-source discovery** — finds food in your backpack, authorized storage containers, and nearby shops (filtered by currency and cost)
- **Per-player config** — toggle compact mode, source groups, scoring tags, set discovery radius and shop currency filters via a single-window editor
- **JSON export** — export game state for the Python prototype planner

### In-Game Commands

| Command                    | Description                                                       |
| -------------------------- | ----------------------------------------------------------------- |
| `/ediet config`            | Open the settings editor (compact, sources, tags, radius, etc.)   |
| `/ediet`                   | List available subcommands                                        |

### Mod Structure

```
mod/EcoDietMod/
├── DietCommands.cs              Chat commands (/ed plan, /ed config, /ed export)
├── GameStateExporter.cs         JSON export for Python planner
├── Algorithm/
│   ├── SpCalculator.cs          SP formulas, variety, tastiness, bonuses
│   ├── BiteSelector.cs          Ranking pipeline (biases, penalties)
│   └── MealPlanner.cs           Plan loop with craving-first strategy
├── Config/
│   ├── PlannerConfig.cs         Algorithm constants + Default instance
│   ├── DisplayConfig.cs         Per-player display prefs (cached)
│   ├── DisplayConfigViewModel.cs  ViewEditor ViewModel
│   └── ConfigEditor.cs          Config UI wiring
├── Discovery/
│   ├── StomachSnapshot.cs       Read User.Stomach into planner dicts
│   ├── FoodDiscovery.cs         Orchestrate backpack + storage + shop discovery
│   ├── StorageDiscovery.cs      Authorized storage containers
│   ├── ShopDiscovery.cs         Nearby shops with currency/cost filtering
│   ├── ShopFilter.cs            Shop filter criteria
│   └── DiscoveryMerger.cs       Merge multi-source results
├── Models/
│   ├── FoodCandidate.cs         Immutable food record (equality by name)
│   ├── MealPlanItem.cs          Single planned bite (record)
│   ├── MealPlanResult.cs        Full plan + summary stats (record)
│   ├── SourceInfo.cs            Source metadata (kind, label, distance)
│   ├── SourceEntry.cs           Source + quantity pair (record)
│   ├── DiscoveryResult.cs       Combined discovery with cached HasMultipleSources
│   ├── ItemGroup.cs             Grouped items for rendering
│   └── PlanStatus.cs            Plan status enum
├── Rendering/
│   ├── EcoDietTooltipLibrary.cs Stomach tooltip registration
│   ├── TooltipRenderer.cs       UILink tooltip rendering
│   ├── ItemGrouping.cs          Shared grouping/formatting utilities
│   └── RichText.cs              TMP color/style constants
└── Tracking/
    ├── PlanTracker.cs           In-memory plan cache, fresh plan computation
    ├── ReplanDetector.cs        Stomach diff + replan reason detection
    └── EcoDietEventHandler.cs   GlobalFoodEatenEvent → plan invalidation
```

### Building the Mod

#### Prerequisites

- [.NET 8.0 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)

Verify your install:

```bash
dotnet --version   # Should show 8.x.x
```

#### Linux

```bash
cd mod/EcoDietMod
dotnet build -c Release
```

Output: `bin/Release/net8.0/EcoDietMod.dll`

#### Windows

```powershell
cd mod\EcoDietMod
dotnet build -c Release
```

Output: `bin\Release\net8.0\EcoDietMod.dll`

### Installing the Mod

#### Option A: Download prebuilt DLL (recommended)

1. Go to the [latest release](https://github.com/HellWatcher/EcoDietCalc/releases/latest)
2. Download `EcoDietMod.dll`
3. Drop it into your Eco server's `Mods/` folder
4. Restart the server
5. Verify by running `/ed plan` in chat

#### Option B: Build from source

1. Build the mod (see above)
2. Copy `EcoDietMod.dll` to your Eco server's `Mods/` folder
3. Restart the server
4. Verify by running `/ed plan` in chat

The `Mods/` folder is in your server's root directory — typically:

- **Linux (Steam):** `~/.local/share/Steam/steamapps/common/Eco/Eco_Data/Server/Mods/`
- **Windows (Steam):** `C:\Program Files (x86)\Steam\steamapps\common\Eco\Eco_Data\Server\Mods\`
- **Windows (standalone):** wherever you extracted the server, e.g. `C:\EcoServer\Mods\`

> **Note:** Only `EcoDietMod.dll` needs to be copied. The mod's NuGet dependencies (`Eco.ReferenceAssemblies`) are already part of the server runtime.

## Development

```bash
# Run tests (Python)
pytest

# Type check (Python)
mypy .

# Build mod (C#)
dotnet build mod/EcoDietMod/EcoDietMod.csproj
```

## License

GPL-2.0
