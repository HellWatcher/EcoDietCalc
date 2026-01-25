use std::collections::HashMap;

use crate::models::Food;
use crate::planner::calculations::{
    calculate_sp, calculate_variety_bonus, count_variety_qualifying, get_sp_delta,
    sum_all_weighted_nutrients,
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
    pub per_budget: Vec<BudgetResult>,
}

impl EvaluationResult {
    /// Lexicographic comparison: (avg_final_sp, avg_delta_sp_per_100kcal, avg_variety_count).
    /// Higher is better for all metrics.
    pub fn cmp_score(&self, other: &Self) -> std::cmp::Ordering {
        // Compare avg_final_sp first
        match self.avg_final_sp.partial_cmp(&other.avg_final_sp) {
            Some(std::cmp::Ordering::Equal) | None => {}
            Some(ord) => return ord,
        }
        // Then avg_delta_sp_per_100kcal
        match self
            .avg_delta_sp_per_100kcal
            .partial_cmp(&other.avg_delta_sp_per_100kcal)
        {
            Some(std::cmp::Ordering::Equal) | None => {}
            Some(ord) => return ord,
        }
        // Finally avg_variety_count
        self.avg_variety_count
            .partial_cmp(&other.avg_variety_count)
            .unwrap_or(std::cmp::Ordering::Equal)
    }
}

/// Candidate food with computed scores (for tuner-specific ranking).
struct Candidate<'a> {
    food: &'a Food,
    rank_score: f64,
    soft_variety_bias: f64,
    proximity_bias: f64,
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
    let bonus_before = calculate_variety_bonus(count_before);

    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let count_after = count_variety_qualifying(&new_stomach);
    let bonus_after = calculate_variety_bonus(count_after);

    let delta_pp = bonus_after - bonus_before;

    let (density, _) = sum_all_weighted_nutrients(&new_stomach);
    let ns_after = density.sum();

    knobs.soft_bias_gamma * ns_after * (delta_pp / 100.0)
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

/// Choose the next best bite using tunable knobs.
fn choose_next_bite_with_knobs<'a>(
    manager: &'a FoodStateManager,
    knobs: &TunerKnobs,
) -> Option<&'a Food> {
    let available = manager.all_available();
    if available.is_empty() {
        return None;
    }

    let stomach = manager.stomach_food_map();
    let cravings: &[String] = &[];
    let cravings_satisfied = 0;

    let candidates: Vec<Candidate> = available
        .into_iter()
        .map(|food| {
            let sp_delta = get_sp_delta(&stomach, food, cravings, cravings_satisfied);
            let penalty = low_calorie_penalty(food.calories, knobs);
            let rank_score = sp_delta + penalty;
            let sv_bias = soft_variety_bias(&stomach, food, knobs);
            let prox_bias = proximity_bias(&stomach, food, knobs);

            Candidate {
                food,
                rank_score,
                soft_variety_bias: sv_bias,
                proximity_bias: prox_bias,
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
        let primary_a = a.rank_score + a.soft_variety_bias;
        let primary_b = b.rank_score + b.soft_variety_bias;

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

    for _ in 0..MAX_ITERATIONS {
        if remaining <= 0.0 {
            break;
        }

        if manager.all_available().is_empty() {
            break;
        }

        let food = match choose_next_bite_with_knobs(manager, knobs) {
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
    let final_sp = calculate_sp(&stomach, &[], 0);
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

    BudgetResult {
        budget,
        final_sp,
        total_calories,
        variety_count,
        bites,
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
    let avg_delta_sp_per_100kcal = per_budget.iter().map(|r| r.delta_sp_per_100kcal()).sum::<f64>() / n;
    let avg_variety_count = per_budget.iter().map(|r| r.variety_count as f64).sum::<f64>() / n;

    EvaluationResult {
        knobs: knobs.clone(),
        avg_final_sp,
        avg_delta_sp_per_100kcal,
        avg_variety_count,
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
            per_budget: vec![],
        };
        let worse = EvaluationResult {
            knobs,
            avg_final_sp: 90.0,
            avg_delta_sp_per_100kcal: 6.0,
            avg_variety_count: 4.0,
            per_budget: vec![],
        };

        assert_eq!(better.cmp_score(&worse), std::cmp::Ordering::Greater);
    }
}
