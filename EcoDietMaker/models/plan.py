from dataclasses import (
    dataclass,
)

from models.food import Food


@dataclass
class MealPlanItem:
    """One planned bite with scoring details.

    Attributes
    ----------
    name : str
        Food name.
    calories : int
        Calories for this bite.
    sp_gain : float
        Delta in SP from adding this bite.
    new_sp : float
        SP after the bite.
    craving : bool
        True if this bite satisfied a craving.
    variety_delta_pp : float
        Variety bonus change (pp) due to the bite.
    taste_delta_pp : float
        Taste bonus change (pp) due to the bite.
    """

    name: str
    calories: int
    sp_gain: float
    new_sp: float
    craving: bool
    variety_delta_pp: float
    taste_delta_pp: float = 0.0


def append_meal_log(
    meal_log: list[MealPlanItem],
    food: Food,
    sp_gain: float,
    new_sp: float,
    craving: bool,
    variety_delta: float,
    taste_delta: float = 0.0,
) -> None:
    """Append a single bite entry to the meal log.

    Parameters
    ----------
    meal_log : list[MealPlanItem]
        List to append to.
    food : Food
        Food consumed.
    sp_gain : float
        Raw SP gain from the bite.
    new_sp : float
        SP after the bite.
    craving : bool
        Whether this bite satisfied a craving.
    variety_delta : float
        Change in variety bonus (percentage points).
    taste_delta : float, optional
        Change in taste bonus (percentage points), by default 0.0.
    """
    # Record a bite; this function only appends to the log
    meal_log.append(
        MealPlanItem(
            name=food.name,
            calories=food.calories,
            sp_gain=sp_gain,
            new_sp=new_sp,
            craving=craving,
            variety_delta_pp=variety_delta,
            taste_delta_pp=taste_delta,
        )
    )
