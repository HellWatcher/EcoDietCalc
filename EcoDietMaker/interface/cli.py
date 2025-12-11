"""Command-line argument builder (parser only)."""

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with subcommands (``plan``, ``rate-unknowns``, ``reset``)
        and global options (e.g., verbosity).
    """
    parser = argparse.ArgumentParser(
        prog="eco",
        description="Eco Diet Planner",
    )
    # Subcommands; `required=False` for back-compat with older single-command usage
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

    # Subcommand: prompt to rate tastiness for available foods marked unknown
    subparsers.add_parser(
        "rate-unknowns",
        help="Rate unknown tastiness for available foods",
    )

    # Subcommand: reset parts of on-disk state (choose which via flags)
    show_parser = subparsers.add_parser(
        "reset",
        help="Reset parts of state",
    )
    # Toggle: clear current stomach counts
    show_parser.add_argument(
        "--stomach",
        action="store_true",
        help="Reset current stomach",
    )
    # Toggle: clear availability counts
    show_parser.add_argument(
        "--availability",
        action="store_true",
        help="Reset availability counts",
    )
    # Toggle: clear all tastiness ratings (set to unknown)
    show_parser.add_argument(
        "--tastiness",
        action="store_true",
        help="Clear all tastiness ratings",
    )

    return parser
