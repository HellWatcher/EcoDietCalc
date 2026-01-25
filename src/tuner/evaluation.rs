use std::collections::HashMap;

use crate::models::Food;
use crate::planner::calculations::{
    calculate_sp, calculate_variety_mult, count_variety_qualifying, get_sp_delta,
    sum_all_weighted_nutrients, SpConfig,
};
use crate::planner::constants::{MAX_ITERATIONS, VARIETY_CAL_THRESHOLD};
use crate::state::FoodStateManager;
use crate::tuner::knobs::TunerKnobs;

/// Result of evaluating a single budget.
#[derive(Debug, Clone)]
pub struct BudgetResult {
    pub budget: f64,
    pub final_sp: f64,
    pub total_calories: f64,
    pub variety_count: usize,
    pub bites: usize,
    /// Balance ratio (min/max nutrient density), 0.0 to 1.0.
    pub balance_ratio: f64,
}

impl BudgetResult {
    /// SP gained per 100 kcal consumed.
    pub fn delta_sp_per_100kcal(&self) -> f64 {
        if self.total_calories > 0.0 {
            (self.final_sp / self.total_calories) * 100.0
        } else {
            0.0
        }
    }
}

/// Aggregated result of evaluating knobs across multiple budgets.
#[derive(Debug, Clone)]
pub struct EvaluationResult {
    pub knobs: TunerKnobs,
    pub avg_final_sp: f64,
    pub avg_delta_sp_per_100kcal: f64,
    pub avg_variety_count: f64,
    /// Average balance ratio across budgets.
    pub avg_balance_ratio: f64,
    pub per_budget: Vec<BudgetResult>,
}

impl EvaluationResult {
    /// Lexicographic comparison: (SP, efficiency, variety, balance).
    /// Higher is better for all metrics.
    pub fn cmp_score(&self, other: &Self) -> std::cmp::Ordering {
        // 1. Compare avg_final_sp first
        match self.avg_final_sp.partial_cmp(&other.avg_final_sp) {
            Some(std::cmp::Ordering::Equal) | None => {}
            Some(ord) => return ord,
        }
        // 2. Then avg_delta_sp_per_100kcal
        match self
            .avg_delta_sp_per_100kcal
            .partial_cmp(&other.avg_delta_sp_per_100kcal)
        {
            Some(std::cmp::Ordering::Equal) | None => {}
            Some(ord) => return ord,
        }
        // 3. Then avg_variety_count
        match self.avg_variety_count.partial_cmp(&other.avg_variety_count) {
            Some(std::cmp::Ordering::Equal) | None => {}
            Some(ord) => return ord,
        }
        // 4. Finally avg_balance_ratio
        self.avg_balance_ratio
            .partial_cmp(&other.avg_balance_ratio)
            .unwrap_or(std::cmp::Ordering::Equal)
    }

    /// Check if this result is dominated by another.
    ///
    /// Dominated means: other is >= in ALL metrics and > in at least one.
    pub fn is_dominated_by(&self, other: &Self) -> bool {
        let dominated_sp = other.avg_final_sp >= self.avg_final_sp;
        let dominated_variety = other.avg_variety_count >= self.avg_variety_count;
        let dominated_balance = other.avg_balance_ratio >= self.avg_balance_ratio;
        let dominated_efficiency = other.avg_delta_sp_per_100kcal >= self.avg_delta_sp_per_100kcal;

        let all_geq =
            dominated_sp && dominated_variety && dominated_balance && dominated_efficiency;

        let any_strictly_better = other.avg_final_sp > self.avg_final_sp
            || other.avg_variety_count > self.avg_variety_count
            || other.avg_balance_ratio > self.avg_balance_ratio
            || other.avg_delta_sp_per_100kcal > self.avg_delta_sp_per_100kcal;

        all_geq && any_strictly_better
    }
}

/// Extract Pareto-optimal (non-dominated) results.
///
/// Returns indices of results that are not dominated by any other result.
pub fn pareto_frontier(results: &[EvaluationResult]) -> Vec<usize> {
    results
        .iter()
        .enumerate()
        .filter(|(_, candidate)| {
            // Keep if no other result dominates this one
            !results.iter().any(|other| candidate.is_dominated_by(other))
        })
        .map(|(idx, _)| idx)
        .collect()
}

/// Select the most "balanced" result from a set using normalized distance to ideal.
///
/// The balanced result is the one closest to the ideal point (max of each metric)
/// using normalized Euclidean distance. This avoids sacrificing any metric too much.
pub fn select_balanced(results: &[EvaluationResult], indices: &[usize]) -> Option<usize> {
    if indices.is_empty() {
        return None;
    }

    // Find min/max for normalization
    let frontier_results: Vec<&EvaluationResult> = indices.iter().map(|&i| &results[i]).collect();

    let (min_sp, max_sp) = min_max(frontier_results.iter().map(|r| r.avg_final_sp));
    let (min_var, max_var) = min_max(frontier_results.iter().map(|r| r.avg_variety_count));
    let (min_bal, max_bal) = min_max(frontier_results.iter().map(|r| r.avg_balance_ratio));
    let (min_eff, max_eff) = min_max(frontier_results.iter().map(|r| r.avg_delta_sp_per_100kcal));

    // Find result with minimum distance to ideal (all metrics at 1.0 normalized)
    let mut best_idx = indices[0];
    let mut best_distance = f64::MAX;

    for &idx in indices {
        let r = &results[idx];

        // Normalize each metric to 0-1 (1 = best)
        let norm_sp = normalize(r.avg_final_sp, min_sp, max_sp);
        let norm_var = normalize(r.avg_variety_count, min_var, max_var);
        let norm_bal = normalize(r.avg_balance_ratio, min_bal, max_bal);
        let norm_eff = normalize(r.avg_delta_sp_per_100kcal, min_eff, max_eff);

        // Euclidean distance to ideal point (1, 1, 1, 1)
        let distance = ((1.0 - norm_sp).powi(2)
            + (1.0 - norm_var).powi(2)
            + (1.0 - norm_bal).powi(2)
            + (1.0 - norm_eff).powi(2))
        .sqrt();

        if distance < best_distance {
            best_distance = distance;
            best_idx = idx;
        }
    }

    Some(best_idx)
}

/// Helper: find min and max of an iterator.
fn min_max(iter: impl Iterator<Item = f64>) -> (f64, f64) {
    let values: Vec<f64> = iter.collect();
    let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    (min, max)
}

/// Helper: normalize a value to 0-1 range.
fn normalize(value: f64, min: f64, max: f64) -> f64 {
    if (max - min).abs() < 1e-10 {
        1.0 // All values are the same
    } else {
        (value - min) / (max - min)
    }
}

/// Configuration for hill climbing refinement.
#[derive(Debug, Clone)]
pub struct HillClimbConfig {
    /// Maximum iterations per result.
    pub max_iterations: usize,
    /// Perturbation factors to try (multiplicative).
    pub factors: Vec<f64>,
}

impl Default for HillClimbConfig {
    fn default() -> Self {
        Self {
            max_iterations: 20,
            factors: vec![0.9, 0.95, 1.05, 1.1],
        }
    }
}

/// Refine a result using hill climbing.
///
/// Tries small perturbations to each knob, keeping changes that improve
/// the result (not dominated by original). Returns the refined result.
pub fn hill_climb(
    initial: &EvaluationResult,
    foods: &[Food],
    budgets: &[f64],
    ranges: &crate::tuner::knobs::KnobRanges,
    config: &HillClimbConfig,
) -> EvaluationResult {
    let mut best = initial.clone();

    for _iteration in 0..config.max_iterations {
        let mut improved = false;

        // Try perturbing each knob
        for knob_idx in 0..TunerKnobs::NUM_KNOBS {
            for &factor in &config.factors {
                let candidate_knobs = best.knobs.perturb(knob_idx, factor, ranges);

                // Skip if knobs didn't change (hit boundary)
                if knobs_equal(&candidate_knobs, &best.knobs) {
                    continue;
                }

                let candidate = evaluate_knobs(&candidate_knobs, foods, budgets);

                // Accept if candidate dominates current best
                if best.is_dominated_by(&candidate) {
                    best = candidate;
                    improved = true;
                    break; // Move to next knob
                }
            }
        }

        if !improved {
            break; // Local maximum reached
        }
    }

    best
}

/// Check if two knob configurations are equal (within epsilon).
fn knobs_equal(a: &TunerKnobs, b: &TunerKnobs) -> bool {
    const EPS: f64 = 1e-9;
    (a.soft_bias_gamma - b.soft_bias_gamma).abs() < EPS
        && (a.tie_alpha - b.tie_alpha).abs() < EPS
        && (a.tie_beta - b.tie_beta).abs() < EPS
        && (a.tie_epsilon - b.tie_epsilon).abs() < EPS
        && (a.cal_floor - b.cal_floor).abs() < EPS
        && (a.cal_penalty_gamma - b.cal_penalty_gamma).abs() < EPS
        && (a.balance_bias_gamma - b.balance_bias_gamma).abs() < EPS
        && (a.repetition_penalty_gamma - b.repetition_penalty_gamma).abs() < EPS
}

/// Candidate food with computed scores (for tuner-specific ranking).
struct Candidate<'a> {
    food: &'a Food,
    rank_score: f64,
    soft_variety_bias: f64,
    proximity_bias: f64,
    balance_bias: f64,
    repetition_penalty: f64,
}

/// Calculate low-calorie penalty using tunable knobs.
fn low_calorie_penalty(calories: f64, knobs: &TunerKnobs) -> f64 {
    if calories >= knobs.cal_floor {
        return 0.0;
    }
    let x = 1.0 - (calories / knobs.cal_floor);
    -knobs.cal_penalty_gamma * (x * x)
}

/// Calculate soft-variety bias using tunable knobs.
fn soft_variety_bias(stomach: &HashMap<&Food, u32>, food: &Food, knobs: &TunerKnobs) -> f64 {
    let count_before = count_variety_qualifying(stomach);
    let mult_before = calculate_variety_mult(count_before);

    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let count_after = count_variety_qualifying(&new_stomach);
    let mult_after = calculate_variety_mult(count_after);

    let delta_mult = mult_after - mult_before;

    let (density, _) = sum_all_weighted_nutrients(&new_stomach);
    let ns_after = density.sum();

    knobs.soft_bias_gamma * ns_after * delta_mult
}

/// Calculate proximity bias using tunable knobs.
fn proximity_bias(stomach: &HashMap<&Food, u32>, food: &Food, knobs: &TunerKnobs) -> f64 {
    let current_count = stomach.get(&food).copied().unwrap_or(0);

    let p_before = (food.calories * current_count as f64) / VARIETY_CAL_THRESHOLD;
    let p_after = (food.calories * (current_count + 1) as f64) / VARIETY_CAL_THRESHOLD;

    let grow = (p_after.min(1.0) - p_before.min(1.0)).max(0.0);
    let over = (p_after - 1.0).max(0.0);

    let overshoot_penalty = if knobs.tie_alpha > 0.0 {
        over * (knobs.tie_beta / knobs.tie_alpha)
    } else {
        0.0
    };

    knobs.tie_alpha * (grow - overshoot_penalty)
}

/// Calculate balance improvement bias.
///
/// Rewards foods that improve the nutrient balance ratio (min/max).
fn balance_bias(stomach: &HashMap<&Food, u32>, food: &Food, knobs: &TunerKnobs) -> f64 {
    if knobs.balance_bias_gamma == 0.0 {
        return 0.0;
    }

    let (density_before, _) = sum_all_weighted_nutrients(stomach);
    let balance_before = if density_before.max() > 0.0 {
        density_before.min_nonzero() / density_before.max()
    } else {
        0.0
    };

    // Simulate adding food
    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let (density_after, _) = sum_all_weighted_nutrients(&new_stomach);
    let balance_after = if density_after.max() > 0.0 {
        let min_val = density_after.min_nonzero();
        if min_val == f64::MAX {
            0.0
        } else {
            min_val / density_after.max()
        }
    } else {
        0.0
    };

    // Reward improvement in balance ratio
    let improvement = balance_after - balance_before;
    knobs.balance_bias_gamma * improvement
}

/// Calculate repetition penalty.
///
/// Penalizes foods that are already heavily represented in the stomach.
fn repetition_penalty(stomach: &HashMap<&Food, u32>, food: &Food, knobs: &TunerKnobs) -> f64 {
    if knobs.repetition_penalty_gamma == 0.0 {
        return 0.0;
    }

    let this_count = stomach.get(&food).copied().unwrap_or(0) as f64;
    let total_bites: f64 = stomach.values().map(|&q| q as f64).sum();

    if total_bites == 0.0 {
        return 0.0;
    }

    // Fraction of stomach that's this food
    let fraction = this_count / total_bites;

    // Penalty increases with repetition
    -knobs.repetition_penalty_gamma * fraction
}

/// Choose the next best bite using tunable knobs.
fn choose_next_bite_with_knobs<'a>(
    manager: &'a FoodStateManager,
    knobs: &TunerKnobs,
    config: &SpConfig,
) -> Option<&'a Food> {
    let available = manager.all_available();
    if available.is_empty() {
        return None;
    }

    let stomach = manager.stomach_food_map();
    let cravings: &[String] = &[];

    let candidates: Vec<Candidate> = available
        .into_iter()
        .map(|food| {
            let sp_delta = get_sp_delta(&stomach, food, cravings, config);
            let penalty = low_calorie_penalty(food.calories, knobs);
            let rank_score = sp_delta + penalty;
            let sv_bias = soft_variety_bias(&stomach, food, knobs);
            let prox_bias = proximity_bias(&stomach, food, knobs);
            let bal_bias = balance_bias(&stomach, food, knobs);
            let rep_penalty = repetition_penalty(&stomach, food, knobs);

            Candidate {
                food,
                rank_score,
                soft_variety_bias: sv_bias,
                proximity_bias: prox_bias,
                balance_bias: bal_bias,
                repetition_penalty: rep_penalty,
            }
        })
        .collect();

    if candidates.is_empty() {
        return None;
    }

    let best_rank = candidates
        .iter()
        .map(|c| c.rank_score)
        .fold(f64::NEG_INFINITY, f64::max);

    let threshold = best_rank - knobs.tie_epsilon;
    let mut finalists: Vec<&Candidate> = candidates
        .iter()
        .filter(|c| c.rank_score >= threshold)
        .collect();

    finalists.sort_by(|a, b| {
        // Primary score includes all biases
        let primary_a = a.rank_score + a.soft_variety_bias + a.balance_bias + a.repetition_penalty;
        let primary_b = b.rank_score + b.soft_variety_bias + b.balance_bias + b.repetition_penalty;

        match primary_b.partial_cmp(&primary_a) {
            Some(std::cmp::Ordering::Equal) | None => b
                .proximity_bias
                .partial_cmp(&a.proximity_bias)
                .unwrap_or(std::cmp::Ordering::Equal),
            Some(ord) => ord,
        }
    });

    finalists.first().map(|c| c.food)
}

/// Generate a plan using tunable knobs (no cravings).
fn generate_plan_with_knobs(
    manager: &mut FoodStateManager,
    remaining_calories: f64,
    knobs: &TunerKnobs,
) -> (f64, usize) {
    let mut remaining = remaining_calories;
    let mut bites = 0;
    let config = SpConfig::default();

    for _ in 0..MAX_ITERATIONS {
        if remaining <= 0.0 {
            break;
        }

        if manager.all_available().is_empty() {
            break;
        }

        let food = match choose_next_bite_with_knobs(manager, knobs, &config) {
            Some(f) => f,
            None => break,
        };

        if food.calories > remaining && bites > 0 {
            break;
        }

        let food_name = food.name.clone();
        let food_calories = food.calories;

        let _ = manager.consume_food(&food_name);
        remaining -= food_calories;
        bites += 1;
    }

    let stomach = manager.stomach_food_map();
    let final_sp = calculate_sp(&stomach, &[], &config);
    (final_sp, bites)
}

/// Evaluate a single knob configuration for one budget.
pub fn evaluate_budget(foods: &[Food], budget: f64, knobs: &TunerKnobs) -> BudgetResult {
    // Clone foods and set high availability for testing
    let test_foods: Vec<Food> = foods
        .iter()
        .map(|f| {
            let mut f = f.clone();
            f.stomach = 0;
            f.available = 999;
            f
        })
        .collect();

    let mut manager = FoodStateManager::new(test_foods);
    let (final_sp, bites) = generate_plan_with_knobs(&mut manager, budget, knobs);

    let stomach = manager.stomach_food_map();
    let variety_count = count_variety_qualifying(&stomach);
    let total_calories = manager.total_stomach_calories();

    // Calculate balance ratio
    let (density, _) = sum_all_weighted_nutrients(&stomach);
    let balance_ratio = if density.max() > 0.0 {
        let min_val = density.min_nonzero();
        if min_val == f64::MAX {
            0.0
        } else {
            min_val / density.max()
        }
    } else {
        0.0
    };

    BudgetResult {
        budget,
        final_sp,
        total_calories,
        variety_count,
        bites,
        balance_ratio,
    }
}

/// Evaluate knobs across multiple budgets.
pub fn evaluate_knobs(knobs: &TunerKnobs, foods: &[Food], budgets: &[f64]) -> EvaluationResult {
    let per_budget: Vec<BudgetResult> = budgets
        .iter()
        .map(|&budget| evaluate_budget(foods, budget, knobs))
        .collect();

    let n = per_budget.len() as f64;
    let avg_final_sp = per_budget.iter().map(|r| r.final_sp).sum::<f64>() / n;
    let avg_delta_sp_per_100kcal = per_budget
        .iter()
        .map(|r| r.delta_sp_per_100kcal())
        .sum::<f64>()
        / n;
    let avg_variety_count = per_budget
        .iter()
        .map(|r| r.variety_count as f64)
        .sum::<f64>()
        / n;
    let avg_balance_ratio = per_budget.iter().map(|r| r.balance_ratio).sum::<f64>() / n;

    EvaluationResult {
        knobs: knobs.clone(),
        avg_final_sp,
        avg_delta_sp_per_100kcal,
        avg_variety_count,
        avg_balance_ratio,
        per_budget,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_foods() -> Vec<Food> {
        vec![
            Food {
                name: "Apple".to_string(),
                calories: 100.0,
                carbs: 20.0,
                protein: 1.0,
                fats: 0.5,
                vitamins: 5.0,
                tastiness: 2,
                stomach: 0,
                available: 50,
            },
            Food {
                name: "Bread".to_string(),
                calories: 500.0,
                carbs: 40.0,
                protein: 8.0,
                fats: 2.0,
                vitamins: 1.0,
                tastiness: 1,
                stomach: 0,
                available: 10,
            },
            Food {
                name: "Cheese".to_string(),
                calories: 300.0,
                carbs: 1.0,
                protein: 20.0,
                fats: 25.0,
                vitamins: 2.0,
                tastiness: 3,
                stomach: 0,
                available: 8,
            },
        ]
    }

    #[test]
    fn test_evaluate_budget() {
        let foods = sample_foods();
        let knobs = TunerKnobs::default();
        let result = evaluate_budget(&foods, 1000.0, &knobs);

        assert!(result.final_sp > 0.0);
        assert!(result.total_calories <= 1000.0 || result.bites == 1);
        assert!(result.bites > 0);
    }

    #[test]
    fn test_evaluate_knobs() {
        let foods = sample_foods();
        let knobs = TunerKnobs::default();
        let budgets = vec![900.0, 1200.0, 1500.0];
        let result = evaluate_knobs(&knobs, &foods, &budgets);

        assert_eq!(result.per_budget.len(), 3);
        assert!(result.avg_final_sp > 0.0);
    }

    #[test]
    fn test_cmp_score() {
        let knobs = TunerKnobs::default();
        let better = EvaluationResult {
            knobs: knobs.clone(),
            avg_final_sp: 100.0,
            avg_delta_sp_per_100kcal: 5.0,
            avg_variety_count: 3.0,
            avg_balance_ratio: 0.8,
            per_budget: vec![],
        };
        let worse = EvaluationResult {
            knobs,
            avg_final_sp: 90.0,
            avg_delta_sp_per_100kcal: 6.0,
            avg_variety_count: 4.0,
            avg_balance_ratio: 0.9,
            per_budget: vec![],
        };

        assert_eq!(better.cmp_score(&worse), std::cmp::Ordering::Greater);
    }

    #[test]
    fn test_pareto_frontier() {
        let knobs = TunerKnobs::default();

        // Create results with different trade-offs
        let results = vec![
            // Dominated by result 1 (worse in everything)
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 80.0,
                avg_delta_sp_per_100kcal: 3.0,
                avg_variety_count: 5.0,
                avg_balance_ratio: 0.5,
                per_budget: vec![],
            },
            // Max SP (pareto optimal)
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 100.0,
                avg_delta_sp_per_100kcal: 4.0,
                avg_variety_count: 8.0,
                avg_balance_ratio: 0.6,
                per_budget: vec![],
            },
            // Max variety (pareto optimal)
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 90.0,
                avg_delta_sp_per_100kcal: 3.5,
                avg_variety_count: 15.0,
                avg_balance_ratio: 0.7,
                per_budget: vec![],
            },
            // Balanced (pareto optimal)
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 95.0,
                avg_delta_sp_per_100kcal: 4.5,
                avg_variety_count: 12.0,
                avg_balance_ratio: 0.85,
                per_budget: vec![],
            },
        ];

        let frontier = pareto_frontier(&results);

        // Result 0 should be dominated (not in frontier)
        assert!(!frontier.contains(&0));
        // Results 1, 2, 3 should be in frontier
        assert!(frontier.contains(&1));
        assert!(frontier.contains(&2));
        assert!(frontier.contains(&3));
        assert_eq!(frontier.len(), 3);
    }

    #[test]
    fn test_select_balanced() {
        let knobs = TunerKnobs::default();

        let results = vec![
            // Max SP, low on others
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 100.0,
                avg_delta_sp_per_100kcal: 4.0,
                avg_variety_count: 5.0,
                avg_balance_ratio: 0.5,
                per_budget: vec![],
            },
            // Balanced across all
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 90.0,
                avg_delta_sp_per_100kcal: 4.5,
                avg_variety_count: 12.0,
                avg_balance_ratio: 0.8,
                per_budget: vec![],
            },
            // Max variety, low SP
            EvaluationResult {
                knobs: knobs.clone(),
                avg_final_sp: 75.0,
                avg_delta_sp_per_100kcal: 3.0,
                avg_variety_count: 20.0,
                avg_balance_ratio: 0.6,
                per_budget: vec![],
            },
        ];

        let indices = vec![0, 1, 2];
        let balanced = select_balanced(&results, &indices);

        // Result 1 should be selected as most balanced
        assert_eq!(balanced, Some(1));
    }

    #[test]
    fn test_cmp_score_balance_tiebreaker() {
        let knobs = TunerKnobs::default();

        // Two results identical in SP, efficiency, variety - differ only in balance
        let higher_balance = EvaluationResult {
            knobs: knobs.clone(),
            avg_final_sp: 100.0,
            avg_delta_sp_per_100kcal: 5.0,
            avg_variety_count: 8.0,
            avg_balance_ratio: 0.85,
            per_budget: vec![],
        };
        let lower_balance = EvaluationResult {
            knobs,
            avg_final_sp: 100.0,
            avg_delta_sp_per_100kcal: 5.0,
            avg_variety_count: 8.0,
            avg_balance_ratio: 0.70,
            per_budget: vec![],
        };

        // Higher balance should win
        assert_eq!(
            higher_balance.cmp_score(&lower_balance),
            std::cmp::Ordering::Greater
        );
    }

    #[test]
    fn test_knobs_equal() {
        use super::knobs_equal;

        let knobs1 = TunerKnobs::default();
        let knobs2 = TunerKnobs::default();
        assert!(knobs_equal(&knobs1, &knobs2));

        let mut knobs3 = TunerKnobs::default();
        knobs3.soft_bias_gamma = 999.0;
        assert!(!knobs_equal(&knobs1, &knobs3));
    }

    #[test]
    fn test_hill_climb_config_default() {
        let config = HillClimbConfig::default();
        assert_eq!(config.max_iterations, 20);
        assert_eq!(config.factors.len(), 4);
        assert!(config.factors.contains(&0.9));
        assert!(config.factors.contains(&1.1));
    }
}
