"""Persistence and integrity logging utilities.

Provides JSON load/save for food data and writes a diagnostic
log of data issues.

Exports
-------
read_food_dict
save_food_dict
log_data_issues
load_food_state

Notes
-----
JSON I/O is UTF-8. Deduplication during save is case-
insensitive by Name.
"""

import json
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
                log_file.write(f"  - {name}\\n")
            log_file.write("\\n")
        if available_unknown:
            log_file.write("[WARN] AVAILABLE entries not in food_state:\n")
            for name in sorted(set(available_unknown)):
                log_file.write(f"  - {name}\\n")
            log_file.write("\\n")
        if invalid_entries:
            log_file.write("[WARN] Invalid tastiness values in food_state:\n")
            for name in sorted(set(invalid_entries)):
                log_file.write(f"  - {name}\\n")
            log_file.write("\\n")
        if taste_unknown:
            log_file.write("[INFO] Foods with unknown tastiness (99):\n")
            for name in sorted(set(taste_unknown)):
                log_file.write(f"  - {name}\\n")
            log_file.write("\\n")
        if not (
            stomach_unknown
            or available_unknown
            or invalid_entries
            or taste_unknown
        ):
            log_file.write("[INFO] No issues found.\n")


def load_food_state(
    reset_stomach=False,
    reset_tastiness=False,
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
            if food.available > 0:
                food.tastiness = prompt_for_tastiness(food.name)

    # Build manager from (possibly reset) data
    manager = FoodStateManager(food_dict)

    # Unknown-tastiness preflight: prompt for items that are available now
    # and still unknown
    unknowns = []
    for food in manager.available.keys():
        if manager.available.get(food, 0) > 0 and getattr(
            food, "tastiness", 99
        ) == 99:
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
