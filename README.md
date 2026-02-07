# EcoDietCalc

SP (Skill Point) optimization tool for the video game **[Eco](https://play.eco/)**. Calculates optimal food consumption sequences to maximize skill point gain based on the game's nutrition mechanics: variety bonuses, tastiness modifiers, cravings, and nutrient density.

Python prototype for algorithm R&D, with a C# Eco server mod for in-game data access.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/HellWatcher/EcoDietCalc.git
cd EcoDietCalc
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Plan an optimal meal
python main.py plan

# Plan with custom config
python main.py --config my_config.yml plan

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
mod/EcoDietMod/          C# Eco mod (read-only game data access)
```

## Eco Mod

The `mod/EcoDietMod/` directory contains an Eco server mod that exposes food/diet game data via chat commands. Compatible with Eco 0.12.x.

### In-Game Commands

| Command                | Description                                                       |
| ---------------------- | ----------------------------------------------------------------- |
| `/ecodiet`             | List available subcommands                                        |
| `/ecodiet stomach`     | Current stomach contents and calories                             |
| `/ecodiet nutrients`   | Nutrient levels (carbs, protein, fat, vitamins)                   |
| `/ecodiet cravings`    | Active craving and craving multiplier                             |
| `/ecodiet taste`       | Discovered taste preferences and multipliers                      |
| `/ecodiet multipliers` | All SP multipliers (variety, balanced diet, taste, craving, etc.) |

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

1. Build the mod (see above)
2. Copy `EcoDietMod.dll` to your Eco server's `Mods/` folder
3. Restart the server
4. Verify by running `/ecodiet` in chat

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
cd mod/EcoDietMod && dotnet build -c Release
```

## License

GPL-2.0
