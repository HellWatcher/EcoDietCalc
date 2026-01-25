use std::collections::HashMap;
use std::sync::LazyLock;

/// Base skill points added to all SP calculations.
pub const BASE_SKILL_POINTS: f64 = 12.0;

/// Calories per food required to qualify for variety bonus.
pub const VARIETY_CAL_THRESHOLD: f64 = 2000.0;

/// Asymptotic cap for variety bonus (percentage points).
pub const VARIETY_BONUS_CAP_PP: f64 = 55.0;

/// Weight applied to taste bonus.
pub const TASTE_WEIGHT: f64 = 1.0;

/// Per-bite craving bonus in the nutrition multiplier (percentage points).
pub const CRAVING_BONUS_PP: f64 = 10.0;

/// Fraction (0..1) applied to final SP for satisfied cravings.
pub const CRAVING_SATISFIED_FRAC: f64 = 0.10;

/// Minimum calories per unit before penalty applies.
pub const CAL_FLOOR: f64 = 471.4887184802519;

/// Quadratic penalty strength for low-calorie foods.
pub const CAL_PENALTY_GAMMA: f64 = 1.5545327695570985;

/// Soft-variety ranking bias strength.
pub const SOFT_BIAS_GAMMA: f64 = 3.705894603947275;

/// Tie-break window in SP for near-equal candidates.
pub const TIE_EPSILON: f64 = 0.4043990501583793;

/// Proximity weight to variety threshold.
pub const TIE_ALPHA: f64 = 0.4239318414056884;

/// Small malus when overshooting the variety threshold.
pub const TIE_BETA: f64 = 0.03536204978722287;

/// Minimum delta to display variety change.
pub const VARIETY_DELTA_THRESHOLD: f64 = 0.01;

/// Minimum delta to display taste change.
pub const TASTE_DELTA_THRESHOLD: f64 = 0.01;

/// Maximum iterations (bites) per planning loop.
pub const MAX_ITERATIONS: usize = 100;

/// Map from tastiness rating to multiplier.
pub static TASTINESS_MULTIPLIERS: LazyLock<HashMap<i8, f64>> = LazyLock::new(|| {
    let mut m = HashMap::new();
    m.insert(-3, -0.30);
    m.insert(-2, -0.20);
    m.insert(-1, -0.10);
    m.insert(0, 0.00);
    m.insert(1, 0.10);
    m.insert(2, 0.20);
    m.insert(3, 0.30);
    m.insert(99, 0.00); // unknown
    m
});

/// Map from tastiness rating to human-readable name.
pub static TASTINESS_NAMES: LazyLock<HashMap<i8, &'static str>> = LazyLock::new(|| {
    let mut m = HashMap::new();
    m.insert(-3, "hated");
    m.insert(-2, "horrible");
    m.insert(-1, "bad");
    m.insert(0, "neutral");
    m.insert(1, "good");
    m.insert(2, "great");
    m.insert(3, "favorite");
    m.insert(99, "unknown");
    m
});

/// Get tastiness multiplier for a rating.
pub fn tastiness_multiplier(rating: i8) -> f64 {
    *TASTINESS_MULTIPLIERS.get(&rating).unwrap_or(&0.0)
}

/// Get tastiness name for a rating.
pub fn tastiness_name(rating: i8) -> &'static str {
    TASTINESS_NAMES.get(&rating).unwrap_or(&"unknown")
}
