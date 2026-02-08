"""Direct unit tests for FoodStateManager.

Covers all public methods with real instances (no mocks).
Uses ``make_food()`` from ``conftest.py`` for test data construction.
"""

from __future__ import annotations

from unittest.mock import patch


from conftest import make_food
from food_state_manager import FoodStateManager
from models.food import Food

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(*foods: Food) -> FoodStateManager:
    """Shorthand to build a manager from varargs."""
    return FoodStateManager(list(foods))


# ---------------------------------------------------------------------------
# TestGetFood
# ---------------------------------------------------------------------------


class TestGetFood:
    """Case-insensitive lookup by name."""

    def test_exact_name(self) -> None:
        mgr = _make_manager(make_food("Bannock", 600))
        result = mgr.get_food("Bannock")
        assert result is not None
        assert result.name == "Bannock"

    def test_case_insensitive(self) -> None:
        mgr = _make_manager(make_food("Bannock", 600))
        assert mgr.get_food("bannock") is not None
        assert mgr.get_food("BANNOCK") is not None
        assert mgr.get_food("bAnNoCk") is not None

    def test_missing_food_returns_none(self) -> None:
        mgr = _make_manager(make_food("Bannock", 600))
        assert mgr.get_food("Nonexistent") is None


# ---------------------------------------------------------------------------
# TestConsume
# ---------------------------------------------------------------------------


class TestConsume:
    """Consuming a food updates stomach and availability."""

    def test_success_increments_stomach_decrements_available(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        result = mgr.consume(food)

        assert result is True
        assert mgr.stomach[food] == 1
        assert mgr.available[food] == 4

    def test_canonical_food_mirrored(self) -> None:
        """After consume, the canonical Food in .foods reflects new counts."""
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        mgr.consume(food)

        canonical = mgr.get_food("Bannock")
        assert canonical is not None
        assert canonical.stomach == 1
        assert canonical.available == 4

    def test_unavailable_returns_false(self) -> None:
        food = make_food("Bannock", 600, available=0)
        mgr = _make_manager(food)

        result = mgr.consume(food)

        assert result is False
        # No state change
        assert mgr.stomach.get(food, 0) == 0

    def test_sequential_consumption_accumulates(self) -> None:
        food = make_food("Bannock", 600, available=10)
        mgr = _make_manager(food)

        for _ in range(3):
            assert mgr.consume(food) is True

        assert mgr.stomach[food] == 3
        assert mgr.available[food] == 7


# ---------------------------------------------------------------------------
# TestCanConsume
# ---------------------------------------------------------------------------


class TestCanConsume:
    """Availability predicate."""

    def test_available_positive(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)
        assert mgr.can_consume(food) is True

    def test_available_zero(self) -> None:
        food = make_food("Bannock", 600, available=0)
        mgr = _make_manager(food)
        assert mgr.can_consume(food) is False

    def test_food_not_in_manager(self) -> None:
        food_in = make_food("Bannock", 600, available=5)
        food_out = make_food("Ghost", 100, available=5)
        mgr = _make_manager(food_in)
        assert mgr.can_consume(food_out) is False


# ---------------------------------------------------------------------------
# TestUniqueVarietyFoods
# ---------------------------------------------------------------------------


class TestUniqueVarietyFoods:
    """Foods qualifying for the variety bonus (calories * qty >= 2000)."""

    def test_empty_stomach(self) -> None:
        mgr = _make_manager(make_food("Bannock", 600, available=5))
        assert mgr.unique_variety_foods() == set()

    def test_qualifying_food(self) -> None:
        """A 2200-cal food at qty=1 qualifies (2200 >= 2000)."""
        food = make_food("Feast Platter", 2200, available=5)
        mgr = _make_manager(food)
        mgr.consume(food)
        assert "feast platter" in mgr.unique_variety_foods()

    def test_non_qualifying_food(self) -> None:
        """A 600-cal food at qty=1 doesn't qualify (600 < 2000)."""
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)
        mgr.consume(food)
        assert mgr.unique_variety_foods() == set()

    def test_becomes_qualifying_after_enough_bites(self) -> None:
        """A 600-cal food qualifies at qty=4 (2400 >= 2000)."""
        food = make_food("Bannock", 600, available=10)
        mgr = _make_manager(food)
        for _ in range(4):
            mgr.consume(food)
        assert "bannock" in mgr.unique_variety_foods()


# ---------------------------------------------------------------------------
# TestAllAvailable
# ---------------------------------------------------------------------------


class TestAllAvailable:
    """Filters to foods with positive availability."""

    def test_filters_positive_only(self) -> None:
        food_yes = make_food("Bannock", 600, available=5)
        food_no = make_food("Stale Bread", 200, available=0)
        mgr = _make_manager(food_yes, food_no)

        available = mgr.all_available()

        assert food_yes in available
        assert food_no not in available

    def test_empty_when_all_zero(self) -> None:
        food = make_food("Bannock", 600, available=0)
        mgr = _make_manager(food)
        assert mgr.all_available() == []


# ---------------------------------------------------------------------------
# TestResetStomach
# ---------------------------------------------------------------------------


class TestResetStomach:
    """Zeros all stomach counts."""

    def test_zeros_all(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        mgr.consume(food)
        before = mgr.get_food("Bannock")
        assert before is not None
        assert before.stomach == 1

        mgr.reset_stomach()
        after = mgr.get_food("Bannock")
        assert after is not None
        assert after.stomach == 0


# ---------------------------------------------------------------------------
# TestResetAvailability
# ---------------------------------------------------------------------------


class TestResetAvailability:
    """Sets uniform availability."""

    def test_sets_uniform(self) -> None:
        food_a = make_food("Bannock", 600, available=5)
        food_b = make_food("Salad", 1100, available=10)
        mgr = _make_manager(food_a, food_b)

        mgr.reset_availability(new_available=20)

        bannock = mgr.get_food("Bannock")
        salad = mgr.get_food("Salad")
        assert bannock is not None
        assert salad is not None
        assert bannock.available == 20
        assert salad.available == 20

    def test_default_zero(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        mgr.reset_availability()

        result = mgr.get_food("Bannock")
        assert result is not None
        assert result.available == 0


# ---------------------------------------------------------------------------
# TestResetTastiness
# ---------------------------------------------------------------------------


class TestResetTastiness:
    """Reset tastiness to unknown (99) or neutral (0)."""

    def test_to_unknown(self) -> None:
        food = make_food("Bannock", 600, tastiness=2)
        mgr = _make_manager(food)

        mgr.reset_tastiness(to_unknown=True)

        result = mgr.get_food("Bannock")
        assert result is not None
        assert result.tastiness == 99

    def test_to_neutral(self) -> None:
        food = make_food("Bannock", 600, tastiness=2)
        mgr = _make_manager(food)

        mgr.reset_tastiness(to_unknown=False)

        result = mgr.get_food("Bannock")
        assert result is not None
        assert result.tastiness == 0


# ---------------------------------------------------------------------------
# TestToJsonReady
# ---------------------------------------------------------------------------


class TestToJsonReady:
    """Serialization reflecting current state."""

    def test_all_foods_emitted(self) -> None:
        food_a = make_food("Bannock", 600, available=5)
        food_b = make_food("Salad", 1100, available=10)
        mgr = _make_manager(food_a, food_b)

        data = mgr.to_json_ready()

        names = {d["Name"] for d in data}
        assert names == {"Bannock", "Salad"}

    def test_reflects_mutations(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        mgr.consume(food)

        data = mgr.to_json_ready()
        entry = data[0]
        assert entry["Stomach"] == 1
        assert entry["Available"] == 4

    def test_has_expected_keys(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        data = mgr.to_json_ready()
        entry = data[0]

        expected_keys = {
            "Name",
            "Calories",
            "Carbs",
            "Protein",
            "Fat",
            "Vitamins",
            "Tastiness",
            "Stomach",
            "Available",
        }
        assert set(entry.keys()) == expected_keys


# ---------------------------------------------------------------------------
# TestGetCurrentSp
# ---------------------------------------------------------------------------


class TestGetCurrentSp:
    """Delegates to calculations.get_sp correctly."""

    def test_delegates_with_args(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        with patch("food_state_manager.get_sp", return_value=42.0) as mock_sp:
            result = mgr.get_current_sp(
                cravings=["Bannock"],
                cravings_satisfied=1,
                server_mult=2.0,
                dinner_party_mult=1.5,
            )

        assert result == 42.0
        mock_sp.assert_called_once()
        call_kwargs = mock_sp.call_args
        assert call_kwargs.kwargs["server_mult"] == 2.0
        assert call_kwargs.kwargs["dinner_party_mult"] == 1.5

    def test_defaults(self) -> None:
        food = make_food("Bannock", 600, available=5)
        mgr = _make_manager(food)

        with patch("food_state_manager.get_sp", return_value=10.0) as mock_sp:
            result = mgr.get_current_sp()

        assert result == 10.0
        call_kwargs = mock_sp.call_args
        assert call_kwargs.kwargs["server_mult"] == 1.0
        assert call_kwargs.kwargs["dinner_party_mult"] == 1.0
