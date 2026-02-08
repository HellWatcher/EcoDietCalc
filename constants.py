"""Domain constants for meal planning and scoring (immutable mappings).

Constants are loaded from config.default.yml (or custom config if specified
via CLI --config flag). Use `config.set_config_path()` before importing
this module to override the config file.

Conventions
-----------
- Percentages are **percentage points (pp)** unless noted.
- Fractions are in **0..1**.
- Tastiness scale: ``{-3,-2,-1,0,1,2,3}``; ``99`` = unknown.

Notes
-----
`TASTINESS_MULTIPLIERS` and `TASTINESS_NAMES` are exposed as read-only
mappings (via `MappingProxyType`). Adjust values in config file to tune behavior.
"""

# Read-only mapping wrapper + explicit "constant" typing
from types import (
    MappingProxyType,
)
from typing import (
    Final,
    Mapping,
)

from config import get_cached_config

# Load config once at module import
_cfg = get_cached_config()

# --- Tastiness ---------------------------------------------------------------

# Private, mutable source dict (edit values here only)
# Fractions (e.g., +0.20 means +20 percentage points before weighting)
_TASTINESS_MULTIPLIERS_DICT: Final[dict[int, float]] = {
    -3: -0.30,
    -2: -0.20,
    -1: -0.10,
    0: 0.00,
    1: 0.10,
    2: 0.20,
    3: 0.30,
    99: 0.00,  # unknown
}

# Human labels for UI/logs; not used in calculations
_TASTINESS_NAMES_DICT: Final[dict[int, str]] = {
    -3: "worst",
    -2: "horrible",
    -1: "bad",
    0: "ok",
    1: "good",
    2: "delicious",
    3: "favorite",
    99: "unknown",
}

# Public, read-only views; mutations raise TypeError
TASTINESS_MULTIPLIERS: Final[Mapping[int, float]] = MappingProxyType(
    _TASTINESS_MULTIPLIERS_DICT
)

TASTINESS_NAMES: Final[Mapping[int, str]] = MappingProxyType(_TASTINESS_NAMES_DICT)


# ─────────────────────────────────────────────────────────────────────────────
# Game rules (from config)
# ─────────────────────────────────────────────────────────────────────────────

# Calories required per food for variety bonus eligibility
VARIETY_CAL_THRESHOLD: Final[int] = _cfg.game_rules.variety_cal_threshold

# ─────────────────────────────────────────────────────────────────────────────
# Safety limits (from config)
# ─────────────────────────────────────────────────────────────────────────────

# Max food additions allowed in a single planning loop (safety)
MAX_ITERATIONS: Final[int] = _cfg.safety.max_iterations

# Default base SP points
BASE_SKILL_POINTS: Final[int] = _cfg.safety.base_skill_points

# ─────────────────────────────────────────────────────────────────────────────
# Tuner-derived constants (from config)
# ─────────────────────────────────────────────────────────────────────────────

# Strength of the soft-variety ranking bias.
SOFT_VARIETY_BIAS_STRENGTH: Final[float] = _cfg.algorithm.soft_variety_bias_strength

# Tie-break window (in SP) for near-equal candidates.
TIEBREAK_SCORE_WINDOW_SP: Final[float] = _cfg.algorithm.tiebreak_score_window_sp

# Proximity weight toward the 2000-cal threshold and
# small malus when already past 1.0.
PROXIMITY_APPROACH_WEIGHT: Final[float] = _cfg.algorithm.proximity_approach_weight
PROXIMITY_OVERSHOOT_PENALTY: Final[float] = _cfg.algorithm.proximity_overshoot_penalty

# Bonus for foods that improve nutrient balance ratio.
BALANCED_DIET_IMPROVEMENT_STRENGTH: Final[float] = (
    _cfg.algorithm.balanced_diet_improvement_strength
)

# Penalty for excessive repetition of same food.
REPETITION_PENALTY_STRENGTH: Final[float] = _cfg.algorithm.repetition_penalty_strength

# Scalars aren't runtime-frozen; Final + UPPERCASE signals "do not reassign"
TASTINESS_WEIGHT: Final[float] = _cfg.algorithm.tastiness_weight

# ─────────────────────────────────────────────────────────────────────────────
# Display thresholds (from config)
# ─────────────────────────────────────────────────────────────────────────────

# Hide noise in displays (minimum absolute delta to show, in pp)
VARIETY_DELTA_THRESHOLD: Final[float] = _cfg.display.variety_delta_threshold
TASTINESS_DELTA_THRESHOLD: Final[float] = _cfg.display.tastiness_delta_threshold

# ─────────────────────────────────────────────────────────────────────────────
# Algorithm parameters (from config)
# ─────────────────────────────────────────────────────────────────────────────

# Penalty applies per unit; shape is quadratic below threshold
LOW_CALORIE_THRESHOLD: Final[int] = _cfg.algorithm.low_calorie_threshold

# Strength of the low-calorie penalty (>=1; higher = harsher).
LOW_CALORIE_PENALTY_STRENGTH: Final[float] = _cfg.algorithm.low_calorie_penalty_strength

# Asymptotic cap for variety bonus (see get_variety_bonus), in pp
VARIETY_BONUS_CAP_PP: Final[float] = _cfg.algorithm.variety_bonus_cap_pp

# ─────────────────────────────────────────────────────────────────────────────
# Craving system constants (from config)
# ─────────────────────────────────────────────────────────────────────────────

# Final SP multiplier: (1 + satisfied_count * CRAVING_SATISFIED_FRAC)
CRAVING_SATISFIED_FRAC: Final[float] = _cfg.game_rules.craving_satisfied_frac
