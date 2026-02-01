"""Command-line interface for the meal planner.

Wires together loading state, collecting user constraints, planning meals,
and persisting updates. Provides subcommands for planning, rating unknowns,
and resetting state.

Exports
-------
cmd_plan
cmd_rate_unknowns
cmd_reset
main

Notes
-----
Use `python -m <package> plan` to run planning from the shell.
"""

# Early config path detection - must happen before importing constants
import sys


def _detect_config_path() -> str | None:
    """Extract --config or -c from sys.argv before full parsing."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg in ("--config", "-c") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--config="):
            return arg.split("=", 1)[1]
    return None


# Set config path before any other imports that use constants
_early_config = _detect_config_path()
if _early_config:
    from config import set_config_path

    set_config_path(_early_config)


# Now safe to import modules that depend on constants
from calculations import (
    calculate_balance_bonus,
    get_sp,
    get_taste_bonus,
    get_variety_bonus,
    is_variety_qualifying,
    sum_all_weighted_nutrients,
)
from constants import (
    CRAVING_BONUS_PP,
    CRAVING_MAX_COUNT,
    CRAVING_SATISFIED_FRAC,
    VARIETY_CAL_THRESHOLD,
)
from interface.cli import (
    build_parser,
)
from interface.persistence import (
    DATA_PATH,
    load_food_state,
    prompt_for_tastiness,
    save_food_dict,
)
from interface.prompts import (
    collect_user_constraints,
)
from interface.render import (
    display_meal_plan,
)
from logs.logging_utils import (
    setup_logging,
)
from planner import (
    normalize_name,
    plan_meal,
    validate_cravings,
)


def cmd_plan(
    args,
) -> None:
    """Execute the ``plan`` subcommand.

    Loads/initializes state, gathers user constraints, generates a meal plan,
    prints it, and optionally saves updated stomach/availability.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.
    """

    # Prompt for cravings (list), satisfied count, and remaining calories
    manager = load_food_state()

    # collect interactive inputs
    user_constraints = collect_user_constraints()
    cravings, cravings_satisfied, remaining_calories = user_constraints

    # Get multipliers from CLI args (with defaults)
    server_mult = getattr(args, "server_mult", 1.0)
    dinner_party_mult = getattr(args, "dinner_party", 1.0)

    # Block until all cravings are valid (or dropped/replaced by the user)
    while True:
        normalized = [normalize_name(c) for c in cravings]
        valid, invalid, suggestions = validate_cravings(manager, normalized)
        if not invalid:
            cravings = valid
            break

        print("\nThe following cravings are not in your foods:")
        for invalid_craving in invalid:
            if invalid_craving in suggestions and suggestions[invalid_craving]:
                suggestion_str = ", ".join(suggestions[invalid_craving])
                print(f"  - {invalid_craving}  (did you mean: {suggestion_str})")
            else:
                print(f"  - {invalid_craving}")
        print("Enter replacements now.")
        print("Leave blank to drop an item.")

        replacements = []
        for invalid_craving in invalid:
            replacement = input(f"Replacement for '{invalid_craving}': ").strip()
            if replacement:
                replacements.append(replacement)

        # Keep existing valid ones, plus any replacements.
        # Loop will re-validate.
        cravings = [*valid, *replacements]

    # Produce a plan under current constraints and show it
    meal_plan = plan_meal(
        manager=manager,
        cravings=cravings,
        cravings_satisfied=cravings_satisfied,
        remaining_calories=remaining_calories,
        server_mult=server_mult,
        dinner_party_mult=dinner_party_mult,
    )

    # Pretty-print the plan for the user
    display_meal_plan(meal_plan)

    # Persist updated stomach/availability back to disk
    save_food_dict(
        manager.to_json_ready(),
        DATA_PATH,
    )


def cmd_rate_unknowns(
    _args,
) -> None:
    """Execute the ``rate-unknowns`` subcommand.

    Prompts for tastiness ratings for any foods marked as unknown and saves
    the updated state.

    Parameters
    ----------
    _args : argparse.Namespace
        Parsed CLI arguments (not otherwise used).
    """

    manager = load_food_state()

    # prompt for tastiness on available foods with unknown ratings
    unknowns = [
        food
        for food in manager.available
        if manager.available[food] > 0
        and getattr(
            food,
            "tastiness",
            99,
        )
        == 99
    ]
    # Only consider foods that are available (>0) and still have
    # unknown tastiness (99)
    if not unknowns:
        print("No available foods with unknown tastiness.")
        return
    # Update tastiness in-place on the canonical Food objects
    for food in unknowns:
        food.tastiness = prompt_for_tastiness(food.name)

    save_food_dict(manager.to_json_ready(), DATA_PATH)
    print("Tastiness ratings saved.")


def cmd_predict(
    args,
) -> None:
    """Execute the ``predict`` subcommand.

    Predicts SP gain from eating a specific food. Used for in-game validation
    testing. Does not modify any state.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.
    """
    manager = load_food_state(skip_prompts=True)

    # Look up the food
    food = manager.get_food(args.food)
    if not food:
        print(f"Error: Food '{args.food}' not found in database.")
        print("Available foods containing that text:")
        matches = [
            name for name in manager.foods.keys() if args.food.lower() in name.lower()
        ]
        for match_name in matches[:10]:
            print(f"  - {manager.foods[match_name].name}")
        return

    # Parse cravings
    cravings = (
        [c.strip() for c in args.cravings.split(",") if c.strip()]
        if args.cravings
        else []
    )

    # Build a simulated stomach with just this food
    quantity = args.quantity
    stomach = {food: quantity}

    # Get multipliers from args
    server_mult = getattr(args, "server_mult", 1.0)
    dinner_party_mult = getattr(args, "dinner_party", 1.0)
    cravings_satisfied = args.satisfied
    variety_count_before = args.variety_count

    # Calculate components
    density, total_cal = sum_all_weighted_nutrients(stomach)
    density_sum = (
        density["carbs"] + density["protein"] + density["fats"] + density["vitamins"]
    )

    nutrients_list = [
        density["carbs"],
        density["protein"],
        density["fats"],
        density["vitamins"],
    ]
    balance_pp = calculate_balance_bonus(nutrients_list)

    # Variety: check if this food qualifies
    food_qualifies = is_variety_qualifying(food, quantity)
    if food_qualifies and variety_count_before == 0:
        # Fresh stomach, this food becomes variety count = 1
        variety_count = 1
    elif food_qualifies:
        # Adding to existing variety
        variety_count = variety_count_before + 1
    else:
        variety_count = variety_count_before

    variety_pp = get_variety_bonus(variety_count)

    taste_pp = get_taste_bonus(stomach)

    # Craving match bonus
    cravings_set = {c.lower() for c in cravings}
    is_craving = food.name.lower() in cravings_set
    craving_match_count = 1 if is_craving else 0
    craving_pp = min(craving_match_count, CRAVING_MAX_COUNT) * CRAVING_BONUS_PP

    # Build unique foods set for SP calculation
    unique_foods_24h = {food.name.lower()} if food_qualifies else set()

    # Calculate final SP
    sp = get_sp(
        stomach=stomach,
        cravings=cravings,
        cravings_satisfied=cravings_satisfied,
        unique_foods_24h=unique_foods_24h,
        server_mult=server_mult,
        dinner_party_mult=dinner_party_mult,
    )

    # Print breakdown
    print("\n" + "=" * 60)
    print(f"SP PREDICTION: {food.name} x {quantity}")
    print("=" * 60)
    print(f"\nFood: {food.debug_string()}")
    print(f"Total Calories: {total_cal:.0f}")
    print()
    print("Component Breakdown:")
    print(f"  Density Sum:     {density_sum:.2f}")
    print(f"    Carbs:         {density['carbs']:.2f}")
    print(f"    Protein:       {density['protein']:.2f}")
    print(f"    Fats:          {density['fats']:.2f}")
    print(f"    Vitamins:      {density['vitamins']:.2f}")
    print()
    print(f"  Balance:         {balance_pp:+.2f} pp")
    print(
        f"  Variety:         {variety_pp:+.2f} pp (count={variety_count}, qualifies={food_qualifies})"
    )
    print(f"  Taste:           {taste_pp:+.2f} pp (tastiness={food.tastiness})")
    print(f"  Craving Match:   {craving_pp:+.2f} pp (match={is_craving})")
    print()
    total_bonus_pp = balance_pp + variety_pp + taste_pp + craving_pp
    satisfied_bonus = cravings_satisfied * CRAVING_SATISFIED_FRAC
    print(
        f"  Total Bonus:     {total_bonus_pp:+.2f} pp + {satisfied_bonus:.2f} satisfied"
    )
    print()
    print(f"Multipliers:")
    print(f"  Server:          {server_mult:.2f}x")
    print(f"  Dinner Party:    {dinner_party_mult:.2f}x")
    print()
    print("-" * 60)
    print(f"PREDICTED SP:      {sp:.2f}")
    print("-" * 60)

    # Show formula
    bonus_frac = total_bonus_pp / 100 + satisfied_bonus
    nutrition_sp = density_sum * (1 + bonus_frac) * dinner_party_mult
    print(
        f"\nFormula: ({density_sum:.2f} * (1 + {bonus_frac:.4f}) * {dinner_party_mult:.2f} + 12) * {server_mult:.2f}"
    )
    print(f"       = ({nutrition_sp:.2f} + 12) * {server_mult:.2f}")
    print(f"       = {sp:.2f}")
    print()


def cmd_reset(
    args,
) -> None:
    """Execute the ``reset`` subcommand.

    Resets persisted state on disk. Flags may control whether stomach counts
    and/or tastiness ratings are cleared.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.
    """

    manager = load_food_state()
    any_reset_performed = False
    if args.stomach:
        manager.reset_stomach()
        any_reset_performed = True
    if args.availability:
        manager.reset_availability()
        any_reset_performed = True
    if args.tastiness:
        manager.reset_tastiness()
        any_reset_performed = True
    if not any_reset_performed:
        print("Nothing to do.")
        print("Pick at least one of: --stomach --availability --tastiness")
        return
    save_food_dict(manager.to_json_ready(), DATA_PATH)
    print("Reset complete.")


def main():
    """CLI entry point.

    Parses args, configures logging, and dispatches to the selected subcommand.
    """

    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)

    # Note: --config was already processed early for config loading
    # (see top of file). The args.config attribute is available but
    # the config has already been applied.

    # Fallback: default to "plan" when no subcommand is provided (back-compat)
    command = args.cmd or "plan"
    if command == "plan":
        cmd_plan(args)
    elif command == "predict":
        cmd_predict(args)
    elif command == "rate-unknowns":
        cmd_rate_unknowns(args)
    elif command == "reset":
        cmd_reset(args)
    else:
        parser.error(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
