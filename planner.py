"""Meal planning and bite selection logic.

Provides the ranking pipeline used to select the next bite. The
algorithm considers SP deltas, soft-variety effects, proximity tie-breaks,
and optional low-calorie penalties.

Exports
-------
plan_meal
"""

import difflib
import logging

from calculations import (
    get_sp_delta,
    get_variety_bonus,
    simulate_stomach_with_added_food,
    soft_variety_count,
    sum_all_weighted_nutrients,
    taste_delta_for_added_unit,
    variety_count,
)
from constants import (
    CAL_FLOOR,
    CAL_PENALTY_GAMMA,
    MAX_ITERATIONS,
    SOFT_BIAS_GAMMA,
    TIE_ALPHA,
    TIE_BETA,
    TIE_EPSILON,
    VARIETY_CAL_THRESHOLD,
)
from food_state_manager import (
    FoodStateManager,
)
from models.food import (
    Food,
)
from models.plan import append_meal_log

logger = logging.getLogger(__name__)


# Ranking-only bias helpers; never change the SP shown to the user
# Nutrient density after a hypothetical bite:
# (carbs+protein+fats+vitamins)/calories
def _nutrient_sum(
    stomach: dict,
) -> float:
    """Compute nutrient-per-calorie density for a stomach state.

    Returns
    -------
    float
        Weighted sum of nutrients divided by total calories.
        Returns 0.0 if there are no calories.
    """
    density, _ = sum_all_weighted_nutrients(stomach)
    return density["carbs"] + density["protein"] + density["fats"] + density["vitamins"]


def fmt_signed(
    value: float,
) -> str:
    """Format a float with an explicit sign and two decimals.

    Parameters
    ----------
    value : float
        Number to format.

    Returns
    -------
    str
        Formatted string like ``+1.23`` or ``-0.45``.
    """
    return f"+{value:.2f}" if value >= 0 else f"{value:.2f}"


def _soft_variety_bias(
    stomach: dict[Food, int],
    food: Food,
) -> float:
    """Bias based on change in soft-variety bonus if one unit is added.

    The soft-variety delta (in percentage points) is scaled by the
    post-bite nutrient density to nudge the ranking.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach counts.
    food : Food
        Candidate food to hypothetically add.

    Returns
    -------
    float
        Bias term to add to the primary rank score.
    """
    # Soft-variety delta (pp) after adding this food; scaled by
    # post-bite nutrient density
    before_sv = soft_variety_count(stomach)
    after_sv = soft_variety_count(simulate_stomach_with_added_food(stomach, food))
    delta_pp = get_variety_bonus(after_sv) - get_variety_bonus(before_sv)

    ns_after = _nutrient_sum(simulate_stomach_with_added_food(stomach, food))
    assert isinstance(
        ns_after, (int, float)
    ), f"ns_after type={type(ns_after)} val={ns_after}"

    return SOFT_BIAS_GAMMA * ns_after * (delta_pp / 100.0)


def _proximity_bias(
    stomach: dict[Food, int],
    food: Food,
) -> float:
    """Tie-break bias for moving toward (or overshooting)
    the per-food variety target.

    Parameters
    ----------
    stomach : dict[Food, int]
        Current stomach counts.
    food : Food
        Candidate food being considered.

    Returns
    -------
    float
    Positive when the bite moves closer to the target.
    Small negative if it overshoots.
    """
    # Favor moving toward the variety threshold (VARIETY_CAL_THRESHOLD) for
    # THIS food; small malus if overshooting
    count_before = stomach.get(food, 0)
    p_before = (food.calories * count_before) / VARIETY_CAL_THRESHOLD
    p_after = (food.calories * (count_before + 1)) / VARIETY_CAL_THRESHOLD
    grow = max(0.0, min(1.0, p_after) - min(1.0, p_before))
    over = max(0.0, p_after - 1.0)
    prox = grow - over * (TIE_BETA / TIE_ALPHA if TIE_ALPHA > 0 else 0.0)
    return TIE_ALPHA * prox


def _low_calorie_penalty(
    food: Food,
) -> float:
    """Quadratic penalty for foods below the calorie floor.

    Parameters
    ----------
    food : Food
        Candidate food being considered.

    Returns
    -------
    float
        Non-positive penalty (0 if at/above the floor).
    """
    # Quadratic penalty below CAL_FLOOR:
    # -CAL_PENALTY_GAMMA * (1 - cal/CAL_FLOOR)^2
    if food.calories >= CAL_FLOOR:
        return 0.0
    x = 1.0 - (food.calories / CAL_FLOOR)  # 0 at floor, -> 1 as calories -> 0
    return -CAL_PENALTY_GAMMA * (x * x)


def update_cravings(
    cravings: list[str],
    food: Food,
) -> bool:
    """Remove a satisfied craving if this food matches.

    Parameters
    ----------
    cravings : list[str]
        Remaining cravings (case-insensitive names).
    food : Food
        Food that may satisfy a craving.

    Returns
    -------
    bool
        True if a craving was removed; False otherwise.
    """
    # Compare using lowercase names; upstream normalized earlier
    food_name = food.name.lower()
    if food_name in cravings:
        cravings.remove(food_name)
        return True
    return False


def _choose_next_bite(
    manager: FoodStateManager,
    remaining_calories: int,
    cravings: list[str],
    cravings_satisfied: int,
) -> tuple[
    Food | None,
    float,
]:
    """Select the next bite purely by ranking.

    First filters by feasibility (calories), then scores candidates by
    SP delta plus penalties/biases; finally applies a soft-variety primary rank
    and a proximity tie-break among near-equal options.

    Parameters
    ----------
    manager : FoodStateManager
        Current food state and availability.
    remaining_calories : int
        Calories left to spend.
    cravings : list[str]
        Current cravings (names, case-insensitive).
    cravings_satisfied : int
        Count of cravings already satisfied.

    Returns
    -------
    tuple[Food | None, float]
        Best food and its raw SP delta; (None, 0.0) if nothing fits.
    """
    candidates: list[tuple[Food, float, float]] = []
    # (food, raw_delta, rank_score)
    best_food = None
    best_rank_score = float("-inf")
    best_raw_delta = 0.0

    # 1) Compute raw ΔSP + low-calorie penalty (first pass, no soft/proximity)
    for food in manager.all_available():
        # Skip foods that exceed the remaining calorie budget for this plan
        if food.calories > remaining_calories:
            continue

        # Raw ΔSP from adding one unit now. Includes daily multiplier
        # via `cravings_satisfied`.
        raw_delta = get_sp_delta(
            food,
            manager.stomach,
            cravings,
            cravings_satisfied,
        )
        rank_score = raw_delta + _low_calorie_penalty(food)
        candidates.append(
            (
                food,
                raw_delta,
                rank_score,
            )
        )
        if rank_score > best_rank_score:
            best_rank_score = rank_score
            best_food = food
            best_raw_delta = raw_delta

    if not candidates:
        return None, 0.0

    # 2) Keep near-equals within TIE_EPSILON of the best rank_score
    near_candidates = [
        (food, raw_delta, rank_score)
        for (food, raw_delta, rank_score) in candidates
        if (best_rank_score - rank_score) <= TIE_EPSILON
    ]

    # Sort by (primary_rank, proximity_bias); pick the last (highest)
    scored_candidates: list[tuple[Food, float, float, float]] = []

    # 3) Add soft-variety as primary rank; use proximity as
    #    deterministic tie-break
    for food, raw_delta, _rank_score in near_candidates:
        soft_variety_bias = _soft_variety_bias(
            manager.stomach,
            food,
        )
        proximity_bias = _proximity_bias(
            manager.stomach,
            food,
        )
        primary_rank = raw_delta + _low_calorie_penalty(food) + soft_variety_bias
        scored_candidates.append(
            (
                food,
                raw_delta,
                primary_rank,
                proximity_bias,
            )
        )

    if not scored_candidates:
        return best_food, best_raw_delta

    scored_candidates.sort(
        key=lambda candidate: (candidate[2], candidate[3]),
    )  # (primary_rank, proximity_bias)
    best_food, best_raw_delta, _, _ = scored_candidates[-1]
    return best_food, best_raw_delta


def _apply_bite(
    manager,
    food,
    *,
    current_sp,
    remaining_calories,
    cravings,
    cravings_satisfied,
    variety_count_now,
    meal_plan,
    server_mult: float = 1.0,
    dinner_party_mult: float = 1.0,
) -> tuple[float, int, int, int]:
    """Consume `food`, recompute SP/bonuses, append to log,
    and return updated state.
    """
    before_sp = current_sp
    pre_stomach = dict(manager.stomach)
    taste_delta = taste_delta_for_added_unit(pre_stomach, food)

    manager.consume(food)
    remaining_calories -= food.calories

    # Consider it satisfied whenever this bite matches a
    # remaining craving (case-insensitive)
    food_name = normalize_name(food.name)
    satisfied = False
    if food_name in cravings:  # remove one instance if duplicated
        cravings.remove(food_name)
        cravings_satisfied += 1
        satisfied = True

    current_sp = manager.get_current_sp(
        cravings=cravings,
        cravings_satisfied=cravings_satisfied,
        server_mult=server_mult,
        dinner_party_mult=dinner_party_mult,
    )

    new_variety_count = variety_count(manager.stomach)
    new_var = get_variety_bonus(new_variety_count)
    old_var = get_variety_bonus(variety_count_now)
    variety_delta = new_var - old_var

    append_meal_log(
        meal_log=meal_plan,
        food=food,
        sp_gain=current_sp - before_sp,
        new_sp=current_sp,
        craving=satisfied,
        variety_delta=variety_delta,
        taste_delta=taste_delta,
    )

    return (
        current_sp,
        remaining_calories,
        cravings_satisfied,
        new_variety_count,
    )


def _pick_feasible_craving(
    manager,
    cravings,
    remaining_calories,
    cravings_satisfied,
):
    """Return a craving food that can be eaten now.
    Picks the highest ΔSP among feasible options, or None.
    """
    cravings_set = {normalize_name(name) for name in cravings}
    candidates = []
    for food, quantity_available in manager.available.items():
        if not quantity_available or food.calories > remaining_calories:
            continue
        if normalize_name(food.name) in cravings_set:
            sp_delta = get_sp_delta(
                food,
                manager.stomach,
                cravings,
                cravings_satisfied,
            )
            candidates.append((sp_delta, food))
    return max(candidates)[1] if candidates else None


def normalize_name(
    text: str,
) -> str:
    """Lowercase + trim for robust name matching."""
    return text.strip().casefold()


def validate_cravings(
    manager,
    cravings_normalized: list[str],
) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """Filter cravings to valid food names; return invalid items
    and suggestions.
    """
    # Build a normalized name index from the known foods
    known_names = {normalize_name(food.name) for food in manager.foods.values()}
    valid = []
    invalid = []
    suggestions: dict[str, list[str]] = {}
    for name in cravings_normalized:
        if name in known_names:
            valid.append(name)
        else:
            invalid.append(name)
            guesses = difflib.get_close_matches(
                name,
                list(known_names),
                n=3,
                cutoff=0.6,
            )
            if guesses:
                suggestions[name] = guesses

    if invalid:
        logger.warning("Ignoring invalid cravings: %s", ", ".join(invalid))
        for bad in invalid:
            if bad in suggestions:
                logger.info(
                    "Did you mean: %s → %s",
                    bad,
                    ", ".join(suggestions[bad]),
                )
    return valid, invalid, suggestions


def plan_meal(
    manager,
    cravings,
    cravings_satisfied,
    remaining_calories,
    *,
    server_mult: float = 1.0,
    dinner_party_mult: float = 1.0,
):
    """Plan a sequence of bites under the current constraints.

    Parameters
    ----------
    manager : FoodStateManager
        Current food state/availability.
    cravings : list of str
        Requested cravings (case-insensitive names).
    cravings_satisfied : int
        Number of cravings already satisfied today.
    remaining_calories : int
        Calorie budget for this plan.
    server_mult : float, optional
        Server skill gain multiplier. Default is 1.0.
    dinner_party_mult : float, optional
        Dinner party multiplier (1.0-3.0). Default is 1.0.

    Returns
    -------
    list[MealPlanItem]
        Ordered plan with per-bite deltas and tags.
    """
    current_sp = manager.get_current_sp(
        cravings,
        cravings_satisfied,
        server_mult=server_mult,
        dinner_party_mult=dinner_party_mult,
    )
    variety_count_now = len(manager.unique_variety_foods())
    meal_plan = []
    cravings = [normalize_name(name) for name in cravings]
    cravings = validate_cravings(manager, cravings)[0]

    for _ in range(MAX_ITERATIONS):
        if remaining_calories <= 0:
            break

        # craving-first if feasible, else ranked best
        food = _pick_feasible_craving(
            manager,
            cravings,
            remaining_calories,
            cravings_satisfied,
        )
        if not food:
            food, _ = _choose_next_bite(
                manager,
                remaining_calories,
                cravings,
                cravings_satisfied,
            )
            if not food:
                logger.info(
                    "No suitable food with %d remaining cal",
                    remaining_calories,
                )
                break

        logger.info(
            "Consume %s | %d cal",
            food.name,
            food.calories,
        )
        (
            current_sp,
            remaining_calories,
            cravings_satisfied,
            variety_count_now,
        ) = _apply_bite(
            manager,
            food,
            current_sp=current_sp,
            remaining_calories=remaining_calories,
            cravings=cravings,
            cravings_satisfied=cravings_satisfied,
            variety_count_now=variety_count_now,
            meal_plan=meal_plan,
            server_mult=server_mult,
            dinner_party_mult=dinner_party_mult,
        )

    else:
        logger.warning(
            "Loop exited after max iterations (%d).",
            MAX_ITERATIONS,
        )

    return meal_plan
