"""Tests for config loading, validation, and merging."""

import pytest
import yaml

from config import (
    Config,
    load_config,
    set_config_path,
)


class TestLoadConfig:
    """Tests for load_config() behavior."""

    def test_load_default_config(self) -> None:
        """Load config.default.yml; verify all sections present."""
        config = load_config()
        assert config.algorithm.soft_variety_bias_strength > 0
        assert config.game_rules.variety_cal_threshold > 0
        assert config.safety.max_iterations > 0
        assert config.display.variety_delta_threshold >= 0

    def test_load_missing_default_returns_defaults(self, tmp_path) -> None:
        """When default file missing, returns Config() defaults."""
        # Point to a nonexistent default by using set_config_path
        # then load without explicit path — falls back to default Config()
        missing = tmp_path / "nonexistent" / "config.yml"
        set_config_path(missing)
        try:
            config = load_config()
            default = Config()
            assert (
                config.algorithm.soft_variety_bias_strength
                == default.algorithm.soft_variety_bias_strength
            )
            assert config.safety.max_iterations == default.safety.max_iterations
        finally:
            set_config_path(None)

    def test_load_explicit_missing_raises(self, tmp_path) -> None:
        """load_config('nonexistent.yml') raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yml")

    def test_invalid_values_raise_value_error(self, tmp_path) -> None:
        """Negative strengths and out-of-range fractions raise ValueError."""
        bad_config = {
            "algorithm": {"soft_variety_bias_strength": -1.0},
        }
        config_file = tmp_path / "bad.yml"
        config_file.write_text(yaml.dump(bad_config))
        with pytest.raises(ValueError, match="soft_variety_bias_strength"):
            load_config(config_file)

    def test_invalid_fraction_raises(self, tmp_path) -> None:
        """craving_satisfied_frac outside [0,1] raises ValueError."""
        bad_config = {
            "game_rules": {"craving_satisfied_frac": 1.5},
        }
        config_file = tmp_path / "bad_frac.yml"
        config_file.write_text(yaml.dump(bad_config))
        with pytest.raises(ValueError, match="craving_satisfied_frac"):
            load_config(config_file)

    def test_partial_config_merges_with_defaults(self, tmp_path) -> None:
        """YAML with only algorithm section; rest uses defaults."""
        partial = {"algorithm": {"soft_variety_bias_strength": 5.0}}
        config_file = tmp_path / "partial.yml"
        config_file.write_text(yaml.dump(partial))

        config = load_config(config_file)
        assert config.algorithm.soft_variety_bias_strength == 5.0
        # Unspecified sections use defaults
        default = Config()
        assert (
            config.game_rules.variety_cal_threshold
            == default.game_rules.variety_cal_threshold
        )
        assert config.safety.max_iterations == default.safety.max_iterations

    def test_unknown_keys_ignored(self, tmp_path) -> None:
        """Extra keys in YAML don't crash."""
        data = {
            "algorithm": {
                "soft_variety_bias_strength": 3.0,
                "totally_fake_key": 999,
            },
            "nonexistent_section": {"foo": "bar"},
        }
        config_file = tmp_path / "extra.yml"
        config_file.write_text(yaml.dump(data))

        config = load_config(config_file)
        assert config.algorithm.soft_variety_bias_strength == 3.0

    def test_empty_yaml_returns_defaults(self, tmp_path) -> None:
        """Empty file loads default Config."""
        config_file = tmp_path / "empty.yml"
        config_file.write_text("")

        config = load_config(config_file)
        default = Config()
        assert (
            config.algorithm.soft_variety_bias_strength
            == default.algorithm.soft_variety_bias_strength
        )
        assert (
            config.game_rules.craving_satisfied_frac
            == default.game_rules.craving_satisfied_frac
        )

    def test_set_config_path_overrides_default(self, tmp_path) -> None:
        """set_config_path() affects subsequent load_config() calls."""
        custom = {"algorithm": {"taste_weight": 2.5}}
        config_file = tmp_path / "custom.yml"
        config_file.write_text(yaml.dump(custom))

        set_config_path(config_file)
        try:
            config = load_config()
            assert config.algorithm.taste_weight == 2.5
        finally:
            set_config_path(None)
