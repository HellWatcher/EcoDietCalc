"""Food data model and (de)serialization helpers.

Defines the `Food` record plus convenience methods for equality, hashing,
string representation, and JSON-compatible conversion.

Exports
-------
Food

Notes
-----
Tastiness scale is ``{-3,-2,-1,0,1,2,3}``; ``99`` denotes unknown.
"""

from constants import (
    TASTINESS_MULTIPLIERS,
)


class Food:
    """Construct a Food record.

    Parameters
    ----------
    name : str
        Food item name.
    calories : int
        Calories per unit.
    carbs : int
        Carbohydrates per unit.
    protein : int
        Protein per unit.
    fats : int
        Fats per unit.
    vitamins : int
        Vitamins per unit.
    tastiness : int
        Tastiness rating in ``{-3,-2,-1,0,1,2,3,99}``.
        ``99`` denotes unknown.
    stomach : int, optional
        Current consumed count, by default ``0``.
    available : int, optional
        Units available to eat, by default ``0``.
    """

    def __init__(
        self,
        name,
        calories,
        carbs,
        protein,
        fats,
        vitamins,
        tastiness,
        stomach=0,
        available=0,
    ):
        # Keep the display name as given; numeric fields are normalized to int
        self.name = name
        self.calories = int(calories)
        self.carbs = int(carbs)
        self.protein = int(protein)
        self.fats = int(fats)
        self.vitamins = int(vitamins)
        # Store the raw tastiness rating (99 = unknown sentinel)
        self.tastiness = int(tastiness)
        self.stomach = int(stomach)
        self.available = int(available)

        # Validate tastiness against the canonical multipliers scale.
        # Edit the scale in `constants.py` if needed.
        if self.tastiness not in TASTINESS_MULTIPLIERS:
            raise ValueError(
                f"Invalid tastiness value: {self.tastiness}"
            )

    def sum_nutrients(
        self,
    ):
        """Sum all nutrient components.

        Returns
        -------
        int
            Total nutrient score (e.g., ``carbs + protein + fats + vitamins``).
        """
        return self.carbs + self.protein + self.fats + self.vitamins

    def is_valid(
        self,
    ):
        """Check basic validity of the record.

        Returns
        -------
        bool
            ``True`` if required fields are present and values
            are within expected ranges.
        """
        return (
            self.calories >= 0
            and self.carbs >= 0
            and self.protein >= 0
            and self.fats >= 0
            and self.vitamins >= 0
            and self.tastiness in TASTINESS_MULTIPLIERS
        )

    def calories_per_nutrient(
        self,
    ):
        """Calories per unit of total nutrients.

        Returns
        -------
        float
            ``calories / sum_nutrients()``.
            Returns ``float('inf')`` when total nutrients are 0.
        """

        # Guard divide-by-zero when total nutrients are 0
        total_nutrients = self.sum_nutrients()
        return (
            self.calories / total_nutrients
            if total_nutrients
            else float("inf")
        )

    def __eq__(
        self,
        other,
    ):
        """Value equality based on identifying fields.

        Parameters
        ----------
        other : object
            Object to compare.

        Returns
        -------
        bool
            ``True`` if both represent the same food (e.g., matching name).
            Otherwise ``False``.
        """
        return (
            isinstance(
                other,
                Food,
            )
            and self.name.lower() == other.name.lower()
        )

    def __hash__(
        self,
    ):
        """Hash compatible with equality semantics.

        Returns
        -------
        int
            Hash derived from the identifying fields (e.g., lowercased name).
        """
        # Hash on the same key used by __eq__ (lowercased name)
        return hash(self.name.lower())

    def __str__(
        self,
    ):
        """Human-readable summary string.

        Returns
        -------
        str
            Short summary (name, nutrients, calories).
        """
        # Short, user-facing label (avoid leaking internal fields)
        return (
            f"{self.name}; {self.sum_nutrients()} Nutrients, "
            f"{self.calories} Cal"
        )

    def __repr__(
        self,
    ):
        """Unambiguous representation for debugging.

        Returns
        -------
        str
            Constructor-like representation.
        """
        # Minimal constructor-like repr; use `.debug_string()` or `.to_dict()`
        # for full details when needed.
        return f"Food({self.name!r}, {self.calories} cal)"

    @classmethod
    def from_dict(
        cls,
        data,
    ):
        """Create a ``Food`` from a JSON-like dictionary.

        Parameters
        ----------
        data : dict
            Must include keys:
            ``"Name"``, ``"Calories"``, ``"Carbs"``, ``"Protein"``,
            ``"Fats"``, ``"Vitamins"``, ``"Tastiness"``.
            Optional keys: ``"Stomach"``, ``"Available"``.

        Returns
        -------
        Food
            Constructed instance.
        """
        # Trust JSON keys; leave the case of "Name" as-is (display).
        # Normalize counts to ints when constructing.
        return cls(
            name=data["Name"],
            calories=data["Calories"],
            carbs=data["Carbs"],
            protein=data["Protein"],
            fats=data["Fats"],
            vitamins=data["Vitamins"],
            tastiness=data["Tastiness"],
            stomach=data.get("Stomach", 0),
            available=data.get("Available", 0),
        )

    def to_dict(
        self,
    ):
        """Serialize to a JSON-ready dictionary.

        Returns
        -------
        dict
            Keys:
            ``Name``, ``Calories``, ``Carbs``, ``Protein``, ``Fats``,
            ``Vitamins``, ``Tastiness``, ``Stomach``, ``Available``.
        """
        # Mirror all fields for stable JSON shape. `getattr` keeps older saves
        # compatible when keys are missing.
        data = {
            "Name": self.name,
            "Calories": self.calories,
            "Carbs": self.carbs,
            "Protein": self.protein,
            "Fats": self.fats,
            "Vitamins": self.vitamins,
            "Tastiness": self.tastiness,
            "Stomach": getattr(self, "stomach", 0),
            "Available": getattr(self, "available", 0),
        }
        return data

    @property
    def density(
        self,
    ):
        """Nutrient density (nutrients per calorie).

        Returns
        -------
        float
            ``sum_nutrients() / max(calories, 1)``.
        """
        return self.sum_nutrients() / max(self.calories, 1)

    def debug_string(
        self,
    ):
        """Detailed nutritional line for logs.

        Returns
        -------
        str
            String including calories, macros, vitamins, and tastiness.
        """
        return (
            f"{self.name} | Cal: {self.calories}, "
            f"C:{self.carbs} P:{self.protein} "
            f"F:{self.fats} V:{self.vitamins} "
            f"T:{self.tastiness}"
        )
