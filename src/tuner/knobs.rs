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
            cal_penalty_gamma: rng.gen_range(ranges.cal_penalty_gamma.0..=ranges.cal_penalty_gamma.1),
        }
    }

    /// Format knobs as a compact string for display.
    pub fn display(&self) -> String {
        format!(
            "sbg={:.3} ta={:.3} tb={:.3} te={:.3} cf={:.1} cpg={:.3}",
            self.soft_bias_gamma,
            self.tie_alpha,
            self.tie_beta,
            self.tie_epsilon,
            self.cal_floor,
            self.cal_penalty_gamma
        )
    }
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
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand::rngs::StdRng;

    #[test]
    fn test_default_knobs_match_constants() {
        let knobs = TunerKnobs::default();
        assert_eq!(knobs.soft_bias_gamma, SOFT_BIAS_GAMMA);
        assert_eq!(knobs.tie_alpha, TIE_ALPHA);
        assert_eq!(knobs.tie_beta, TIE_BETA);
        assert_eq!(knobs.tie_epsilon, TIE_EPSILON);
        assert_eq!(knobs.cal_floor, CAL_FLOOR);
        assert_eq!(knobs.cal_penalty_gamma, CAL_PENALTY_GAMMA);
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
    }
}
