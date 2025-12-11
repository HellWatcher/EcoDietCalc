"""Interactive prompts used by the CLI.

Order enforced by `collect_user_constraints`:
1) Current calories → 2) Max calories → 3) Satisfied cravings → 4) Current craving.
"""

from constants import (
    TASTINESS_MULTIPLIERS,
    TASTINESS_NAMES,
)


def prompt_for_cravings_satisfied():
    """Prompt the user for how many cravings have been satisfied today.

    Returns
    -------
    int
        Number of cravings satisfied (0+).
    """
    while True:
        value = input("How many cravings have you satisfied today? (0+) > ").strip()
        if value == "":
            return 0
        try:
            num = int(value)
            if num >= 0:
                return num
            print("Please enter 0 or a positive number.")
        except ValueError:
            print("Invalid input. Enter a whole number.")


def prompt_current_calories() -> int:
    """Ask for calories already consumed (>= 0)."""
    while True:
        try:
            val = int(input("How many calories have you already consumed? > ").strip())
            if val < 0:
                print("Calories cannot be negative.")
            else:
                return val
        except ValueError:
            print("That doesn't seem to be a number.")


def prompt_max_calories(
    current_cal: int,
) -> int:
    """Ask for max calorie limit (>= current)."""
    while True:
        try:
            val = int(input("What is your maximum calorie limit? > ").strip())
            if val < current_cal:
                print("Maximum must be greater than or equal to current intake.")
            else:
                return val
        except ValueError:
            print("That doesn't seem to be a number.")


def collect_user_constraints():
    """Collect user-defined constraints for meal planning.

    Order:
    1) Current calories
    2) Max calories
    3) Satisfied cravings
    4) Current craving
    (Rating unknown foods is handled during load.)

    Returns
    -------
    tuple[list[str], int, int]
        ``(cravings, cravings_satisfied, remaining_calories)``.
    """
    current_cal = prompt_current_calories()
    max_cal = prompt_max_calories(current_cal)
    cravings_satisfied = prompt_for_cravings_satisfied()
    print("Enter your current craving (press Enter to skip):")
    entry = input("> ").strip()
    cravings = [entry.lower()] if entry else []
    remaining_calories = max_cal - current_cal
    return (cravings, cravings_satisfied, remaining_calories)


def prompt_for_tastiness(
    food_name,
):
    """Prompt user for tastiness rating for a given food item.

    Parameters
    ----------
    food_name : str
        Name of the food item to rate.

    Returns
    -------
    int
        Tastiness rating in ``{-3, -2, -1, 0, 1, 2, 3}``, or ``99`` if skipped/unknown.
    """
    print(f"[PROMPT] Enter tastiness rating for '{food_name}' (-3 to 3, or 99 for unknown):")

    # Show human labels for valid ratings; exclude 99 (unknown) from the hint line
    print("  Hints:", ", ".join(f"{key}: {TASTINESS_NAMES[key]}" for key in sorted(TASTINESS_NAMES) if key != 99))

    # Accept blank to keep tastiness as unknown (99); otherwise loop until a valid int in range
    while True:
        value = input("> ").strip()
        if value == "":
            return 99  # Skip and keep as unknown
        try:
            value = int(value)

            # Validate against constants, not hardcoded bounds, so changing the scale only touches constants.py
            if value in TASTINESS_MULTIPLIERS:
                return value
            print("Invalid value. Valid: -3 to 3, or 99 for unknown.")
        except ValueError:
            print("Enter an integer or press Enter to skip.")


def prompt_yes_no(
    prompt: str,
    default: bool = True,
) -> bool:
    """Prompt the user for a yes/no response.

    Parameters
    ----------
    prompt : str
        The question to display.
    default : bool, optional
        Default value if the user presses Enter, by default ``True``.

    Returns
    -------
    bool
        ``True`` for yes, ``False`` for no.
    """

    # Conventional Y/n or y/N rendering with the default capitalized
    suffix = " (Y/n) > " if default else " (y/N) > "
    while True:
        # Normalize input (strip + lowercase); blank means "take the default"
        resp = input(prompt + suffix).strip().lower()
        if resp == "":
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("Please enter yes or no (y/n).")
