"""Tests for interactive prompt functions."""

from interface.prompts import (
    collect_user_constraints,
    prompt_current_calories,
    prompt_for_cravings_satisfied,
    prompt_for_tastiness,
    prompt_max_calories,
    prompt_yes_no,
)


class TestPromptCurrentCalories:
    """Tests for prompt_current_calories()."""

    def test_valid_input(self, monkeypatch) -> None:
        """ "500" → 500."""
        monkeypatch.setattr("builtins.input", lambda _: "500")
        assert prompt_current_calories() == 500

    def test_rejects_negative(self, monkeypatch) -> None:
        """ "-1" then "0" → 0."""
        responses = iter(["-1", "0"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        assert prompt_current_calories() == 0


class TestPromptMaxCalories:
    """Tests for prompt_max_calories()."""

    def test_rejects_below_current(self, monkeypatch) -> None:
        """max < current retries."""
        responses = iter(["100", "600"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        assert prompt_max_calories(500) == 600


class TestPromptCravingsSatisfied:
    """Tests for prompt_for_cravings_satisfied()."""

    def test_empty_default(self, monkeypatch) -> None:
        """ "" → 0."""
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert prompt_for_cravings_satisfied() == 0

    def test_valid_input(self, monkeypatch) -> None:
        """ "2" → 2."""
        monkeypatch.setattr("builtins.input", lambda _: "2")
        assert prompt_for_cravings_satisfied() == 2


class TestPromptForTastiness:
    """Tests for prompt_for_tastiness()."""

    def test_valid_rating(self, monkeypatch) -> None:
        """ "3" → 3."""
        monkeypatch.setattr("builtins.input", lambda _: "3")
        assert prompt_for_tastiness("Test Food") == 3

    def test_skip_returns_unknown(self, monkeypatch) -> None:
        """ "" → 99."""
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert prompt_for_tastiness("Test Food") == 99

    def test_invalid_then_valid(self, monkeypatch) -> None:
        """ "5" then "2" → 2."""
        responses = iter(["5", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        assert prompt_for_tastiness("Test Food") == 2


class TestPromptYesNo:
    """Tests for prompt_yes_no()."""

    def test_default_yes(self, monkeypatch) -> None:
        """ "" → True (default=True)."""
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert prompt_yes_no("Continue?") is True

    def test_explicit_no(self, monkeypatch) -> None:
        """ "n" → False."""
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert prompt_yes_no("Continue?") is False

    def test_default_no(self, monkeypatch) -> None:
        """ "" → False (default=False)."""
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert prompt_yes_no("Continue?", default=False) is False


class TestCollectUserConstraints:
    """Tests for collect_user_constraints()."""

    def test_integration(self, monkeypatch) -> None:
        """Mocks all inputs, verifies tuple."""
        # Order: current_cal, max_cal, cravings_satisfied, craving name
        responses = iter(["200", "1000", "1", "bannock"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))

        cravings, cravings_satisfied, remaining = collect_user_constraints()
        assert cravings == ["bannock"]
        assert cravings_satisfied == 1
        assert remaining == 800  # 1000 - 200

    def test_no_craving(self, monkeypatch) -> None:
        """Empty craving input returns empty list."""
        responses = iter(["0", "2000", "0", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))

        cravings, cravings_satisfied, remaining = collect_user_constraints()
        assert cravings == []
        assert cravings_satisfied == 0
        assert remaining == 2000
