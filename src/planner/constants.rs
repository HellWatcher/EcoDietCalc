use std::collections::HashMap;
use std::sync::LazyLock;

/// Base skill points added after all multipliers.
pub const BASE_SKILL_POINTS: f64 = 12.0;

/// Calories per food required to qualify for variety bonus.
pub const VARIETY_CAL_THRESHOLD: f64 = 2000.0;

/// Maximum variety multiplier (1.0 = no bonus, 1.55 = +55%).
pub const VARIETY_MULT_MAX: f64 = 1.55;

/// Balance multiplier range: min (worst balance) to max (perfect balance).
pub const BALANCE_MULT_MIN: f64 = 0.5;
pub const BALANCE_MULT_MAX: f64 = 2.0;

/// Taste multiplier range: -3 rating to +3 rating.
pub const TASTE_MULT_MIN: f64 = 0.7;
pub const TASTE_MULT_MAX: f64 = 1.3;

/// Craving multiplier bonus per matched craving food.
pub const CRAVING_MULT_PER_MATCH: f64 = 0.1;

/// Default server skill gain multiplier.
pub const DEFAULT_SERVER_MULT: f64 = 1.0;

/// Default dinner party multiplier.
pub const DEFAULT_DINNER_PARTY_MULT: f64 = 1.0;

// ─────────────────────────────────────────────────────────────────────────────
// Tuner-derived constants (from hyperparameter optimization)
// Last updated: 2026-01-26 from tuner_best.json
// ─────────────────────────────────────────────────────────────────────────────

/// Minimum calories per unit before penalty applies.
pub const CAL_FLOOR: f64 = 395.0;

/// Quadratic penalty strength for low-calorie foods.
pub const CAL_PENALTY_GAMMA: f64 = 2.479;

/// Soft-variety ranking bias strength.
pub const SOFT_BIAS_GAMMA: f64 = 3.606;

/// Tie-break window in SP for near-equal candidates.
pub const TIE_EPSILON: f64 = 0.449;

/// Proximity weight to variety threshold.
pub const TIE_ALPHA: f64 = 0.977;

/// Small malus when overshooting the variety threshold.
pub const TIE_BETA: f64 = 0.076;

/// Bonus for foods that improve nutrient balance ratio.
pub const BALANCE_BIAS_GAMMA: f64 = 1.914;

/// Penalty for excessive repetition of same food.
pub const REPETITION_PENALTY_GAMMA: f64 = 1.255;

// ─────────────────────────────────────────────────────────────────────────────
// Display thresholds
// ─────────────────────────────────────────────────────────────────────────────

/// Minimum delta to display variety change.
pub const VARIETY_DELTA_THRESHOLD: f64 = 0.01;

/// Minimum delta to display taste change.
pub const TASTE_DELTA_THRESHOLD: f64 = 0.01;

/// Maximum iterations (bites) per planning loop.
pub const MAX_ITERATIONS: usize = 100;

/// Map from tastiness rating to multiplier (centered at 1.0).
/// Range: 0.7 (-3) to 1.3 (+3).
pub static TASTINESS_MULTIPLIERS: LazyLock<HashMap<i8, f64>> = LazyLock::new(|| {
    let mut m = HashMap::new();
    m.insert(-3, 0.70);
    m.insert(-2, 0.80);
    m.insert(-1, 0.90);
    m.insert(0, 1.00);
    m.insert(1, 1.10);
    m.insert(2, 1.20);
    m.insert(3, 1.30);
    m.insert(99, 1.00); // unknown = neutral
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
