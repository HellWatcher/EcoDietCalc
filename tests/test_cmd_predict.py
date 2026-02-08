"""Tests for cmd_predict() command."""

from argparse import Namespace


from conftest import make_food
from food_state_manager import FoodStateManager


def _make_manager() -> FoodStateManager:
    """Create a test manager with a few foods."""
    foods = [
        make_food("Bannock", calories=600, carbs=12, protein=3, fat=8, vitamins=0),
        make_food(
            "Elk Wellington",
            calories=1400,
            carbs=10,
            protein=18,
            fat=12,
            vitamins=8,
            tastiness=2,
            available=5,
        ),
        make_food(
            "Crimson Salad", calories=1100, carbs=12, protein=6, fat=8, vitamins=22
        ),
    ]
    return FoodStateManager(foods)


def _make_args(**overrides) -> Namespace:
    """Create a Namespace with predict defaults, overridable."""
    defaults = {
        "food": "Bannock",
        "quantity": 1,
        "cravings": "",
        "satisfied": 0,
        "variety_count": 0,
        "server_mult": 1.0,
        "dinner_party": 1.0,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class TestCmdPredict:
    """Tests for the predict subcommand."""

    def test_predict_known_food(self, capsys, monkeypatch) -> None:
        """Outputs SP prediction with breakdown."""
        monkeypatch.setattr(
            "main.load_food_state",
            lambda **kwargs: _make_manager(),
        )
        from main import cmd_predict

        cmd_predict(_make_args(food="Bannock"))
        output = capsys.readouterr().out
        assert "PREDICTED SP" in output
        assert "Bannock" in output
        assert "Density Sum" in output

    def test_predict_unknown_food(self, capsys, monkeypatch) -> None:
        """Prints error + suggestions for unknown food."""
        monkeypatch.setattr(
            "main.load_food_state",
            lambda **kwargs: _make_manager(),
        )
        from main import cmd_predict

        cmd_predict(_make_args(food="Pizza"))
        output = capsys.readouterr().out
        assert "not found" in output

    def test_predict_with_cravings(self, capsys, monkeypatch) -> None:
        """Satisfied craving bonus appears in output."""
        monkeypatch.setattr(
            "main.load_food_state",
            lambda **kwargs: _make_manager(),
        )
        from main import cmd_predict

        cmd_predict(_make_args(food="Bannock", cravings="Bannock", satisfied=1))
        output = capsys.readouterr().out
        assert "satisfied" in output.lower()

    def test_predict_with_variety(self, capsys, monkeypatch) -> None:
        """Variety count affects SP."""
        monkeypatch.setattr(
            "main.load_food_state",
            lambda **kwargs: _make_manager(),
        )
        from main import cmd_predict

        # With variety_count=5, variety bonus should be higher
        cmd_predict(_make_args(food="Bannock", variety_count=5))
        output = capsys.readouterr().out
        assert "Variety" in output
        assert "count=" in output

    def test_predict_with_multipliers(self, capsys, monkeypatch) -> None:
        """Server/dinner party multipliers scale output."""
        monkeypatch.setattr(
            "main.load_food_state",
            lambda **kwargs: _make_manager(),
        )
        from main import cmd_predict

        cmd_predict(_make_args(food="Bannock", server_mult=2.0, dinner_party=1.5))
        output = capsys.readouterr().out
        assert "2.00x" in output  # server mult
        assert "1.50x" in output  # dinner party mult
