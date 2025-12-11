"""Domain constants for meal planning and scoring (immutable mappings).

Conventions
-----------
- Percentages are **percentage points (pp)** unless noted.
- Fractions are in **0..1**.
- Tastiness scale: ``{-3,-2,-1,0,1,2,3}``; ``99`` = unknown.

Notes
-----
`TASTINESS_MULTIPLIERS` and `TASTINESS_NAMES` are exposed as read-only
mappings (via `MappingProxyType`). Adjust values here to tune behavior.
"""

# Read-only mapping wrapper + explicit "constant" typing
from types import (
    MappingProxyType,
)
from typing import (
    Final,
    Mapping,
)

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
    -3: "hated",
    -2: "horrible",
    -1: "bad",
    0: "neutral",
    1: "good",
    2: "great",
    3: "favorite",
    99: "unknown",
}

# Public, read-only views; mutations raise TypeError
TASTINESS_MULTIPLIERS: Final[Mapping[int, float]] = MappingProxyType(
    _TASTINESS_MULTIPLIERS_DICT
)

TASTINESS_NAMES: Final[Mapping[int, str]] = MappingProxyType(
    _TASTINESS_NAMES_DICT
)


# Calories required per food for variety bonus eligibility
VARIETY_CAL_THRESHOLD = 2000

# Max food additions allowed in a single planning loop (safety)
MAX_ITERATIONS = 100

# Default base SP points
BASE_SKILL_POINTS = 12

# Strength of the soft-variety ranking bias (Option A). 2–3 is a good default.
SOFT_BIAS_GAMMA = 0.3

# Tie-break window (in SP) for Option B.
# Candidates within this of the best true ΔSP are “near-equal”.
TIE_EPSILON = 0.85

# Proximity weight toward the 2000-cal threshold (alpha) and
# small malus when already past 1.0 (beta).
TIE_ALPHA = 0.22
TIE_BETA = 0.04

# Scalars aren't runtime-frozen; Final + UPPERCASE signals "do not reassign"
TASTE_WEIGHT: Final[float] = 1.0

# Hide noise in displays (minimum absolute delta to show, in pp)
VARIETY_DELTA_THRESHOLD: Final[float] = 0.01
TASTE_DELTA_THRESHOLD: Final[float] = 0.01

# Penalty applies per unit; shape is quadratic below CAL_FLOOR
CAL_FLOOR: Final[int] = 420  # calories/unit

# Strength of the low-calorie penalty (>=1; higher = harsher).
CAL_PENALTY_GAMMA: Final[float] = 0.2

# Asymptotic cap for variety bonus (see get_variety_bonus), in pp
VARIETY_BONUS_CAP_PP: Final[float] = 55.0

# Per-bite, within the nutrition multiplier (not a final SP multiplier), in pp
CRAVING_BONUS_PP: Final[float] = 10.0

# Final SP multiplier: (1 + satisfied_count * CRAVING_SATISFIED_FRAC)
CRAVING_SATISFIED_FRAC: Final[float] = 0.10  # fraction 0..1
