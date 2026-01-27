import math
from collections import (
    namedtuple,
)

from calculations import (
    calculate_nutrition_multiplier,
    evaluate_bonus_with_addition,
    get_sp,
    get_sp_delta,
    get_taste_bonus,
    get_variety_bonus,
    simulate_stomach_with_added_food,
    sum_all_weighted_nutrients,
)
from constants import (
    CRAVING_BONUS_PP,
    CRAVING_SATISFIED_FRAC,
    TASTE_WEIGHT,
    TASTINESS_MULTIPLIERS,
    VARIETY_BONUS_CAP_PP,
    VARIETY_CAL_THRESHOLD,
)

# ---- Hashable Food-like for dict keys ----
FoodLike = namedtuple(
    "FoodLike",
    [
        "name",
        "calories",
        "carbs",
        "protein",
        "fats",
        "vitamins",
        "tastiness",
    ],
)


def food(
    name,
    cal,
    c=0,
    p=0,
    f=0,
    v=0,
    t=0,
):
    return FoodLike(
        name,
        cal,
        c,
        p,
        f,
        v,
        t,
    )


def _S(stomach) -> float:
    # sum_all_weighted_nutrients may return (density_dict, total_cal) or just the dict
    out = sum_all_weighted_nutrients(stomach)
    density = out[0] if isinstance(out, tuple) else out
    return float(
        density["carbs"] + density["protein"] + density["fats"] + density["vitamins"]
    )


def stomach_dict(*items):
    """stomach_dict((food, qty), (food, qty), ...)"""
    return dict(items)


def _density_sum(stomach) -> float:
    density, _ = sum_all_weighted_nutrients(stomach)  # dict of floats
    return density["carbs"] + density["protein"] + density["fats"] + density["vitamins"]


def test_get_taste_bonus_matches_definition():
    a = food(
        "sweet",
        200,
        t=3,
    )
    b = food(
        "bitter",
        200,
        t=-3,
    )
    st = stomach_dict(
        (
            a,
            1,
        ),
        (
            b,
            1,
        ),
    )

    expected = (
        (TASTINESS_MULTIPLIERS[3] * 200 + TASTINESS_MULTIPLIERS[-3] * 200)
        / (200 + 200)
        * 100.0
        * TASTE_WEIGHT
    )
    assert abs(get_taste_bonus(st) - expected) < 1e-9


def test_variety_bonus_is_capped_and_monotonic():
    x1 = get_variety_bonus(1)
    x2 = get_variety_bonus(5)
    x3 = get_variety_bonus(100)
    assert 0.0 <= x1 <= x2 <= x3 <= VARIETY_BONUS_CAP_PP


def test_calculate_nutrition_multiplier_includes_craving_bonus():
    a = food(
        "apple",
        150,
        c=15,
    )
    b = food(
        "bread",
        200,
        c=40,
    )
    st = stomach_dict(
        (
            a,
            1,
        ),
        (
            b,
            1,
        ),
    )
    cravings = [
        "apple",
    ]  # one craved item present
    uniq_24h = {
        "apple",
        "bread",
    }  # any set is fine for this test

    val = calculate_nutrition_multiplier(
        st,
        cravings,
        uniq_24h,
    )
    # Should be some baseline (balance + variety + taste) plus exactly CRAVING_BONUS_PP
    val_no_crave = calculate_nutrition_multiplier(
        st,
        [],
        uniq_24h,
    )
    assert abs((val - val_no_crave) - CRAVING_BONUS_PP) < 1e-9


def test_get_sp_satisfied_cravings_fraction_scales_total():
    a = food("fish", 300, p=30)
    st = stomach_dict((a, 2))  # calories/qty shouldn't change the delta
    cravings = []
    uniq_24h = {"fish"}

    base = get_sp(
        st, cravings=cravings, unique_foods_24h=uniq_24h, cravings_satisfied=0
    )
    plus1 = get_sp(
        st, cravings=cravings, unique_foods_24h=uniq_24h, cravings_satisfied=1
    )

    expected_delta = _density_sum(st) * CRAVING_SATISFIED_FRAC  # no * calories or * qty
    assert abs((plus1 - base) - expected_delta) < 1e-9


def test_taste_delta_for_added_unit_matches_manual_diff():
    a = food(
        "nice",
        200,
        t=3,
    )
    b = food(
        "meh",
        200,
        t=0,
    )
    st = stomach_dict(
        (
            a,
            1,
        ),
        (
            b,
            1,
        ),
    )
    after = simulate_stomach_with_added_food(
        st,
        a,
    )
    manual_delta = get_taste_bonus(after) - get_taste_bonus(st)
    # Import lazily to avoid circulars if any
    from calculations import taste_delta_for_added_unit

    assert abs(taste_delta_for_added_unit(st, a) - manual_delta) < 1e-9


def test_sp_delta_matches_difference(simple_manager_factory):
    # Build a tiny stomach with 2–3 foods; pick one to add.
    m = simple_manager_factory()
    foods = list(m.foods.values())[:3]
    f = foods[0]
    cravings, cs = [], 0

    from calculations import (
        _unique_variety_names,
        get_sp,
        get_sp_delta,
        simulate_stomach_with_added_food,
    )

    before = dict(m.stomach)
    after = simulate_stomach_with_added_food(before, f)

    truth = get_sp(after, cravings, cs, _unique_variety_names(after)) - get_sp(
        before, cravings, cs, _unique_variety_names(before)
    )
    approx = get_sp_delta(f, before, cravings, cs)
    assert abs(truth - approx) < 1e-9


def test_meal_plan_uses_true_delta(simple_manager_factory):
    m = simple_manager_factory()
    from calculations import (
        _unique_variety_names,
        get_sp,
        simulate_stomach_with_added_food,
    )
    from planner import plan_meal

    # Snapshot BEFORE planning (plan_meal mutates manager.stomach)
    start_stomach = dict(m.stomach)

    cravings, cs = [], 0
    cal_budget = 1000
    meal = plan_meal(
        m,
        cravings=cravings,
        cravings_satisfied=cs,
        remaining_calories=cal_budget,
    )

    # Reconstruct deltas by simulating each chosen bite from the pre-plan state
    stomach = dict(start_stomach)
    for item in meal:
        before = dict(stomach)

        # Find the actual Food instance by name
        food = next(f for f in m.foods.values() if f.name == item.name)

        after = simulate_stomach_with_added_food(before, food)

        truth = get_sp(after, cravings, cs, _unique_variety_names(after)) - get_sp(
            before, cravings, cs, _unique_variety_names(before)
        )

        assert abs(item.sp_gain - truth) < 1e-6

        # Advance local stomach for the next bite
        stomach = after


def test_variety_set_hard_threshold(simple_manager_factory):
    m = simple_manager_factory()
    # One food below the threshold shouldn't contribute to variety count
    low = next(f for f in m.foods.values() if f.calories < VARIETY_CAL_THRESHOLD)
    hi = next(f for f in m.foods.values() if f.calories >= VARIETY_CAL_THRESHOLD)
    m.stomach[low] = 1
    m.stomach[hi] = 1
    from calculations import variety_count

    assert variety_count(m.stomach) == 1


def test_cravings_satisfied_scales_density_sum_only():
    # With one food, density_sum = 1+2+3+4 = 10
    food = FoodLike("Apple", 500, 1.0, 2.0, 3.0, 4.0, 0)
    stomach, uniq = {food: 1}, set()
    sp0 = get_sp(stomach, cravings=[], cravings_satisfied=0, unique_foods_24h=uniq)
    sp1 = get_sp(stomach, cravings=[], cravings_satisfied=1, unique_foods_24h=uniq)

    expected_delta = _density_sum(stomach) * CRAVING_SATISFIED_FRAC
    assert math.isclose(sp1 - sp0, expected_delta, rel_tol=1e-9, abs_tol=1e-9)


def test_per_item_craving_bonus_counts_unique_foods_not_quantity():
    # Per-item craving bonus should apply once per present food, not per quantity
    food = FoodLike("Apple", 500, 1.0, 2.0, 3.0, 4.0, 0)
    uniq = set()
    S = _S({food: 1})
    expected = S * (CRAVING_BONUS_PP / 100.0)
    d1 = get_sp({food: 1}, ["apple"], 0, uniq) - get_sp({food: 1}, [], 0, uniq)
    d2 = get_sp({food: 2}, ["apple"], 0, uniq) - get_sp({food: 2}, [], 0, uniq)
    assert math.isclose(d1, expected, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(d2, expected, rel_tol=1e-9, abs_tol=1e-9)


def test_evaluate_bonus_with_addition_matches_direct_and_grows_on_threshold():
    # If a bite newly meets the per-food variety threshold, variety set must update
    hi = FoodLike("HiFood", VARIETY_CAL_THRESHOLD, 1, 1, 1, 1, 0)
    before = {}
    predicted_pp = evaluate_bonus_with_addition(
        before, hi, cravings=[], variety_reference=set()
    )
    after = simulate_stomach_with_added_food(before, hi)
    direct_pp = calculate_nutrition_multiplier(
        after, cravings=[], unique_foods_24h={hi.name.lower()}
    )
    assert math.isclose(predicted_pp, direct_pp, rel_tol=1e-9, abs_tol=1e-9)
    assert predicted_pp >= calculate_nutrition_multiplier(
        before, cravings=[], unique_foods_24h=set()
    )


def test_get_sp_delta_equals_difference():
    # get_sp_delta must equal SP(after) - SP(before) using the same variety logic
    food = FoodLike("Apple", 500, 1.0, 2.0, 3.0, 4.0, 0)
    before = {}
    after = simulate_stomach_with_added_food(before, food)
    delta = get_sp_delta(food, before, cravings=[], cravings_satisfied=0)
    diff = get_sp(after, [], 0, set()) - get_sp(before, [], 0, set())
    assert math.isclose(delta, diff, rel_tol=1e-9, abs_tol=1e-9)


def test_simulate_stomach_with_added_food_does_not_mutate():
    food = FoodLike("Apple", 500, 1.0, 2.0, 3.0, 4.0, 0)
    stomach = {food: 1}
    clone = simulate_stomach_with_added_food(stomach, food)
    assert stomach.get(food) == 1
    assert clone.get(food) == 2


def test_craving_bonus_capped_at_three():
    """Craving matches should be capped at CRAVING_MAX_COUNT (3)."""
    from constants import CRAVING_MAX_COUNT
    from calculations import calculate_nutrition_multiplier

    # Create 5 foods, all matching cravings
    foods = [FoodLike(f"Food{i}", 600, 10, 10, 10, 10, 2) for i in range(5)]
    stomach = {f: 1 for f in foods}
    cravings = [f"food{i}" for i in range(5)]
    unique = set()

    # With 5 matches, should only get bonus for 3
    bonus_5 = calculate_nutrition_multiplier(stomach, cravings, unique)

    # With 3 matches, should get same craving bonus
    stomach_3 = {f: 1 for f in foods[:3]}
    cravings_3 = [f"food{i}" for i in range(3)]
    bonus_3 = calculate_nutrition_multiplier(stomach_3, cravings_3, unique)

    # The craving portion should be capped (other bonuses differ due to different stomach)
    # Just verify that 5 matches doesn't give 5x the per-match bonus
    from constants import CRAVING_BONUS_PP

    max_craving_bonus = CRAVING_MAX_COUNT * CRAVING_BONUS_PP
    # Extract just the craving portion by comparing with no cravings
    bonus_no_crave = calculate_nutrition_multiplier(stomach, [], unique)
    craving_portion = bonus_5 - bonus_no_crave
    assert craving_portion <= max_craving_bonus + 0.01  # Allow small float tolerance
