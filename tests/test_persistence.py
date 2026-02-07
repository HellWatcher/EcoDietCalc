"""Tests for persistence I/O and data integrity logging."""

import json

import pytest

from conftest import make_food
from interface.persistence import (
    log_data_issues,
    read_food_dict,
    save_food_dict,
)
from models.food import Food


class TestReadFoodDict:
    """Tests for read_food_dict()."""

    def test_read_valid_json(self, tmp_path) -> None:
        """Read valid JSON, get list[Food]."""
        data = [
            {
                "Name": "Bannock",
                "Calories": 600,
                "Carbs": 12,
                "Protein": 3,
                "Fats": 8,
                "Vitamins": 0,
                "Tastiness": 0,
                "Stomach": 0,
                "Available": 5,
            }
        ]
        path = tmp_path / "food.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = read_food_dict(path)
        assert len(result) == 1
        assert isinstance(result[0], Food)
        assert result[0].name == "Bannock"
        assert result[0].calories == 600

    def test_read_corrupt_json_returns_empty(self, tmp_path) -> None:
        """Corrupt file returns []."""
        path = tmp_path / "bad.json"
        path.write_text("{not valid json!!!", encoding="utf-8")

        result = read_food_dict(path)
        assert result == []

    def test_read_missing_file_raises(self, tmp_path) -> None:
        """Nonexistent file raises."""
        with pytest.raises(FileNotFoundError):
            read_food_dict(tmp_path / "missing.json")


class TestSaveFoodDict:
    """Tests for save_food_dict()."""

    def test_save_deduplicates(self, tmp_path) -> None:
        """Two entries same name → keeps last."""
        food_list = [
            {"Name": "Bannock", "Calories": 600},
            {"Name": "bannock", "Calories": 700},  # same name, different case
        ]
        path = tmp_path / "dedup.json"
        save_food_dict(food_list, path)

        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["Calories"] == 700  # last occurrence wins

    def test_save_roundtrip(self, tmp_path) -> None:
        """save then read = same data."""
        food = make_food(
            "Elk Wellington", calories=1400, carbs=10, protein=18, fats=12, vitamins=8
        )
        food_list = [food.to_dict()]
        path = tmp_path / "roundtrip.json"

        save_food_dict(food_list, path)
        result = read_food_dict(path)

        assert len(result) == 1
        assert result[0].name == "Elk Wellington"
        assert result[0].calories == 1400


class TestLogDataIssues:
    """Tests for log_data_issues()."""

    def test_no_issues_writes_clean(self, tmp_path, monkeypatch) -> None:
        """Clean state writes 'No issues found'."""
        monkeypatch.chdir(tmp_path)
        food = make_food("Bannock", calories=600)
        log_data_issues(
            all_foods=[food],
            stomach_counts={},
            available_counts={},
        )
        log_content = (tmp_path / "log.txt").read_text(encoding="utf-8")
        assert "No issues found" in log_content

    def test_reports_unknown_stomach(self, tmp_path, monkeypatch) -> None:
        """Detects foods in stomach but missing from master list."""
        monkeypatch.chdir(tmp_path)
        known_food = make_food("Bannock", calories=600)
        unknown_food = make_food("Mystery Stew", calories=500)

        log_data_issues(
            all_foods=[known_food],
            stomach_counts={unknown_food: 1},
            available_counts={},
        )
        log_content = (tmp_path / "log.txt").read_text(encoding="utf-8")
        assert "STOMACH" in log_content
        assert "Mystery Stew" in log_content

    def test_reports_invalid_tastiness(self, tmp_path, monkeypatch) -> None:
        """Detects bad tastiness ratings."""
        monkeypatch.chdir(tmp_path)
        # Create a food then forcibly set invalid tastiness
        food = make_food("Bad Taste", calories=500)
        food.tastiness = 42  # invalid

        log_data_issues(
            all_foods=[food],
            stomach_counts={},
            available_counts={},
        )
        log_content = (tmp_path / "log.txt").read_text(encoding="utf-8")
        assert "Invalid tastiness" in log_content
        assert "Bad Taste" in log_content

    def test_newlines_are_real(self, tmp_path, monkeypatch) -> None:
        """Verify log output uses real newlines, not escaped \\n."""
        monkeypatch.chdir(tmp_path)
        known_food = make_food("Bannock", calories=600)
        unknown_food = make_food("Mystery", calories=500)

        log_data_issues(
            all_foods=[known_food],
            stomach_counts={unknown_food: 1},
            available_counts={},
        )
        log_content = (tmp_path / "log.txt").read_text(encoding="utf-8")
        # Should NOT contain literal backslash-n
        assert "\\n" not in log_content
        # Should contain real newlines
        assert "\n" in log_content


class TestLoadFoodState:
    """Tests for load_food_state()."""

    def test_load_food_state_skip_prompts(self, tmp_path, monkeypatch) -> None:
        """skip_prompts=True never calls input."""
        # Create a minimal food_state.json
        data = [
            {
                "Name": "Bannock",
                "Calories": 600,
                "Carbs": 12,
                "Protein": 3,
                "Fats": 8,
                "Vitamins": 0,
                "Tastiness": 0,
                "Stomach": 2,
                "Available": 5,
            }
        ]
        food_file = tmp_path / "food_state.json"
        food_file.write_text(json.dumps(data), encoding="utf-8")

        # Patch DATA_PATH to use our tmp file
        monkeypatch.setattr("interface.persistence.DATA_PATH", food_file)
        monkeypatch.chdir(tmp_path)

        # input() should never be called
        monkeypatch.setattr("builtins.input", lambda _: pytest.fail("input() called"))

        from interface.persistence import load_food_state

        manager = load_food_state(skip_prompts=True)
        assert manager.get_food("bannock") is not None

    def test_load_food_state_reset_stomach(self, tmp_path, monkeypatch) -> None:
        """Resets stomach counts to 0."""
        data = [
            {
                "Name": "Bannock",
                "Calories": 600,
                "Carbs": 12,
                "Protein": 3,
                "Fats": 8,
                "Vitamins": 0,
                "Tastiness": 0,
                "Stomach": 5,
                "Available": 10,
            }
        ]
        food_file = tmp_path / "food_state.json"
        food_file.write_text(json.dumps(data), encoding="utf-8")

        monkeypatch.setattr("interface.persistence.DATA_PATH", food_file)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda _: pytest.fail("input() called"))

        from interface.persistence import load_food_state

        manager = load_food_state(reset_stomach=True, skip_prompts=True)
        # Stomach should be empty after reset
        assert len(manager.stomach) == 0
