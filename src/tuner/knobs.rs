use rand::Rng;
use serde::{Deserialize, Serialize};

use crate::planner::constants::{
    CAL_FLOOR, CAL_PENALTY_GAMMA, SOFT_BIAS_GAMMA, TIE_ALPHA, TIE_BETA, TIE_EPSILON,
};

/// Runtime-configurable planner knobs for tuning.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TunerKnobs {
    pub soft_bias_gamma: f64,
    pub tie_alpha: f64,
    pub tie_beta: f64,
    pub tie_epsilon: f64,
    pub cal_floor: f64,
    pub cal_penalty_gamma: f64,
    /// Bonus for foods that improve nutrient balance ratio.
    pub balance_bias_gamma: f64,
    /// Penalty for excessive repetition of same food.
    pub repetition_penalty_gamma: f64,
}

impl Default for TunerKnobs {
    fn default() -> Self {
        Self {
            soft_bias_gamma: SOFT_BIAS_GAMMA,
            tie_alpha: TIE_ALPHA,
            tie_beta: TIE_BETA,
            tie_epsilon: TIE_EPSILON,
            cal_floor: CAL_FLOOR,
            cal_penalty_gamma: CAL_PENALTY_GAMMA,
            // New knobs default to 0.0 (disabled) for backward compatibility
            balance_bias_gamma: 0.0,
            repetition_penalty_gamma: 0.0,
        }
    }
}

impl TunerKnobs {
    /// Generate random knobs within the given ranges.
    pub fn random(rng: &mut impl Rng, ranges: &KnobRanges) -> Self {
        Self {
            soft_bias_gamma: rng.gen_range(ranges.soft_bias_gamma.0..=ranges.soft_bias_gamma.1),
            tie_alpha: rng.gen_range(ranges.tie_alpha.0..=ranges.tie_alpha.1),
            tie_beta: rng.gen_range(ranges.tie_beta.0..=ranges.tie_beta.1),
            tie_epsilon: rng.gen_range(ranges.tie_epsilon.0..=ranges.tie_epsilon.1),
            cal_floor: rng.gen_range(ranges.cal_floor.0..=ranges.cal_floor.1),
            cal_penalty_gamma: rng
                .gen_range(ranges.cal_penalty_gamma.0..=ranges.cal_penalty_gamma.1),
            balance_bias_gamma: rng
                .gen_range(ranges.balance_bias_gamma.0..=ranges.balance_bias_gamma.1),
            repetition_penalty_gamma: rng
                .gen_range(ranges.repetition_penalty_gamma.0..=ranges.repetition_penalty_gamma.1),
        }
    }

    /// Format knobs as a compact string for display.
    pub fn display(&self) -> String {
        format!(
            "sbg={:.3} ta={:.3} tb={:.3} te={:.3} cf={:.1} cpg={:.3} bbg={:.3} rpg={:.3}",
            self.soft_bias_gamma,
            self.tie_alpha,
            self.tie_beta,
            self.tie_epsilon,
            self.cal_floor,
            self.cal_penalty_gamma,
            self.balance_bias_gamma,
            self.repetition_penalty_gamma
        )
    }

    /// Create a copy with one knob multiplied by a factor.
    ///
    /// `knob_idx` maps to: 0=soft_bias_gamma, 1=tie_alpha, 2=tie_beta,
    /// 3=tie_epsilon, 4=cal_floor, 5=cal_penalty_gamma, 6=balance_bias_gamma,
    /// 7=repetition_penalty_gamma.
    ///
    /// The result is clamped to the given ranges.
    pub fn perturb(&self, knob_idx: usize, factor: f64, ranges: &KnobRanges) -> Self {
        let mut new = self.clone();
        match knob_idx {
            0 => {
                new.soft_bias_gamma = (self.soft_bias_gamma * factor)
                    .clamp(ranges.soft_bias_gamma.0, ranges.soft_bias_gamma.1);
            }
            1 => {
                new.tie_alpha =
                    (self.tie_alpha * factor).clamp(ranges.tie_alpha.0, ranges.tie_alpha.1);
            }
            2 => {
                new.tie_beta = (self.tie_beta * factor).clamp(ranges.tie_beta.0, ranges.tie_beta.1);
            }
            3 => {
                new.tie_epsilon =
                    (self.tie_epsilon * factor).clamp(ranges.tie_epsilon.0, ranges.tie_epsilon.1);
            }
            4 => {
                new.cal_floor =
                    (self.cal_floor * factor).clamp(ranges.cal_floor.0, ranges.cal_floor.1);
            }
            5 => {
                new.cal_penalty_gamma = (self.cal_penalty_gamma * factor)
                    .clamp(ranges.cal_penalty_gamma.0, ranges.cal_penalty_gamma.1);
            }
            6 => {
                new.balance_bias_gamma = (self.balance_bias_gamma * factor)
                    .clamp(ranges.balance_bias_gamma.0, ranges.balance_bias_gamma.1);
            }
            7 => {
                new.repetition_penalty_gamma = (self.repetition_penalty_gamma * factor).clamp(
                    ranges.repetition_penalty_gamma.0,
                    ranges.repetition_penalty_gamma.1,
                );
            }
            _ => {} // Invalid index, return unchanged
        }
        new
    }

    /// Number of tunable knobs.
    pub const NUM_KNOBS: usize = 8;
}

/// Min/max ranges for each tunable knob.
#[derive(Debug, Clone)]
pub struct KnobRanges {
    /// (min, max) for SOFT_BIAS_GAMMA
    pub soft_bias_gamma: (f64, f64),
    /// (min, max) for TIE_ALPHA
    pub tie_alpha: (f64, f64),
    /// (min, max) for TIE_BETA
    pub tie_beta: (f64, f64),
    /// (min, max) for TIE_EPSILON
    pub tie_epsilon: (f64, f64),
    /// (min, max) for CAL_FLOOR
    pub cal_floor: (f64, f64),
    /// (min, max) for CAL_PENALTY_GAMMA
    pub cal_penalty_gamma: (f64, f64),
    /// (min, max) for BALANCE_BIAS_GAMMA
    pub balance_bias_gamma: (f64, f64),
    /// (min, max) for REPETITION_PENALTY_GAMMA
    pub repetition_penalty_gamma: (f64, f64),
}

impl Default for KnobRanges {
    fn default() -> Self {
        Self {
            soft_bias_gamma: (0.0, 6.0),
            tie_alpha: (0.0, 1.0),
            tie_beta: (0.0, 0.2),
            tie_epsilon: (0.1, 1.0),
            cal_floor: (200.0, 500.0),
            cal_penalty_gamma: (0.0, 4.0),
            // New knob ranges
            balance_bias_gamma: (0.0, 3.0),
            repetition_penalty_gamma: (0.0, 2.0),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    #[test]
    fn test_default_knobs_match_constants() {
        let knobs = TunerKnobs::default();
        assert_eq!(knobs.soft_bias_gamma, SOFT_BIAS_GAMMA);
        assert_eq!(knobs.tie_alpha, TIE_ALPHA);
        assert_eq!(knobs.tie_beta, TIE_BETA);
        assert_eq!(knobs.tie_epsilon, TIE_EPSILON);
        assert_eq!(knobs.cal_floor, CAL_FLOOR);
        assert_eq!(knobs.cal_penalty_gamma, CAL_PENALTY_GAMMA);
        // New knobs default to 0.0 (disabled)
        assert_eq!(knobs.balance_bias_gamma, 0.0);
        assert_eq!(knobs.repetition_penalty_gamma, 0.0);
    }

    #[test]
    fn test_random_knobs_within_range() {
        let mut rng = StdRng::seed_from_u64(42);
        let ranges = KnobRanges::default();
        let knobs = TunerKnobs::random(&mut rng, &ranges);

        assert!(knobs.soft_bias_gamma >= ranges.soft_bias_gamma.0);
        assert!(knobs.soft_bias_gamma <= ranges.soft_bias_gamma.1);
        assert!(knobs.tie_alpha >= ranges.tie_alpha.0);
        assert!(knobs.tie_alpha <= ranges.tie_alpha.1);
        assert!(knobs.tie_beta >= ranges.tie_beta.0);
        assert!(knobs.tie_beta <= ranges.tie_beta.1);
        assert!(knobs.tie_epsilon >= ranges.tie_epsilon.0);
        assert!(knobs.tie_epsilon <= ranges.tie_epsilon.1);
        assert!(knobs.cal_floor >= ranges.cal_floor.0);
        assert!(knobs.cal_floor <= ranges.cal_floor.1);
        assert!(knobs.cal_penalty_gamma >= ranges.cal_penalty_gamma.0);
        assert!(knobs.cal_penalty_gamma <= ranges.cal_penalty_gamma.1);
        // New knobs
        assert!(knobs.balance_bias_gamma >= ranges.balance_bias_gamma.0);
        assert!(knobs.balance_bias_gamma <= ranges.balance_bias_gamma.1);
        assert!(knobs.repetition_penalty_gamma >= ranges.repetition_penalty_gamma.0);
        assert!(knobs.repetition_penalty_gamma <= ranges.repetition_penalty_gamma.1);
    }

    #[test]
    fn test_perturb_modifies_single_knob() {
        let knobs = TunerKnobs {
            soft_bias_gamma: 2.0,
            tie_alpha: 0.5,
            tie_beta: 0.1,
            tie_epsilon: 0.5,
            cal_floor: 350.0,
            cal_penalty_gamma: 2.0,
            balance_bias_gamma: 1.0,
            repetition_penalty_gamma: 1.0,
        };
        let ranges = KnobRanges::default();

        // Perturb soft_bias_gamma by 1.1x
        let perturbed = knobs.perturb(0, 1.1, &ranges);
        assert!((perturbed.soft_bias_gamma - 2.2).abs() < 0.001);
        // Other knobs unchanged
        assert_eq!(perturbed.tie_alpha, 0.5);
        assert_eq!(perturbed.cal_floor, 350.0);

        // Perturb cal_floor by 0.9x
        let perturbed2 = knobs.perturb(4, 0.9, &ranges);
        assert!((perturbed2.cal_floor - 315.0).abs() < 0.001);
        // soft_bias_gamma unchanged
        assert_eq!(perturbed2.soft_bias_gamma, 2.0);
    }

    #[test]
    fn test_perturb_clamps_to_range() {
        let knobs = TunerKnobs {
            soft_bias_gamma: 5.5, // Near max of 6.0
            tie_alpha: 0.05,      // Near min of 0.0
            tie_beta: 0.1,
            tie_epsilon: 0.5,
            cal_floor: 350.0,
            cal_penalty_gamma: 2.0,
            balance_bias_gamma: 1.0,
            repetition_penalty_gamma: 1.0,
        };
        let ranges = KnobRanges::default();

        // Perturb soft_bias_gamma by 1.2x would exceed max
        let perturbed = knobs.perturb(0, 1.2, &ranges);
        assert_eq!(perturbed.soft_bias_gamma, 6.0); // Clamped to max

        // Perturb tie_alpha by 0.5x would go below min
        let perturbed2 = knobs.perturb(1, 0.5, &ranges);
        assert_eq!(perturbed2.tie_alpha, 0.025); // 0.05 * 0.5, still above 0
    }
}
