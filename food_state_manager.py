"""State manager for foods, stomach, and availability.

Holds the authoritative stomach/available counts, supports lookups and
consumption, and exposes helpers used by the planner and scoring functions.

Exports
-------
FoodStateManager

Notes
-----
Computations of SP and bonuses are delegated to `calculations`.
"""

import logging

from calculations import (
    get_sp,
    is_variety_qualifying,
)
from models.food import (
    Food,
)

logger = logging.getLogger(__name__)


class FoodStateManager:
    """Manage foods, stomach, and availability.

    Parameters
    ----------
    foods : list of Food
        Source records used to seed stomach/availability maps.

    Attributes
    ----------
    foods : dict[str, Food]
        Canonical foods keyed by lowercased name.
    stomach : dict[Food, int]
        Counts consumed (sparse: only positive entries stored).
    available : dict[Food, int]
        Counts available to consume (sparse).
    """

    def __init__(
        self,
        foods: list[Food],
    ):
        """Initialize the food state manager.

        Parameters
        ----------
        foods : list[Food]
            Collection of foods to manage. Initial `stomach` and `available`
            maps are populated from each item's
            ``stomach`` and ``available`` counts.
        """
        self.foods = {food.name.lower(): food for food in foods}
        # Sparse maps: store only positive counts.
        # Omit zeros to keep dicts small.
        self.stomach = {}
        self.available = {}
        for food in foods:
            # Seed only positive stomach counts
            if food.stomach > 0:
                self.stomach[food] = food.stomach
            # Seed only positive availability
            if food.available > 0:
                self.available[food] = food.available

    def get_food(
        self,
        name: str,
    ) -> Food | None:
        """Look up a food by name (case-insensitive).

        Parameters
        ----------
        name : str
            Food name to search for.

        Returns
        -------
        Food or None
            Matching food object if found; otherwise ``None``.
        """
        # Case-insensitive by design
        return self.foods.get(name.lower())

    def consume(
        self,
        food: Food,
    ) -> bool:
        """Consume one unit of a food if available.

        Parameters
        ----------
        food : Food
            Food to consume.

        Returns
        -------
        bool
            ``True`` if the bite was consumed and state updated.
            ``False`` if unavailable.
        """
        # Fast-fail if no stock for this item
        if self.available.get(food, 0) <= 0:
            return False
        # Increment stomach (per-bite consumption)
        self.stomach[food] = self.stomach.get(food, 0) + 1
        # Decrement on-hand availability
        self.available[food] -= 1

        # Mirror counts onto the canonical Food instance so that
        # `to_json_ready()` stays accurate
        self.foods[food.name.lower()].stomach = self.stomach[food]
        self.foods[food.name.lower()].available = self.available[food]

        return True

    def can_consume(
        self,
        food: Food,
    ) -> bool:
        """Check whether a food can be consumed (has stock available).

        Parameters
        ----------
        food : Food
            Food to check.

        Returns
        -------
        bool
            ``True`` if the available count is greater than zero.
            Otherwise ``False``.
        """
        # Availability predicate used by planner filters
        return self.available.get(food, 0) > 0

    def get_current_sp(
        self,
        cravings: list[str] | None = None,
        cravings_satisfied: int = 0,
        *,
        server_mult: float = 1.0,
        dinner_party_mult: float = 1.0,
    ) -> float:
        """Compute current SP given stomach state and cravings.

        Parameters
        ----------
        cravings : list of str, optional
            Active cravings (names, case-insensitive). Default is empty.
        cravings_satisfied : int, optional
            Number of cravings already satisfied. Default is 0.
        server_mult : float, optional
            Server skill gain multiplier. Default is 1.0.
        dinner_party_mult : float, optional
            Dinner party multiplier (1.0-3.0). Default is 1.0.

        Returns
        -------
        float
            Current SP value.
        """
        cravings = cravings or []

        # Pass (stomach, cravings, cravings_satisfied,
        # unique_foods_24h) — unique set, not list
        return get_sp(
            stomach=self.stomach,
            cravings=cravings,
            cravings_satisfied=cravings_satisfied,
            unique_foods_24h=self.unique_variety_foods(),
            server_mult=server_mult,
            dinner_party_mult=dinner_party_mult,
        )

    def unique_variety_foods(
        self,
    ) -> set[str]:
        """Get the set of foods that count toward the variety bonus.

        Returns
        -------
        set of str
            Lowercased names of foods in the stomach that qualify for variety.
        """
        # Lowercased names for foods whose
        # (calories * quantity) meet the variety threshold
        return {
            food_item.name.lower()
            for food_item, quantity in self.stomach.items()
            if is_variety_qualifying(food_item, quantity)
        }

    def all_available(
        self,
    ) -> list[Food]:
        """List all foods that still have available units.

        Returns
        -------
        list of Food
            Foods with ``available > 0``.
        """
        # Return Food objects that still have units available (not names/ids)
        return [food for food in self.available if self.available[food] > 0]

    def reset_stomach(
        self,
    ) -> None:
        """Zero out current stomach quantities for all foods.

        Returns
        -------
        None
        """
        for food in self.foods.values():
            food.stomach = 0

    def reset_availability(
        self,
        new_available: int = 0,
    ) -> None:
        """Set available counts for all foods.

        Parameters
        ----------
        new_available : int, optional
            New availability assigned to every food, by default ``0``.

        Returns
        -------
        None
        """
        for food in self.foods.values():
            food.available = new_available

    def reset_tastiness(
        self,
        to_unknown: bool = True,
    ) -> None:
        """Clear tastiness ratings for all foods.

        Parameters
        ----------
        to_unknown : bool, optional
            When ``True`` set tastiness to ``99`` (unknown).
            When ``False``, set to ``0`` (neutral).

        Returns
        -------
        None
        """
        new_val = 99 if to_unknown else 0
        for food in self.foods.values():
            food.tastiness = new_val

    def to_json_ready(
        self,
    ) -> list[dict]:
        """Serialize foods into JSON-compatible dicts reflecting current state.

        Returns
        -------
        list of dict
            One entry per food with keys:
            ``Name``, ``Calories``, ``Carbs``,
            ``Protein``, ``Fats``, ``Vitamins``,
            ``Tastiness``, ``Stomach``, and ``Available``.
        """
        # Stable field order to mirror `Food.to_dict()` for readable diffs
        json_ready = []
        # Emit all known foods, not just those currently present
        # in `stomach`/`available`
        for food in self.foods.values():
            # Stable key order for readable diffs; keep fields 1:1
            # with `Food.to_dict()`
            json_ready.append(
                {
                    "Name": food.name,
                    "Calories": food.calories,
                    "Carbs": food.carbs,
                    "Protein": food.protein,
                    "Fat": food.fat,
                    "Vitamins": food.vitamins,
                    "Tastiness": food.tastiness,
                    "Stomach": food.stomach,
                    "Available": food.available,
                }
            )
        return json_ready
