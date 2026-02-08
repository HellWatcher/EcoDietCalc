from constants import (
    CRAVING_SATISFIED_FRAC,
    TASTINESS_DELTA_THRESHOLD,
    VARIETY_DELTA_THRESHOLD,
)
from planner import fmt_signed


def display_meal_plan(
    meal_plan: list,
    notices: list[str] | None = None,
):
    """Pretty-print the meal plan.

    Parameters
    ----------
    meal_plan : list[MealPlanItem]
        Items to display, including calories, SP gain, new SP, and deltas.
    notices : list of str, optional
        Lines to print above the table (e.g., invalid cravings).
        Defaults to ``None``.
    """
    if notices:
        # print notices (e.g., invalid cravings) above the table
        for note in notices:
            print(f"Note: {note}")
    if not meal_plan:
        print("No meal plan generated.")
        return

    # Build rows with preformatted tag text
    rows = []
    for index, item in enumerate(meal_plan, 1):
        tags = []
        if getattr(item, "craving", False):
            percent = int(CRAVING_SATISFIED_FRAC * 100)
            tags.append(f"[Craving Satisfied +{percent}%]")

        variety_delta = getattr(item, "variety_delta_pp", 0.0)
        if abs(variety_delta) >= VARIETY_DELTA_THRESHOLD:
            tags.append(f"Variety Δ {fmt_signed(item.variety_delta_pp)} pp")

        tastiness_delta = getattr(item, "tastiness_delta_pp", 0.0)
        if abs(tastiness_delta) >= TASTINESS_DELTA_THRESHOLD:
            tags.append(f"Tastiness Δ {fmt_signed(item.tastiness_delta_pp)} pp")

        rows.append(
            (
                index,
                item.name,
                item.calories,
                item.sp_gain,
                item.new_sp,
                ", ".join(tags),
            )
        )

    # Column widths
    index_width = len(str(len(rows))) if rows else 1
    name_width = max((len(row[1]) for row in rows), default=0)
    calorie_width = max((len(str(row[2])) for row in rows), default=0)
    delta_width = max((len(fmt_signed(row[3])) for row in rows), default=0)
    sp_width = max((len(f"{row[4]:.2f}") for row in rows), default=0)

    # Compose left prefixes first to align tag column
    prefixes = []
    for row in rows:
        left = f" {row[0]:>{index_width}}. "
        left += f"{row[1]:<{name_width}} - "
        left += f"{row[2]:>{calorie_width}} cal | "
        right = f"SP {fmt_signed(row[3]):>{delta_width}} ⇒ {row[4]:>{sp_width}.2f}"
        prefixes.append(left + right)

    prefix_width = max((len(prefix) for prefix in prefixes), default=0)

    print("========== MEAL PLAN ==========")
    for prefix, row in zip(prefixes, rows):
        if not row[5]:
            print(prefix)
        else:
            padding = " " * (prefix_width - len(prefix))
            print(prefix + padding + "  " + row[5])
    print("================================")
