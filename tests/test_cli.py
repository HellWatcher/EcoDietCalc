"""Tests for CLI argument parser."""

import pytest

from interface.cli import build_parser


class TestBuildParser:
    """Tests for build_parser() argument parsing."""

    def test_plan_subcommand_defaults(self) -> None:
        """plan sets server_mult=1.0, dinner_party=1.0."""
        args = build_parser().parse_args(["plan"])
        assert args.cmd == "plan"
        assert args.server_mult == 1.0
        assert args.dinner_party == 1.0

    def test_predict_subcommand_requires_food(self) -> None:
        """predict without --food fails."""
        with pytest.raises(SystemExit):
            build_parser().parse_args(["predict"])

    def test_predict_subcommand_defaults(self) -> None:
        """Default quantity=1, satisfied=0, variety_count=0."""
        args = build_parser().parse_args(["predict", "--food", "Bannock"])
        assert args.cmd == "predict"
        assert args.food == "Bannock"
        assert args.quantity == 1
        assert args.satisfied == 0
        assert args.variety_count == 0

    def test_reset_flags(self) -> None:
        """reset --stomach --tastiness sets correct booleans."""
        args = build_parser().parse_args(["reset", "--stomach", "--tastiness"])
        assert args.cmd == "reset"
        assert args.stomach is True
        assert args.tastiness is True
        assert args.availability is False

    def test_verbose_counting(self) -> None:
        """-v = 1, -vv = 2."""
        args_v = build_parser().parse_args(["-v", "plan"])
        assert args_v.verbose == 1

        args_vv = build_parser().parse_args(["-vv", "plan"])
        assert args_vv.verbose == 2

    def test_config_flag(self) -> None:
        """--config path.yml captured."""
        args = build_parser().parse_args(["--config", "my_config.yml", "plan"])
        assert args.config == "my_config.yml"

    def test_no_subcommand_defaults_none(self) -> None:
        """No subcommand → cmd=None."""
        args = build_parser().parse_args([])
        assert args.cmd is None
