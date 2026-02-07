"""Tests for meal plan display rendering."""

from models.plan import MealPlanItem
from interface.render import display_meal_plan


class TestDisplayMealPlan:
    """Tests for display_meal_plan()."""

    def test_display_empty_plan(self, capsys) -> None:
        """Prints 'No meal plan generated.' for empty plan."""
        display_meal_plan([])
        output = capsys.readouterr().out
        assert "No meal plan generated." in output

    def test_display_single_item(self, capsys) -> None:
        """Contains food name, calories, SP."""
        item = MealPlanItem(
            name="Bannock",
            calories=600,
            sp_gain=1.5,
            new_sp=13.5,
            craving=False,
            variety_delta_pp=0.0,
            taste_delta_pp=0.0,
        )
        display_meal_plan([item])
        output = capsys.readouterr().out
        assert "Bannock" in output
        assert "600" in output
        assert "13.5" in output

    def test_display_with_craving_tag(self, capsys) -> None:
        """Shows '[Craving Satisfied +X%]'."""
        item = MealPlanItem(
            name="Elk Wellington",
            calories=1400,
            sp_gain=3.0,
            new_sp=15.0,
            craving=True,
            variety_delta_pp=0.0,
            taste_delta_pp=0.0,
        )
        display_meal_plan([item])
        output = capsys.readouterr().out
        assert "Craving Satisfied" in output

    def test_display_with_notices(self, capsys) -> None:
        """Prints 'Note: ...' lines."""
        item = MealPlanItem(
            name="Bannock",
            calories=600,
            sp_gain=1.0,
            new_sp=13.0,
            craving=False,
            variety_delta_pp=0.0,
        )
        display_meal_plan([item], notices=["Invalid craving: Pizza"])
        output = capsys.readouterr().out
        assert "Note: Invalid craving: Pizza" in output
