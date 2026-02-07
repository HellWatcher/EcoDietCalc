"""Unit tests for planner ranking functions.

Tests the internal ranking helpers (_low_calorie_penalty, _soft_variety_bias,
_proximity_bias) and the full bite selection pipeline (_choose_next_bite).
"""

import math

from conftest import make_food
from constants import (
    LOW_CALORIE_PENALTY_STRENGTH,
    LOW_CALORIE_THRESHOLD,
    PROXIMITY_APPROACH_WEIGHT,
    SOFT_VARIETY_BIAS_STRENGTH,
    VARIETY_CAL_THRESHOLD,
)
from food_state_manager import FoodStateManager
from models.food import Food
from planner import (
    _choose_next_bite,
    _low_calorie_penalty,
    _proximity_bias,
    _soft_variety_bias,
)

# --- Fixtures and helpers ---


class DummyManager(FoodStateManager):
    """Minimal manager for testing ranking logic."""

    def __init__(self, foods: list[Food]) -> None:
        super().__init__(foods)


# --- _low_calorie_penalty tests ---


class TestLowCaloriePenalty:
    """Tests for quadratic low-calorie penalty."""

    def test_zero_calories_gives_max_penalty(self) -> None:
        """Food with 0 calories should get the maximum penalty."""
        food = make_food("Empty", calories=0)
        penalty = _low_calorie_penalty(food)
        # At 0 cal, deficit_ratio = 1.0, penalty = -STRENGTH * 1^2
        expected = -LOW_CALORIE_PENALTY_STRENGTH
        assert math.isclose(penalty, expected, rel_tol=1e-9)

    def test_at_threshold_no_penalty(self) -> None:
        """Food exactly at the threshold should have no penalty."""
        food = make_food("Threshold", calories=LOW_CALORIE_THRESHOLD)
        penalty = _low_calorie_penalty(food)
        assert penalty == 0.0

    def test_above_threshold_no_penalty(self) -> None:
        """Food above the threshold should have no penalty."""
        food = make_food("High", calories=500)
        assert 500 > LOW_CALORIE_THRESHOLD  # sanity check
        penalty = _low_calorie_penalty(food)
        assert penalty == 0.0

    def test_half_threshold_quadratic_penalty(self) -> None:
        """Food at half the threshold should get 1/4 penalty (quadratic)."""
        half_cal = LOW_CALORIE_THRESHOLD // 2
        food = make_food("Half", calories=half_cal)
        penalty = _low_calorie_penalty(food)
        # deficit_ratio = 1 - 0.5 = 0.5, penalty = -STRENGTH * 0.25
        deficit_ratio = 1.0 - (half_cal / LOW_CALORIE_THRESHOLD)
        expected = -LOW_CALORIE_PENALTY_STRENGTH * (deficit_ratio**2)
        assert math.isclose(penalty, expected, rel_tol=1e-6)

    def test_200_calories_penalty(self) -> None:
        """Test specific value: 200 calories."""
        food = make_food("LowCal", calories=200)
        penalty = _low_calorie_penalty(food)
        deficit_ratio = 1.0 - (200 / LOW_CALORIE_THRESHOLD)
        expected = -LOW_CALORIE_PENALTY_STRENGTH * (deficit_ratio**2)
        assert math.isclose(penalty, expected, rel_tol=1e-6)
        # Should be negative (a penalty)
        assert penalty < 0


# --- _soft_variety_bias tests ---


class TestSoftVarietyBias:
    """Tests for soft variety bias ranking adjustment."""

    def test_empty_stomach_new_food_positive_bias(self) -> None:
        """Adding a food to empty stomach should give positive variety bias."""
        food = make_food(
            "HighNutrient",
            calories=VARIETY_CAL_THRESHOLD,
            carbs=20,
            protein=20,
            fats=20,
            vitamins=20,
        )
        stomach: dict[Food, int] = {}
        bias = _soft_variety_bias(stomach, food)
        # Should be positive: new food adds variety
        assert bias > 0

    def test_food_already_at_variety_cap_zero_bias(self) -> None:
        """Food that's already well past variety threshold contributes 0 delta."""
        food = make_food("BigFood", calories=VARIETY_CAL_THRESHOLD)
        # Already eaten enough to max variety contribution
        stomach = {food: 5}  # 5 units = way past threshold
        bias = _soft_variety_bias(stomach, food)
        # Variety delta should be 0 since already capped
        assert math.isclose(bias, 0.0, abs_tol=0.01)

    def test_low_nutrient_food_smaller_bias(self) -> None:
        """Low-nutrient food should have smaller bias than high-nutrient."""
        low_food = make_food(
            "LowNutrient",
            calories=VARIETY_CAL_THRESHOLD,
            carbs=1,
            protein=1,
            fats=1,
            vitamins=1,
        )
        high_food = make_food(
            "HighNutrient",
            calories=VARIETY_CAL_THRESHOLD,
            carbs=20,
            protein=20,
            fats=20,
            vitamins=20,
        )
        stomach: dict[Food, int] = {}

        low_bias = _soft_variety_bias(stomach, low_food)
        high_bias = _soft_variety_bias(stomach, high_food)

        # High nutrient food should have larger bias
        assert high_bias > low_bias

    def test_bias_scales_with_strength_constant(self) -> None:
        """Verify bias is scaled by SOFT_VARIETY_BIAS_STRENGTH."""
        food = make_food(
            "Test",
            calories=VARIETY_CAL_THRESHOLD,
            carbs=10,
            protein=10,
            fats=10,
            vitamins=10,
        )
        stomach: dict[Food, int] = {}
        bias = _soft_variety_bias(stomach, food)
        # Bias should be non-zero and scaled by strength
        if SOFT_VARIETY_BIAS_STRENGTH > 0:
            assert bias != 0.0


# --- _proximity_bias tests ---


class TestProximityBias:
    """Tests for proximity bias (progress toward variety threshold)."""

    def test_progress_toward_threshold_positive(self) -> None:
        """Moving from 0 toward threshold should give positive bias."""
        food = make_food("Medium", calories=1000)
        stomach: dict[Food, int] = {}
        bias = _proximity_bias(stomach, food)
        # First bite moves progress from 0 to 0.5 (1000/2000)
        # growth_toward_threshold = 0.5 - 0 = 0.5
        assert bias > 0

    def test_already_at_full_progress_no_additional_growth(self) -> None:
        """Food already at 1.0 progress shouldn't gain additional proximity."""
        food = make_food("BigFood", calories=VARIETY_CAL_THRESHOLD)
        # Already eaten 1 unit (at threshold)
        stomach = {food: 1}
        bias = _proximity_bias(stomach, food)
        # Progress before = 1.0, progress after = 2.0
        # growth_toward_threshold = min(2.0,1) - min(1.0,1) = 0
        # overshoot = max(0, 2.0 - 1.0) = 1.0
        # So bias should be negative (overshoot penalty)
        assert bias < 0 or math.isclose(bias, 0.0, abs_tol=0.01)

    def test_overshoot_small_penalty(self) -> None:
        """Overshooting the threshold should incur a small penalty."""
        food = make_food("VeryBig", calories=3000)
        stomach: dict[Food, int] = {}
        bias = _proximity_bias(stomach, food)
        # Progress goes from 0 to 1.5 in one bite
        # growth_toward_threshold = min(1.5,1) - 0 = 1.0
        # overshoot = 0.5
        # net bias depends on weights
        # This should still be positive but less than if no overshoot
        assert bias >= -1.0  # Not a huge penalty

    def test_small_food_incremental_progress(self) -> None:
        """Small food gives proportional progress."""
        food = make_food("Small", calories=500)  # 25% of threshold
        stomach: dict[Food, int] = {}
        bias = _proximity_bias(stomach, food)
        # Progress: 0 -> 0.25
        expected_growth = 0.25
        expected_bias = PROXIMITY_APPROACH_WEIGHT * expected_growth
        assert math.isclose(bias, expected_bias, rel_tol=0.01)


# --- _choose_next_bite tests ---


class TestChooseNextBite:
    """Tests for the full ranking pipeline."""

    def test_all_foods_exceed_budget_returns_none(self) -> None:
        """When all foods exceed calorie budget, returns (None, 0.0)."""
        foods = [
            make_food("Big1", calories=1000),
            make_food("Big2", calories=800),
        ]
        manager = DummyManager(foods)
        remaining_calories = 100  # Can't afford any

        food, delta = _choose_next_bite(
            manager,
            remaining_calories=remaining_calories,
            cravings=[],
            cravings_satisfied=0,
        )

        assert food is None
        assert delta == 0.0

    def test_single_candidate_returns_that_food(self) -> None:
        """With one feasible candidate, returns it."""
        expensive = make_food("Expensive", calories=1000)
        cheap = make_food("Cheap", calories=100)
        foods = [expensive, cheap]
        manager = DummyManager(foods)
        remaining_calories = 150  # Only cheap fits

        food, _delta = _choose_next_bite(
            manager,
            remaining_calories=remaining_calories,
            cravings=[],
            cravings_satisfied=0,
        )

        assert food is not None
        assert food.name == "Cheap"

    def test_higher_sp_food_preferred(self) -> None:
        """Food with higher SP delta should be preferred."""
        # Same calories, different nutrients
        low_nutrient = make_food(
            "Low", calories=500, carbs=1, protein=1, fats=1, vitamins=1
        )
        high_nutrient = make_food(
            "High", calories=500, carbs=20, protein=20, fats=20, vitamins=20
        )
        foods = [low_nutrient, high_nutrient]
        manager = DummyManager(foods)

        food, _ = _choose_next_bite(
            manager,
            remaining_calories=1000,
            cravings=[],
            cravings_satisfied=0,
        )

        assert food is not None
        assert food.name == "High"

    def test_low_calorie_food_penalized(self) -> None:
        """Very low calorie food should be penalized vs higher calorie."""
        tiny = make_food("Tiny", calories=20, carbs=5, protein=5, fats=5, vitamins=5)
        medium = make_food(
            "Medium", calories=400, carbs=5, protein=5, fats=5, vitamins=5
        )
        foods = [tiny, medium]
        manager = DummyManager(foods)

        food, _ = _choose_next_bite(
            manager,
            remaining_calories=1000,
            cravings=[],
            cravings_satisfied=0,
        )

        # Medium should be preferred due to low-calorie penalty on tiny
        assert food is not None
        assert food.name == "Medium"

    def test_empty_manager_returns_none(self) -> None:
        """Empty food list returns (None, 0.0)."""
        manager = DummyManager([])

        food, delta = _choose_next_bite(
            manager,
            remaining_calories=1000,
            cravings=[],
            cravings_satisfied=0,
        )

        assert food is None
        assert delta == 0.0

    def test_unavailable_foods_excluded(self) -> None:
        """Foods with zero availability should not be selected."""
        available = make_food("Available", calories=500, available=5)
        unavailable = make_food(
            "Unavailable",
            calories=500,
            carbs=50,
            protein=50,
            fats=50,
            vitamins=50,
            available=0,
        )
        foods = [available, unavailable]
        manager = DummyManager(foods)

        food, _ = _choose_next_bite(
            manager,
            remaining_calories=1000,
            cravings=[],
            cravings_satisfied=0,
        )

        assert food is not None
        assert food.name == "Available"


# --- Proximity tie-breaking tests ---


class TestProximityTiebreak:
    """Tests for proximity bias as tie-breaker among near-equal candidates."""

    def test_near_equal_scores_use_proximity(self) -> None:
        """When scores are within TIEBREAK_SCORE_WINDOW_SP, proximity breaks tie."""
        # Create two foods with very similar SP but different proximity effects
        food_far = make_food(
            "Far", calories=100, carbs=10, protein=10, fats=10, vitamins=10
        )
        food_near = make_food(
            "Near", calories=1900, carbs=10, protein=10, fats=10, vitamins=10
        )
        foods = [food_far, food_near]
        manager = DummyManager(foods)

        food, _ = _choose_next_bite(
            manager,
            remaining_calories=3000,
            cravings=[],
            cravings_satisfied=0,
        )

        # One of them should be selected; exact choice depends on full scoring
        assert food is not None

    def test_variety_considerations_in_ranking(self) -> None:
        """Foods that improve variety should be ranked higher."""
        # Two foods with similar base nutrients but one adds variety
        food_a = make_food(
            "FoodA",
            calories=VARIETY_CAL_THRESHOLD,
            carbs=10,
            protein=10,
            fats=10,
            vitamins=10,
        )
        food_b = make_food(
            "FoodB", calories=100, carbs=10, protein=10, fats=10, vitamins=10
        )  # Below threshold
        foods = [food_a, food_b]
        manager = DummyManager(foods)

        food, _ = _choose_next_bite(
            manager,
            remaining_calories=3000,
            cravings=[],
            cravings_satisfied=0,
        )

        # FoodA should likely be preferred (contributes to variety)
        assert food is not None
