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
    (cravings, cravings_satisfied, remaining_calories) = collect_user_constraints()

    # Block until all cravings are valid (or dropped/replaced by the user)
    while True:
        valid, invalid, suggestions = validate_cravings(manager, [normalize_name(c) for c in cravings])
        if not invalid:
            cravings = valid
            break

        print("\nThe following cravings are not in your foods:")
        for bad in invalid:
            if bad in suggestions and suggestions[bad]:
                print(f"  - {bad}  (did you mean: {', '.join(suggestions[bad])})")
            else:
                print(f"  - {bad}")
        print("Enter replacements now. Leave blank to drop an item.")

        replacements = []
        for bad in invalid:
            repl = input(f"Replacement for '{bad}': ").strip()
            if repl:
                replacements.append(repl)

        # Keep existing valid ones, plus any replacements; loop will re-validate
        cravings = [*valid, *replacements]

    # Produce a plan under current constraints and show it
    meal_plan = plan_meal(
        manager=manager,
        cravings=cravings,
        cravings_satisfied=cravings_satisfied,
        remaining_calories=remaining_calories,
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
    # Only consider foods that are available (>0) and still have unknown tastiness (99)
    if not unknowns:
        print("No available foods with unknown tastiness.")
        return
    # Update tastiness in-place on the canonical Food objects
    for food in unknowns:
        food.tastiness = prompt_for_tastiness(food.name)

    save_food_dict(manager.to_json_ready(), DATA_PATH)
    print("Tastiness ratings saved.")


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
    did_any = False
    if args.stomach:
        manager.reset_stomach()
        did_any = True
    if args.availability:
        manager.reset_availability()
        did_any = True
    if args.tastiness:
        manager.reset_tastiness()
        did_any = True
    if not did_any:
        print("Nothing to do. Pick at least one of: --stomach --availability --tastiness")
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

    # Fallback: default to "plan" when no subcommand is provided (back-compat)
    command = args.cmd or "plan"
    if command == "plan":
        cmd_plan(args)
    elif command == "rate-unknowns":
        cmd_rate_unknowns(args)
    elif command == "reset":
        cmd_reset(args)
    else:
        parser.error(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
