"""Command-line argument builder (parser only)."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with subcommands (``plan``,
        ``rate-unknowns``, ``reset``) and global options
        (e.g., verbosity, config file).
    """
    parser = argparse.ArgumentParser(
        prog="eco",
        description="Eco Diet Planner",
    )
    # Subcommands; `required=False` for back-compat with older
    # single-command usage
    subparsers = parser.add_subparsers(
        dest="cmd",
        required=False,
    )

    # Global -v/--verbose for all commands (counting flag)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="-v for INFO, -vv for DEBUG",
    )

    # Global --config for custom configuration file
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to custom config YAML file (default: config.default.yml)",
    )

    # Subcommand: plan meals
    plan_parser = subparsers.add_parser(
        "plan",
        help="Generate a meal plan",
    )
    plan_parser.add_argument(
        "-s",
        "--server-mult",
        type=float,
        default=1.0,
        help="Server skill gain multiplier (default: 1.0)",
    )
    plan_parser.add_argument(
        "-d",
        "--dinner-party",
        type=float,
        default=1.0,
        help="Dinner party multiplier (1.0-3.0, default: 1.0)",
    )

    # Subcommand: prompt to rate tastiness for available foods marked unknown
    subparsers.add_parser(
        "rate-unknowns",
        help="Rate unknown tastiness for available foods",
    )

    # Subcommand: predict SP for a food (validation mode)
    predict_parser = subparsers.add_parser(
        "predict",
        help="Predict SP for eating a specific food (validation mode)",
    )
    predict_parser.add_argument(
        "--food",
        "-f",
        type=str,
        required=True,
        help="Name of the food to predict",
    )
    predict_parser.add_argument(
        "--quantity",
        "-q",
        type=int,
        default=1,
        help="Number of units to eat (default: 1)",
    )
    predict_parser.add_argument(
        "--cravings",
        "-c",
        type=str,
        default="",
        help="Comma-separated craving names (default: none)",
    )
    predict_parser.add_argument(
        "--satisfied",
        type=int,
        default=0,
        help="Number of cravings already satisfied today (default: 0)",
    )
    predict_parser.add_argument(
        "--variety-count",
        type=int,
        default=0,
        help="Current variety count before eating (default: 0 = empty stomach)",
    )
    predict_parser.add_argument(
        "-s",
        "--server-mult",
        type=float,
        default=1.0,
        help="Server skill gain multiplier (default: 1.0)",
    )
    predict_parser.add_argument(
        "-d",
        "--dinner-party",
        type=float,
        default=1.0,
        help="Dinner party multiplier (1.0-3.0, default: 1.0)",
    )

    # Subcommand: reset parts of on-disk state (choose which via flags)
    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset parts of state",
    )
    # Toggle: clear current stomach counts
    reset_parser.add_argument(
        "--stomach",
        action="store_true",
        help="Reset current stomach",
    )
    # Toggle: clear availability counts
    reset_parser.add_argument(
        "--availability",
        action="store_true",
        help="Reset availability counts",
    )
    # Toggle: clear all tastiness ratings (set to unknown)
    reset_parser.add_argument(
        "--tastiness",
        action="store_true",
        help="Clear all tastiness ratings",
    )

    return parser
