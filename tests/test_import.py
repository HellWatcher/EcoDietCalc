"""Tests for mod-exported game state import pipeline."""

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interface.persistence import (
    _parse_cravings_satisfied,
    load_game_state_export,
)

# ---------------------------------------------------------------------------
# Fixture: minimal valid game-state JSON
# ---------------------------------------------------------------------------

SAMPLE_EXPORT = {
    "ExportedAt": "2026-02-07T19:30:00Z",
    "PlayerName": "Steve",
    "Note": "test fixture",
    "Calories": {"Current": 2400.0, "Max": 3000.0},
    "Cravings": {
        "Current": "Charred Fish",
        "Multiplier": 1.10,
        "Description": "1 craving satisfied",
    },
    "Multipliers": {
        "BalancedDiet": 1.15,
        "Variety": 1.20,
        "Tastiness": 1.10,
        "Craving": 1.10,
        "DinnerParty": 1.50,
        "Calorie": 1.00,
        "NutrientSkillRate": 42.5,
    },
    "Foods": [
        {
            "Name": "Charred Fish",
            "Calories": 500,
            "Carbs": 0,
            "Protein": 12,
            "Fats": 8,
            "Vitamins": 0,
            "Tastiness": 1,
            "Stomach": 3,
        },
        {
            "Name": "Bannock",
            "Calories": 600,
            "Carbs": 12,
            "Protein": 3,
            "Fats": 8,
            "Vitamins": 0,
            "Tastiness": 0,
            "Stomach": 0,
        },
        {
            "Name": "Mystery Stew",
            "Calories": 800,
            "Carbs": 10,
            "Protein": 10,
            "Fats": 10,
            "Vitamins": 10,
            "Tastiness": 99,
            "Stomach": 0,
        },
    ],
}


@pytest.fixture
def export_path(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write the sample export to a temp file and return its path."""
    path = tmp_path / "game_state_test.json"
    path.write_text(json.dumps(SAMPLE_EXPORT), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# _parse_cravings_satisfied
# ---------------------------------------------------------------------------


class TestParseCravingsSatisfied:
    def test_parses_description_single(self) -> None:
        assert _parse_cravings_satisfied("1 craving satisfied", 1.10) == 1

    def test_parses_description_plural(self) -> None:
        assert _parse_cravings_satisfied("3 cravings satisfied", 1.30) == 3

    def test_fallback_to_multiplier(self) -> None:
        """When description has no number, derive from multiplier."""
        assert _parse_cravings_satisfied("some text", 1.20) == 2

    def test_zero_when_no_signal(self) -> None:
        assert _parse_cravings_satisfied("", 1.0) == 0

    def test_zero_when_multiplier_below_one(self) -> None:
        assert _parse_cravings_satisfied("", 0.95) == 0


# ---------------------------------------------------------------------------
# load_game_state_export — food loading
# ---------------------------------------------------------------------------


class TestLoadGameStateExportFoods:
    def test_loads_all_foods(self, export_path: pathlib.Path) -> None:
        manager, *_ = load_game_state_export(export_path)
        assert len(manager.foods) == 3

    def test_food_nutrients(self, export_path: pathlib.Path) -> None:
        manager, *_ = load_game_state_export(export_path)
        fish = manager.get_food("Charred Fish")
        assert fish is not None
        assert fish.calories == 500
        assert fish.protein == 12
        assert fish.fat == 8
        assert fish.carbs == 0
        assert fish.vitamins == 0

    def test_stomach_counts(self, export_path: pathlib.Path) -> None:
        manager, *_ = load_game_state_export(export_path)
        fish = manager.get_food("Charred Fish")
        assert fish is not None
        assert fish.stomach == 3
        # fish should be in the stomach dict
        assert manager.stomach.get(fish, 0) == 3

    def test_unknown_tastiness_preserved(self, export_path: pathlib.Path) -> None:
        manager, *_ = load_game_state_export(export_path)
        stew = manager.get_food("Mystery Stew")
        assert stew is not None
        assert stew.tastiness == 99

    def test_known_tastiness_values(self, export_path: pathlib.Path) -> None:
        """Tastiness values -3..+3 and 99 are all valid."""
        manager, *_ = load_game_state_export(export_path)
        fish = manager.get_food("Charred Fish")
        assert fish is not None
        assert fish.tastiness == 1  # "Good"

    def test_default_availability(self, export_path: pathlib.Path) -> None:
        """When Available is missing, default to 99 (unlimited proxy)."""
        manager, *_ = load_game_state_export(export_path)
        bannock = manager.get_food("Bannock")
        assert bannock is not None
        assert bannock.available == 99


# ---------------------------------------------------------------------------
# load_game_state_export — cravings & calories
# ---------------------------------------------------------------------------


class TestLoadGameStateExportMeta:
    def test_cravings_list(self, export_path: pathlib.Path) -> None:
        _, cravings, *_ = load_game_state_export(export_path)
        assert cravings == ["Charred Fish"]

    def test_cravings_satisfied(self, export_path: pathlib.Path) -> None:
        _, _, cravings_satisfied, *_ = load_game_state_export(export_path)
        assert cravings_satisfied == 1

    def test_remaining_calories(self, export_path: pathlib.Path) -> None:
        _, _, _, remaining_calories, *_ = load_game_state_export(export_path)
        assert remaining_calories == pytest.approx(600.0)

    def test_dinner_party_mult(self, export_path: pathlib.Path) -> None:
        _, _, _, _, _, dinner_party_mult = load_game_state_export(export_path)
        assert dinner_party_mult == pytest.approx(1.50)

    def test_no_craving_yields_empty_list(self, tmp_path: pathlib.Path) -> None:
        """When Current is 'None', cravings list should be empty."""
        data = {**SAMPLE_EXPORT}
        data["Cravings"] = {
            "Current": "None",
            "Multiplier": 1.0,
            "Description": "",
        }
        path = tmp_path / "no_craving.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        _, cravings, *_ = load_game_state_export(path)
        assert cravings == []


# ---------------------------------------------------------------------------
# load_game_state_export — error cases
# ---------------------------------------------------------------------------


class TestLoadGameStateExportErrors:
    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_game_state_export("/nonexistent/game_state.json")

    def test_missing_foods_key_raises(self, tmp_path: pathlib.Path) -> None:
        data = {
            "Calories": {"Current": 0, "Max": 3000},
            "Cravings": {"Current": "None", "Multiplier": 1.0, "Description": ""},
            "Multipliers": {"DinnerParty": 1.0},
        }
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(KeyError):
            load_game_state_export(path)


# ---------------------------------------------------------------------------
# Tastiness enum mapping coverage (all 7 levels + unknown)
# ---------------------------------------------------------------------------


class TestTastinessMapping:
    """Verify that all tastiness integers from the mod map to valid Food values."""

    @pytest.mark.parametrize(
        "tastiness",
        [-3, -2, -1, 0, 1, 2, 3, 99],
        ids=[
            "worst",
            "horrible",
            "bad",
            "ok",
            "good",
            "delicious",
            "favorite",
            "unknown",
        ],
    )
    def test_valid_tastiness_creates_food(self, tastiness: int) -> None:
        from models.food import Food

        food = Food(
            name="Test",
            calories=100,
            carbs=5,
            protein=5,
            fat=5,
            vitamins=5,
            tastiness=tastiness,
        )
        assert food.tastiness == tastiness
