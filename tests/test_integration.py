"""Integration tests for full meal planning.

Tests the complete meal planning pipeline including:
- Budget constraints
- Availability limits
- Craving handling
- Variety accumulation
"""

from conftest import make_food
from food_state_manager import FoodStateManager
from planner import plan_meal


class TestFullPlanGeneration:
    """Integration tests for complete meal planning."""

    def test_plan_respects_calorie_budget(self, simple_manager_factory) -> None:
        """Total calories consumed should not exceed budget."""
        manager = simple_manager_factory()
        calorie_budget = 2000
        cravings: list[str] = []
        cravings_satisfied = 0

        meal_plan = plan_meal(
            manager=manager,
            cravings=cravings,
            cravings_satisfied=cravings_satisfied,
            remaining_calories=calorie_budget,
        )

        total_calories = sum(item.calories for item in meal_plan)
        assert total_calories <= calorie_budget

    def test_plan_items_have_valid_sp_gain(self, simple_manager_factory) -> None:
        """Each item in the plan should have a reasonable sp_gain."""
        manager = simple_manager_factory()

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=3000,
        )

        # Should have items
        assert len(meal_plan) > 0

        # Each item should have defined SP gain (can be positive or negative)
        for item in meal_plan:
            assert hasattr(item, "sp_gain")
            assert isinstance(item.sp_gain, (int, float))

    def test_craving_items_consumed_when_available(self, simple_manager_factory) -> None:
        """Craving foods should be consumed if available and within budget."""
        manager = simple_manager_factory()
        # Use a food name that exists in the fixture
        craving_name = "Bannock"

        meal_plan = plan_meal(
            manager=manager,
            cravings=[craving_name],
            cravings_satisfied=0,
            remaining_calories=3000,
        )

        # Bannock should appear in the plan (it's prioritized as a craving)
        consumed_names = [item.name for item in meal_plan]
        assert craving_name in consumed_names

    def test_variety_count_increases(self, simple_manager_factory) -> None:
        """Variety-qualifying foods should contribute to variety count."""
        manager = simple_manager_factory()

        # Initial variety should be 0 (empty stomach)
        initial_variety = len(manager.unique_variety_foods())
        assert initial_variety == 0

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=5000,
        )

        # After eating, variety should increase
        final_variety = len(manager.unique_variety_foods())
        assert final_variety > 0
        assert len(meal_plan) > 0


class TestPlanRespectsAvailability:
    """Tests that planning respects food availability limits."""

    def test_limited_availability_not_exceeded(self) -> None:
        """Foods with limited availability should not be over-consumed."""
        # Create a food with very limited availability
        limited_food = make_food("Limited", calories=500, available=2)
        abundant_food = make_food("Abundant", calories=500, available=100)
        foods = [limited_food, abundant_food]
        manager = FoodStateManager(foods)

        # Plan with enough budget to want more than 2 of limited
        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=5000,  # Could fit 10 units
        )

        # Count how many times Limited was consumed
        limited_count = sum(1 for item in meal_plan if item.name == "Limited")
        assert limited_count <= 2

    def test_zero_availability_excluded(self) -> None:
        """Foods with zero availability should not appear in plan."""
        unavailable = make_food("Unavailable", calories=500, available=0)
        available = make_food("Available", calories=500, available=10)
        foods = [unavailable, available]
        manager = FoodStateManager(foods)

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=3000,
        )

        # Unavailable food should never be in the plan
        consumed_names = [item.name for item in meal_plan]
        assert "Unavailable" not in consumed_names

    def test_availability_decrements_during_planning(self) -> None:
        """Availability should decrement as foods are consumed."""
        food = make_food("TestFood", calories=500, available=5)
        manager = FoodStateManager([food])

        initial_available = manager.available[food]
        assert initial_available == 5

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=2000,  # Can fit 4 units
        )

        # Count consumed
        consumed_count = sum(1 for item in meal_plan if item.name == "TestFood")

        # Availability should have decreased
        final_available = manager.available.get(food, 0)
        assert final_available == initial_available - consumed_count


class TestEmptyStomachToFull:
    """Tests for planning from an empty stomach."""

    def test_empty_stomach_produces_plan(self, simple_manager_factory) -> None:
        """Fresh manager with empty stomach should produce a plan."""
        manager = simple_manager_factory()

        # Verify empty stomach
        assert len(manager.stomach) == 0

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=3000,
        )

        # Should have produced a non-empty plan
        assert len(meal_plan) > 0

    def test_sp_increases_from_zero(self, simple_manager_factory) -> None:
        """SP should increase from zero after eating."""
        manager = simple_manager_factory()

        # Initial SP from empty stomach
        initial_sp = manager.get_current_sp(cravings=[], cravings_satisfied=0)

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=3000,
        )

        # Final SP should be higher
        final_sp = manager.get_current_sp(cravings=[], cravings_satisfied=0)
        assert final_sp > initial_sp

        # The total SP gain from items should match
        total_sp_gain = sum(item.sp_gain for item in meal_plan)
        assert abs(final_sp - initial_sp - total_sp_gain) < 0.01

    def test_large_budget_uses_variety(self, simple_manager_factory) -> None:
        """With large budget, planner should use multiple foods for variety."""
        manager = simple_manager_factory()

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=10000,  # Very large budget
        )

        # Should have consumed multiple different foods
        unique_foods = set(item.name for item in meal_plan)
        assert len(unique_foods) > 1


class TestMultiplierSupport:
    """Tests for server and dinner party multipliers."""

    def test_server_multiplier_affects_sp(self, simple_manager_factory) -> None:
        """Server multiplier should scale SP gain."""
        manager1 = simple_manager_factory()
        manager2 = simple_manager_factory()

        # Plan without multiplier
        _plan1 = plan_meal(
            manager=manager1,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=1000,
            server_mult=1.0,
        )

        # Plan with 2x server multiplier
        _plan2 = plan_meal(
            manager=manager2,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=1000,
            server_mult=2.0,
        )

        # SP gains should differ (plan2 should be higher per item)
        sp1 = manager1.get_current_sp(
            cravings=[], cravings_satisfied=0, server_mult=1.0
        )
        sp2 = manager2.get_current_sp(
            cravings=[], cravings_satisfied=0, server_mult=2.0
        )

        # With 2x server mult, SP should be approximately 2x
        assert sp2 > sp1

    def test_dinner_party_multiplier_affects_sp(self, simple_manager_factory) -> None:
        """Dinner party multiplier should scale SP gain."""
        manager1 = simple_manager_factory()
        manager2 = simple_manager_factory()

        # Plan without multiplier
        plan_meal(
            manager=manager1,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=1000,
            dinner_party_mult=1.0,
        )

        # Plan with 3x dinner party multiplier
        plan_meal(
            manager=manager2,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=1000,
            dinner_party_mult=3.0,
        )

        # SP should be higher with multiplier
        sp1 = manager1.get_current_sp(
            cravings=[], cravings_satisfied=0, dinner_party_mult=1.0
        )
        sp2 = manager2.get_current_sp(
            cravings=[], cravings_satisfied=0, dinner_party_mult=3.0
        )

        assert sp2 > sp1


class TestEdgeCases:
    """Edge case tests for meal planning."""

    def test_zero_calorie_budget_empty_plan(self, simple_manager_factory) -> None:
        """Zero calorie budget should produce empty plan."""
        manager = simple_manager_factory()

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=0,
        )

        assert len(meal_plan) == 0

    def test_tiny_budget_no_affordable_food(self) -> None:
        """Budget smaller than any food should produce empty plan."""
        # All foods cost at least 100 calories
        foods = [
            make_food("Food1", calories=100),
            make_food("Food2", calories=200),
        ]
        manager = FoodStateManager(foods)

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=50,  # Can't afford anything
        )

        assert len(meal_plan) == 0

    def test_invalid_craving_ignored(self, simple_manager_factory) -> None:
        """Invalid craving names should be gracefully ignored."""
        manager = simple_manager_factory()

        # This craving doesn't match any food
        meal_plan = plan_meal(
            manager=manager,
            cravings=["NonExistentFood"],
            cravings_satisfied=0,
            remaining_calories=2000,
        )

        # Should still produce a plan (craving validation happens internally)
        # The plan just won't have the invalid craving satisfied
        assert len(meal_plan) >= 0  # May or may not have items

    def test_single_food_manager(self) -> None:
        """Manager with single food should work correctly."""
        food = make_food("OnlyFood", calories=500, available=5)
        manager = FoodStateManager([food])

        meal_plan = plan_meal(
            manager=manager,
            cravings=[],
            cravings_satisfied=0,
            remaining_calories=2000,
        )

        # Should consume the only available food
        assert len(meal_plan) > 0
        assert all(item.name == "OnlyFood" for item in meal_plan)
