import pathlib
import sys

import pytest  # pyright: ignore[reportMissingImports]

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from food_state_manager import FoodStateManager
from models.food import Food


def make_food(
    name: str,
    calories: int,
    carbs: int = 10,
    protein: int = 10,
    fat: int = 10,
    vitamins: int = 10,
    tastiness: int = 0,
    stomach: int = 0,
    available: int = 10,
) -> Food:
    """Create a Food instance with sensible defaults."""
    return Food(
        name=name,
        calories=calories,
        carbs=carbs,
        protein=protein,
        fat=fat,
        vitamins=vitamins,
        tastiness=tastiness,
        stomach=stomach,
        available=available,
    )


@pytest.fixture
def simple_manager_factory():
    def _make():
        foods = [
            Food("Bannock", 600, 12, 3, 8, 0, 0, stomach=0, available=10),
            Food("Elk Wellington", 1400, 10, 18, 12, 8, 0, stomach=0, available=10),
            Food("Crimson Salad", 1100, 12, 6, 8, 22, 0, stomach=0, available=10),
            Food(
                "Feast Platter", 2200, 20, 20, 20, 10, 0, stomach=0, available=10
            ),  # ≥ 2000
            Food("Cereal Germ", 20, 5, 1, 0, 0, 0, stomach=0, available=10),
        ]
        return FoodStateManager(foods)

    return _make
