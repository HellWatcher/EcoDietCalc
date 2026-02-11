"""Pure scoring utilities for nutrients, bonuses, and SP.

Contains deterministic helpers for nutrient totals, balanced diet/variety/tastiness
bonuses, and SP calculations, plus small simulators used by the planner.

Exports
-------
sum_weighted_nutrients
sum_all_weighted_nutrients
calculate_balanced_diet_bonus
calculate_balanced_diet_ratio
get_tastiness_bonus
calculate_nutrition_multiplier
get_sp
simulate_stomach_with_added_food
evaluate_bonus_with_addition
get_sp_delta
get_balanced_diet_ratio
get_variety_bonus
tastiness_delta_for_added_unit
variety_fraction_for
is_variety_qualifying
soft_variety_count
variety_count

Notes
-----
All functions are side-effect free; inputs are treated as read-only.
"""

import logging
from typing import Dict

from constants import (
    BASE_SKILL_POINTS,
    CRAVING_SATISFIED_FRAC,
    TASTINESS_MULTIPLIERS,
    TASTINESS_WEIGHT,
    VARIETY_BONUS_CAP_PP,
    VARIETY_CAL_THRESHOLD,
)
from models.food import (
    Food,
)

logger = logging.getLogger(__name__)


def _unique_variety_names(
    stomach: dict,
) -> set[str]:
    # only items that individually meet the variety threshold
    return {
        food.name.lower()
        for food, quantity in stomach.items()
        if is_variety_qualifying(food, quantity)
    }


def _total_calories(
    stomach: dict,
) -> float:
    return sum(food.calories * quantity for food, quantity in stomach.items())


def sum_weighted_nutrients(
    stomach,
    attr,
):
    """Calorie-weighted **sum** for a single nutrient.

    Notes
    -----
    Uses the per-food calorie share computed in `sum_all_weighted_nutrients`
    (not raw calories multiplication).

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.
    attr : str
        Nutrient attribute name.
        Examples: "carbs", "protein", "fat", "vitamins".

    Returns
    -------
    float
        Weighted sum for the selected nutrient.
        (Sum over ``nutrient * quantity``.)
    """
    # Weight by calories*quantity so high-cal foods influence balance
    return sum(getattr(food, attr) * quantity for food, quantity in stomach.items())


def sum_all_weighted_nutrients(
    stomach: dict,
):
    """Weighted sums for all nutrient types.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.

    Returns
    -------
    tuple[dict[str, float], float]
        ``(density_dict, total_calories)`` where the dict has keys
        ``"carbs"``, ``"protein"``, ``"fat"``, ``"vitamins"``.
    """
    # Delegate per-attr computation to keep logic in one place
    total_cal = _total_calories(stomach)
    totals = {"carbs": 0.0, "protein": 0.0, "fat": 0.0, "vitamins": 0.0}
    if total_cal == 0:
        return totals, 0.0

    for food, quantity in stomach.items():
        calorie_weight = (food.calories * quantity) / total_cal
        totals["carbs"] += food.carbs * calorie_weight
        totals["protein"] += food.protein * calorie_weight
        totals["fat"] += food.fat * calorie_weight
        totals["vitamins"] += food.vitamins * calorie_weight

    return totals, total_cal


def calculate_balanced_diet_bonus(
    nutrients: list[float],
) -> float:
    """Convert balance ratio to bonus percentage.

    Formula: ``(min_nonzero / max) * 100 - 50``.

    Parameters
    ----------
    nutrients : list of float
        Weighted nutrient totals.

    Returns
    -------
    float
        Bonus percentage in ``[-50, +50]``.
    """

    ratio = calculate_balanced_diet_ratio(nutrients)
    return (ratio * 100) - 50


def calculate_balanced_diet_ratio(
    nutrients: list[float],
) -> float:
    """Balance ratio of the nutrient distribution.

    Defined as ``min_nonzero / max`` among the nutrient values.

    Parameters
    ----------
    nutrients : list of float
        Weighted nutrient totals.

    Returns
    -------
    float
        Ratio in ``[0, 1]``; higher means more balanced.
    """

    # If all totals are zero, ratio is 0; otherwise min/max including zeros
    max_nutrient = max(nutrients)
    if max_nutrient <= 0:
        return 0.0
    return min(nutrients) / max_nutrient


def get_tastiness_bonus(
    stomach: dict,
) -> float:
    """Tastiness bonus percentage points for the current stomach.

    A calorie-weighted average of tastiness multipliers.
    Scaled by ``TASTINESS_WEIGHT``.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.

    Returns
    -------
    float
        Taste bonus in percentage points.
    """

    total_cal = sum(food.calories * quantity for food, quantity in stomach.items())
    if total_cal <= 0:
        return 0.0
    # Map tastiness → multiplier (fraction); default 0 for unknowns.
    # Convert to percentage points below.
    taste_score = sum(
        TASTINESS_MULTIPLIERS.get(food.tastiness, 0.0) * food.calories * quantity
        for food, quantity in stomach.items()
    )
    return (taste_score / total_cal) * 100.0 * TASTINESS_WEIGHT


def calculate_nutrition_multiplier(
    stomach: dict,
    cravings: list[str],
    unique_foods_24h: set[str],
) -> float:
    """Total nutrition multiplier (percentage points).

    Includes balance, variety, and taste bonuses.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.
    cravings : list of str
        Active craving names (case-insensitive).  Reserved for
        future use; not currently consumed by this function.
    unique_foods_24h : set of str
        Foods (names, lowercased) that qualify for variety
        within the 24h window.

    Returns
    -------
    float
        Sum of bonus components in percentage points.
    """

    # ---- balanced diet (ordered list, not dict) ----
    density, _ = sum_all_weighted_nutrients(stomach)

    balanced_diet_pp = calculate_balanced_diet_bonus(
        [
            density["carbs"],
            density["protein"],
            density["fat"],
            density["vitamins"],
        ]
    )
    variety_pp = get_variety_bonus(len(unique_foods_24h))
    tastiness_pp = get_tastiness_bonus(stomach)

    # returns percentage points (not a fraction)
    return balanced_diet_pp + variety_pp + tastiness_pp


def get_sp(
    stomach,
    cravings,
    cravings_satisfied,
    unique_foods_24h,
    *,
    server_mult: float = 1.0,
    dinner_party_mult: float = 1.0,
) -> float:
    """Compute SP (skill points) from stomach and bonuses.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.
    cravings : list of str
        Active craving names.
    cravings_satisfied : int
        Number of cravings already satisfied.
    unique_foods_24h : set of str
        Variety reference set (qualified foods by name).
    server_mult : float, optional
        Server skill gain multiplier. Default is 1.0.
    dinner_party_mult : float, optional
        Dinner party multiplier (1.0-3.0). Default is 1.0.

    Returns
    -------
    float
        Final SP value.

    Notes
    -----
    Formula: ((nutrient_sp * bonuses * dinner_party) + BASE_SP) * server_mult
    """

    density, _ = sum_all_weighted_nutrients(stomach)  # calorie-weighted avg
    density_sum = (
        density["carbs"] + density["protein"] + density["fat"] + density["vitamins"]
    )

    bonus = (
        calculate_nutrition_multiplier(
            stomach,
            cravings,
            unique_foods_24h,
        )
        / 100.0
    )
    bonus += cravings_satisfied * CRAVING_SATISFIED_FRAC

    # Apply dinner party multiplier to nutrition SP, then add base, then server mult
    nutrition_sp = density_sum * (1.0 + bonus) * dinner_party_mult
    return (nutrition_sp + BASE_SKILL_POINTS) * server_mult


def simulate_stomach_with_added_food(
    stomach: dict,
    food_to_add: Food,
) -> dict:
    """Clone the stomach and add one unit of the given food.

    Parameters
    ----------
    stomach : dict[Food, int]
        Original stomach state.
    food_to_add : Food
        Food to add.

    Returns
    -------
    dict[Food, int]
        New stomach mapping with the increment applied.
    """

    # Work on a shallow copy; never mutate the caller's stomach
    clone = dict(stomach)
    clone[food_to_add] = (
        clone.get(
            food_to_add,
            0,
        )
        + 1
    )
    return clone


def evaluate_bonus_with_addition(
    stomach,
    food_to_add,
    cravings,
    variety_reference: set[str],
):
    """Estimate nutrition multiplier after hypothetically adding a food.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.
    food_to_add : Food
        Food to consider adding.
    cravings : list of str
        Active craving names.
    variety_reference : set of str
        Names (lowercased) that already meet the variety threshold.

    Returns
    -------
    float
        Predicted total bonus (percentage points) after the addition.
    """

    test_stomach = simulate_stomach_with_added_food(
        stomach,
        food_to_add,
    )

    # Only add to variety set if this bite newly meets the per-food threshold
    new_total = food_to_add.calories * test_stomach[food_to_add]
    if (
        new_total >= VARIETY_CAL_THRESHOLD
        and food_to_add.name.lower() not in variety_reference
    ):
        updated_variety = variety_reference | {food_to_add.name.lower()}
    else:
        updated_variety = variety_reference

    return calculate_nutrition_multiplier(
        test_stomach,
        cravings,
        updated_variety,
    )


def get_sp_delta(
    food,
    stomach,
    cravings,
    cravings_satisfied,
) -> float:
    """Change in SP from adding one unit of a specific food.

    Parameters
    ----------
    food : Food
        Candidate food to add.
    stomach : dict[Food, int]
        Current stomach state.
    cravings : list of str
        Active craving names.
    cravings_satisfied : int
        Number of cravings already satisfied.

    Returns
    -------
    float
        ``SP(after) - SP(before)`` for a single added unit.
    """

    # Marginal SP: SP(after adding one unit) − SP(before)
    after = simulate_stomach_with_added_food(
        stomach,
        food,
    )
    delta = get_sp(
        after,
        cravings,
        cravings_satisfied,
        _unique_variety_names(after),
    ) - get_sp(
        stomach,
        cravings,
        cravings_satisfied,
        _unique_variety_names(stomach),
    )
    return delta


def get_balanced_diet_ratio(
    stomach,
):
    """Balance ratio for the current stomach.

    Returns
    -------
    float
        ``min_nonzero / max`` using weighted nutrient totals.
    """
    density, _ = sum_all_weighted_nutrients(stomach)
    nutrients = [
        density["carbs"],
        density["protein"],
        density["fat"],
        density["vitamins"],
    ]
    max_nutrient = max(nutrients)
    if max_nutrient <= 0:
        return 0
    return min(nutrients) / max_nutrient


def get_variety_bonus(
    unique_food_count,
):
    """Variety bonus from the number of qualifying foods.

    Parameters
    ----------
    unique_food_count : int
        Count of foods meeting the variety calorie threshold.

    Returns
    -------
    float
        Variety bonus in percentage points (capped).
    """

    # Exponential cap: each +20 qualifying foods halves the remaining gap
    # to the cap
    return VARIETY_BONUS_CAP_PP * (1 - 0.5 ** (unique_food_count / 20))


def tastiness_delta_for_added_unit(
    stomach: dict[Food, int],
    food: Food,
) -> float:
    """Change in tastiness bonus from adding one unit of a food.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.
    food : Food
        Food to add.

    Returns
    -------
    float
        ``tastiness_bonus(after) - tastiness_bonus(before)`` in percentage points.
    """

    before = get_tastiness_bonus(stomach)
    after = get_tastiness_bonus(
        simulate_stomach_with_added_food(
            stomach,
            food,
        )
    )
    return after - before


def variety_fraction_for(
    food_item: Food,
    quantity: int,
) -> float:
    """Fractional variety contribution of a single food.

    Parameters
    ----------
    food_item : Food
        Food to evaluate.
    quantity : int
        Quantity in the stomach.

    Returns
    -------
    float
        Value in ``[0.0, 1.0]``.
        Computed as ``min(1, calories*quantity / VARIETY_CAL_THRESHOLD)``.
    """

    # No contribution when quantity ≤ 0
    if quantity <= 0:
        return 0.0
    # Fraction toward threshold (clamped to 1.0)
    return min(
        1.0,
        (food_item.calories * quantity) / VARIETY_CAL_THRESHOLD,
    )


def is_variety_qualifying(
    food_item: Food,
    quantity: int,
) -> bool:
    """Whether this food alone meets the variety threshold.

    Parameters
    ----------
    food_item : Food
        Food to evaluate.
    quantity : int
        Quantity in the stomach.

    Returns
    -------
    bool
        ``True`` if ``calories * quantity >= VARIETY_CAL_THRESHOLD``.
    """

    # Qualifies if calories * quantity meets or exceeds the threshold
    return (food_item.calories * quantity) >= VARIETY_CAL_THRESHOLD


def soft_variety_count(
    stomach: Dict[Food, int],
) -> float:
    """Soft (fractional) variety count across all foods.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.

    Returns
    -------
    float
        Sum of fractional contributions (can be non-integer).
    """

    # Sum fractional contributions for soft variety
    return sum(
        variety_fraction_for(food_item, quantity)
        for food_item, quantity in stomach.items()
    )


def variety_count(
    stomach: Dict[Food, int],
) -> int:
    """Count of foods that individually meet the variety threshold.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach state.

    Returns
    -------
    int
        Number of qualifying foods.
    """

    # Count foods that individually meet the threshold (hard variety)
    return sum(
        1
        for food_item, quantity in stomach.items()
        if is_variety_qualifying(food_item, quantity)
    )
