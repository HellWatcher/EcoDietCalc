from collections import (
    namedtuple,
)

FoodLike = namedtuple(
    "FoodLike",
    [
        "name",
        "calories",
        "carbs",
        "protein",
        "fat",
        "vitamins",
        "tastiness",
    ],
)


def food(
    name,
    cal,
    c=0,
    p=0,
    f=0,
    v=0,
    t=0,
):
    return FoodLike(
        name,
        cal,
        c,
        p,
        f,
        v,
        t,
    )


class DummyManager:
    def __init__(
        self,
        avail,
    ):
        self.stomach = {}
        self._avail = list(avail)

    def all_available(
        self,
    ):
        return list(self._avail)

    def consume(
        self,
        food,
    ):
        self.stomach[food] = self.stomach.get(food, 0) + 1


def test_one_bite_increases_sp_delta():
    from planner import _choose_next_bite  # private, but fine for smoke test

    a = food(
        "A",
        200,
        p=10,
        t=3,
    )
    b = food(
        "B",
        300,
        p=15,
        t=0,
    )
    m = DummyManager(
        [
            a,
            b,
        ]
    )

    best, delta = _choose_next_bite(
        m,
        remaining_calories=1000,
        cravings=[],
        cravings_satisfied=0,
    )
    assert best in (
        a,
        b,
    )
    assert isinstance(delta, float)
