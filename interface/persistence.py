"""Persistence and integrity logging utilities.

Provides JSON load/save for food data, writes a diagnostic
log of data issues, and imports mod-exported game state snapshots.

Exports
-------
read_food_dict
save_food_dict
log_data_issues
load_food_state
load_game_state_export

Notes
-----
JSON I/O is UTF-8. Deduplication during save is case-
insensitive by Name.
"""

import json
import re
from pathlib import (
    Path,
)

from constants import (
    TASTINESS_MULTIPLIERS,
)
from food_state_manager import FoodStateManager
from interface.prompts import (
    prompt_for_tastiness,
    prompt_yes_no,
)
from models.food import (
    Food,
)

# Persisted state next to this file (works when run as a module)
ROOT_DIR = Path(__file__).resolve().parents[1]  # project root (one level up)
DATA_PATH = ROOT_DIR / "food_state.json"


def read_food_dict(
    path,
):
    """Load food data from a JSON file into `Food` objects.

    Parameters
    ----------
    path : str | os.PathLike
        Path to the JSON file.

    Returns
    -------
    list[Food]
        Parsed foods. Returns an empty list on error.

    Notes
    -----
    The input JSON is expected to be a list of dicts compatible
    with ``Food.from_dict``.
    """

    # Text mode, UTF-8; fail soft (print + return []) so the CLI can continue
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as in_file:
        try:
            # Defensive parse: swallow JSON/IO errors here.
            # Upstream should handle an empty result set.
            data = json.load(in_file)
            result = []
            for entry in data:
                result.append(Food.from_dict(entry))
            return result
        except Exception as exc:
            print(f"[ERROR] Failed to read food data: {exc}")
            return []


def save_food_dict(
    food_list,
    path,
):
    """Save a deduplicated list of food dicts to a JSON file.

    Parameters
    ----------
    food_list : list[dict]
        Foods as dictionaries. Each entry must include a ``"Name"`` key.
    path : str | os.PathLike
        Destination file path.

    Notes
    -----
    Deduplication is case-insensitive by ``"Name"``. Only the last
    occurrence of each name is kept.
    """

    # Deduplicate by case-insensitive Name; last occurrence wins
    # (dict overwrites by key)
    unique_by_name = {}
    for food in food_list:
        unique_by_name[food["Name"].lower()] = food
    with open(
        path,
        "w",
        encoding="utf-8",
    ) as out_file:
        # Persist the last-seen order of unique names.
        # `list(...)` fixes JSON iteration order on older Python versions
        json.dump(
            list(unique_by_name.values()),
            out_file,
            indent=2,
        )


def log_data_issues(
    all_foods,
    stomach_counts,
    available_counts,
):
    """Log data integrity issues for the current food state to ``log.txt``.

    Parameters
    ----------
    all_foods : list[Food]
        All loaded foods.
    stomach_counts : dict[Food, int]
        Foods consumed (counts per `Food`).
    available_counts : dict[Food, int]
        Foods available (counts per `Food`).

    Notes
    -----
    Writes human-readable sections covering:
    - Foods referenced in stomach/available but missing from the
      master list
    - Invalid tastiness values
    - Unknown tastiness (``99``)
    """
    # Build an index of foods by lowercased name for O(1) membership checks
    foods_by_name = {}
    for food in all_foods:
        foods_by_name[food.name.lower()] = food

    # Names referenced in stomach but missing from the master list
    stomach_unknown = []
    for food in stomach_counts:
        if food.name.lower() not in foods_by_name:
            stomach_unknown.append(food.name)

    available_unknown = []
    for food in available_counts:
        if food.name.lower() not in foods_by_name:
            available_unknown.append(food.name)

    # Any tastiness not present in TASTINESS_MULTIPLIERS is considered invalid
    invalid_entries = []
    for food in all_foods:
        if food.tastiness not in TASTINESS_MULTIPLIERS:
            invalid_entries.append(food.name)

    # Union of referenced foods; flag those still at the unknown sentinel (99)
    taste_unknown = []
    for food in set(stomach_counts) | set(available_counts):
        if food.tastiness == 99:
            taste_unknown.append(food.name)

    # Overwrite log.txt each run
    with open(
        "log.txt",
        "w",
        encoding="utf-8",
    ) as log_file:
        if stomach_unknown:
            log_file.write("[WARN] STOMACH entries not in food_state:\n")
            # De-duplicate and sort for stable, readable output
            for name in sorted(set(stomach_unknown)):
                log_file.write(f"  - {name}\n")
            log_file.write("\n")
        if available_unknown:
            log_file.write("[WARN] AVAILABLE entries not in food_state:\n")
            for name in sorted(set(available_unknown)):
                log_file.write(f"  - {name}\n")
            log_file.write("\n")
        if invalid_entries:
            log_file.write("[WARN] Invalid tastiness values in food_state:\n")
            for name in sorted(set(invalid_entries)):
                log_file.write(f"  - {name}\n")
            log_file.write("\n")
        if taste_unknown:
            log_file.write("[INFO] Foods with unknown tastiness (99):\n")
            for name in sorted(set(taste_unknown)):
                log_file.write(f"  - {name}\n")
            log_file.write("\n")
        if not (
            stomach_unknown or available_unknown or invalid_entries or taste_unknown
        ):
            log_file.write("[INFO] No issues found.\n")


def load_food_state(
    reset_stomach=False,
    reset_tastiness=False,
    *,
    skip_prompts=False,
):
    """Load foods and construct a ``FoodStateManager``.

    Optionally resets stomach counts and/or tastiness ratings, then logs
    integrity issues (unknown names, invalid tastiness) before returning.

    Parameters
    ----------
    reset_stomach : bool
        If ``True``, clear all stomach counts.
    reset_tastiness : bool
        If ``True``, clear all unknown/known tastiness values to default.
    skip_prompts : bool
        If ``True``, skip interactive prompts (for non-interactive use).

    Returns
    -------
    FoodStateManager
        Ready manager with current stomach and availability loaded.
    """

    # Start from persisted state (empty list if missing/corrupt)
    food_dict = read_food_dict(DATA_PATH)

    # Optional: clear stomach counts before building the manager
    if reset_stomach:
        for food in food_dict:
            food.stomach = 0

    # Optional: reset all tastiness to the unknown sentinel (99)
    if reset_tastiness:
        for food in food_dict:
            food.tastiness = 99
            if food.available > 0 and not skip_prompts:
                food.tastiness = prompt_for_tastiness(food.name)

    # Build manager from (possibly reset) data
    manager = FoodStateManager(food_dict)

    # Unknown-tastiness preflight: prompt for items that are available now
    # and still unknown
    if not skip_prompts:
        unknowns = []
        for food in manager.available.keys():
            if (
                manager.available.get(food, 0) > 0
                and getattr(food, "tastiness", 99) == 99
            ):
                unknowns.append(food)
        if unknowns:
            # Short warning message split across two prints to stay under
            # the line-length limit.
            print(f"[WARN] {len(unknowns)} unknown tastiness items.")
            print("(neutral effect).")
            if prompt_yes_no("Would you like to rate them now?"):
                for food in unknowns:
                    food.tastiness = prompt_for_tastiness(food.name)

    if reset_stomach or reset_tastiness:
        save_food_dict(
            manager.to_json_ready(),
            DATA_PATH,
        )
        print("[INFO] Reset saved to 'food_state.json'.")

    log_data_issues(
        food_dict,
        manager.stomach,
        manager.available,
    )
    return manager


def _parse_cravings_satisfied(description: str, multiplier: float) -> int:
    """Derive cravings-satisfied count from the mod export.

    Tries the description string first (e.g. "2 cravings satisfied"),
    then falls back to the multiplier (each satisfied = +0.10 over 1.0).

    Parameters
    ----------
    description : str
        ``Cravings.Description`` from the export JSON.
    multiplier : float
        ``Cravings.Multiplier`` from the export JSON.

    Returns
    -------
    int
        Number of cravings satisfied.
    """
    match = re.search(r"(\d+)\s+craving", description)
    if match:
        return int(match.group(1))
    # Fallback: multiplier is 1.0 + 0.10 per satisfied craving
    if multiplier > 1.0:
        return round((multiplier - 1.0) / 0.10)
    return 0


def load_game_state_export(
    path: str | Path,
) -> tuple[FoodStateManager, list[str], int, float, float, float]:
    """Load a mod-exported game-state JSON into planner-ready objects.

    Parameters
    ----------
    path : str or Path
        Path to the ``game_state_*.json`` file written by the C# mod.

    Returns
    -------
    tuple
        ``(manager, cravings, cravings_satisfied,
        remaining_calories, server_mult, dinner_party_mult)``

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    KeyError
        If required top-level keys are missing.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Build Food objects from the Foods array.
    # The mod sets Available = 0 (can't see inventory); default to unlimited.
    foods: list[Food] = []
    for entry in data["Foods"]:
        food = Food(
            name=entry["Name"],
            calories=entry["Calories"],
            carbs=entry["Carbs"],
            protein=entry["Protein"],
            fat=entry.get("Fat", entry.get("Fats")),
            vitamins=entry["Vitamins"],
            tastiness=entry["Tastiness"],
            stomach=entry.get("Stomach", 0),
            available=entry.get("Available", 99),
        )
        foods.append(food)

    manager = FoodStateManager(foods)

    # Cravings
    cravings_data = data["Cravings"]
    current_craving = cravings_data.get("Current", "None")
    cravings: list[str] = (
        [current_craving] if current_craving and current_craving != "None" else []
    )
    cravings_satisfied = _parse_cravings_satisfied(
        cravings_data.get("Description", ""),
        cravings_data.get("Multiplier", 1.0),
    )

    # Remaining calories
    cal_data = data["Calories"]
    remaining_calories = cal_data["Max"] - cal_data["Current"]

    # Multipliers (server and dinner party are passthrough)
    mult_data = data["Multipliers"]
    server_mult = 1.0  # server mult is not in the per-player export
    dinner_party_mult = mult_data.get("DinnerParty", 1.0)

    return (
        manager,
        cravings,
        cravings_satisfied,
        remaining_calories,
        server_mult,
        dinner_party_mult,
    )
