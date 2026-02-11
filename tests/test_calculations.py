import math
from collections import (
    namedtuple,
)

from calculations import (
    calculate_nutrition_multiplier,
    evaluate_bonus_with_addition,
    get_sp,
    get_sp_delta,
    get_tastiness_bonus,
    get_variety_bonus,
    simulate_stomach_with_added_food,
    sum_all_weighted_nutrients,
)
from constants import (
    CRAVING_SATISFIED_FRAC,
    TASTINESS_WEIGHT,
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
        "fat",
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


def stomach_dict(*items):
    """stomach_dict((food, qty), (food, qty), ...)"""
    return dict(items)


def _density_sum(stomach) -> float:
    density, _ = sum_all_weighted_nutrients(stomach)  # dict of floats
    return density["carbs"] + density["protein"] + density["fat"] + density["vitamins"]


def test_get_tastiness_bonus_matches_definition():
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
        * TASTINESS_WEIGHT
    )
    assert abs(get_tastiness_bonus(st) - expected) < 1e-9


def test_variety_bonus_is_capped_and_monotonic():
    x1 = get_variety_bonus(1)
    x2 = get_variety_bonus(5)
    x3 = get_variety_bonus(100)
    assert 0.0 <= x1 <= x2 <= x3 <= VARIETY_BONUS_CAP_PP


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


def test_tastiness_delta_for_added_unit_matches_manual_diff():
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
    manual_delta = get_tastiness_bonus(after) - get_tastiness_bonus(st)
    # Import lazily to avoid circulars if any
    from calculations import tastiness_delta_for_added_unit

    assert abs(tastiness_delta_for_added_unit(st, a) - manual_delta) < 1e-9


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


# ---- Balanced diet ratio tests ----


def test_balanced_diet_ratio_includes_zero_nutrients():
    """Zero nutrients must count toward min, giving ratio=0 (max penalty)."""
    from calculations import calculate_balanced_diet_ratio

    # Pumpkin-like: C=5, P=1, F=0, V=2 — fat is zero
    nutrients = [5.0, 1.0, 0.0, 2.0]
    ratio = calculate_balanced_diet_ratio(nutrients)
    assert ratio == 0.0, f"Expected 0.0 (fat=0 means min=0), got {ratio}"


def test_balanced_diet_bonus_with_zero_nutrient():
    """A zero nutrient should give -50 pp (maximum penalty)."""
    from calculations import calculate_balanced_diet_bonus

    nutrients = [5.0, 1.0, 0.0, 2.0]
    bonus = calculate_balanced_diet_bonus(nutrients)
    assert bonus == -50.0, f"Expected -50.0 pp, got {bonus}"


def test_balanced_diet_ratio_all_equal():
    """Perfectly balanced nutrients give ratio=1.0."""
    from calculations import calculate_balanced_diet_ratio

    nutrients = [3.0, 3.0, 3.0, 3.0]
    assert calculate_balanced_diet_ratio(nutrients) == 1.0


def test_balanced_diet_ratio_all_zero():
    """All-zero nutrients give ratio=0.0."""
    from calculations import calculate_balanced_diet_ratio

    assert calculate_balanced_diet_ratio([0.0, 0.0, 0.0, 0.0]) == 0.0


def test_sp_matches_game_pumpkin_scenario():
    """Reproduce the in-game scenario: 6 pumpkins, SP should be 16."""
    pumpkin = food("Pumpkin", 340, c=5, p=1, f=0, v=2, t=0)
    stomach = {pumpkin: 6}
    # No cravings, no variety (below threshold with game's accounting),
    # but our variety check says 6*340=2040 >= 2000, so 1 qualifying food.
    # Game shows Variety=1.0 (no bonus), so we test with empty variety set
    # to match game behavior where variety=1.0 means no variety multiplier.
    sp = get_sp(stomach, [], 0, set(), server_mult=1.0, dinner_party_mult=1.0)
    # density=8, balanced_diet ratio=0 (fat=0) → -50pp → mult=0.5
    # nutrition_sp = 8 * 0.5 = 4, SP = 4 + 12 = 16
    assert abs(sp - 16.0) < 0.1, f"Expected ~16.0, got {sp}"
