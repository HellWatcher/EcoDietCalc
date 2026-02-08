"""Configuration loader for tunable constants.

Provides a Config dataclass and a loader that reads from YAML files,
falling back to default values if no config file is specified or found.

Exports
-------
Config
load_config
get_config
set_config_path
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default config file path (next to this module)
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.default.yml"

# Global config path override (set via CLI)
_config_path_override: Path | None = None


@dataclass
class AlgorithmConfig:
    """Algorithm tuning parameters."""

    soft_variety_bias_strength: float = 3.61
    tiebreak_score_window_sp: float = 0.449
    proximity_approach_weight: float = 0.977
    proximity_overshoot_penalty: float = 0.076
    low_calorie_threshold: int = 395
    low_calorie_penalty_strength: float = 2.48
    variety_bonus_cap_pp: float = 55.0
    tastiness_weight: float = 1.0
    balanced_diet_improvement_strength: float = 1.91
    repetition_penalty_strength: float = 1.25


@dataclass
class GameRulesConfig:
    """Game mechanics constants."""

    variety_cal_threshold: int = 2000
    craving_satisfied_frac: float = 0.10


@dataclass
class SafetyConfig:
    """Safety limits."""

    max_iterations: int = 100
    base_skill_points: int = 12


@dataclass
class DisplayConfig:
    """Display thresholds."""

    variety_delta_threshold: float = 0.01
    tastiness_delta_threshold: float = 0.01


@dataclass
class Config:
    """Root configuration container."""

    algorithm: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    game_rules: GameRulesConfig = field(default_factory=GameRulesConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)


def _merge_dict_into_dataclass(data: dict[str, Any], dc_instance: Any) -> None:
    """Merge dictionary values into a dataclass instance."""
    for key, value in data.items():
        if hasattr(dc_instance, key):
            setattr(dc_instance, key, value)


def _validate_config(config: Config) -> list[str]:
    """Validate config values and return list of errors."""
    errors: list[str] = []

    # Algorithm validations
    if config.algorithm.soft_variety_bias_strength < 0:
        errors.append("algorithm.soft_variety_bias_strength must be >= 0")
    if config.algorithm.tiebreak_score_window_sp < 0:
        errors.append("algorithm.tiebreak_score_window_sp must be >= 0")
    if config.algorithm.proximity_approach_weight < 0:
        errors.append("algorithm.proximity_approach_weight must be >= 0")
    if config.algorithm.low_calorie_threshold < 0:
        errors.append("algorithm.low_calorie_threshold must be >= 0")
    if config.algorithm.low_calorie_penalty_strength < 0:
        errors.append("algorithm.low_calorie_penalty_strength must be >= 0")
    if config.algorithm.variety_bonus_cap_pp <= 0:
        errors.append("algorithm.variety_bonus_cap_pp must be > 0")

    # Game rules validations
    if config.game_rules.variety_cal_threshold <= 0:
        errors.append("game_rules.variety_cal_threshold must be > 0")
    if not (0.0 <= config.game_rules.craving_satisfied_frac <= 1.0):
        errors.append("game_rules.craving_satisfied_frac must be in [0, 1]")

    # Safety validations
    if config.safety.max_iterations < 1:
        errors.append("safety.max_iterations must be >= 1")
    if config.safety.base_skill_points < 0:
        errors.append("safety.base_skill_points must be >= 0")

    return errors


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from YAML file.

    Parameters
    ----------
    path : str | Path | None
        Path to config file. If None, uses the global override
        (set via set_config_path) or falls back to config.default.yml.

    Returns
    -------
    Config
        Loaded and validated configuration.

    Raises
    ------
    FileNotFoundError
        If specified path doesn't exist.
    ValueError
        If config validation fails.
    """
    # Determine which path to use
    if path is not None:
        config_path = Path(path)
    elif _config_path_override is not None:
        config_path = _config_path_override
    else:
        config_path = _DEFAULT_CONFIG_PATH

    # Check file exists
    if not config_path.exists():
        if path is not None:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        # Fall back to defaults if default config doesn't exist
        return Config()

    # Load YAML
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    # Build config from defaults, then overlay loaded values
    config = Config()

    if "algorithm" in data:
        _merge_dict_into_dataclass(data["algorithm"], config.algorithm)
    if "game_rules" in data:
        _merge_dict_into_dataclass(data["game_rules"], config.game_rules)
    if "safety" in data:
        _merge_dict_into_dataclass(data["safety"], config.safety)
    if "display" in data:
        _merge_dict_into_dataclass(data["display"], config.display)

    # Validate
    errors = _validate_config(config)
    if errors:
        raise ValueError(
            "Config validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return config


def set_config_path(path: str | Path | None) -> None:
    """Set global config path override.

    Call this early (e.g., from CLI parsing) to affect subsequent
    imports of constants.

    Parameters
    ----------
    path : str | Path | None
        Path to config file, or None to reset to default.
    """
    global _config_path_override
    _config_path_override = Path(path) if path is not None else None


def get_config() -> Config:
    """Get the current configuration.

    Convenience wrapper around load_config() using the current
    global path override.

    Returns
    -------
    Config
        Current configuration.
    """
    return load_config()


# Singleton instance for lazy loading
_cached_config: Config | None = None


def get_cached_config() -> Config:
    """Get cached configuration (loads once).

    Returns
    -------
    Config
        Cached configuration instance.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config


def reload_config() -> Config:
    """Reload and cache configuration.

    Returns
    -------
    Config
        Freshly loaded configuration instance.
    """
    global _cached_config
    _cached_config = load_config()
    return _cached_config
