use std::collections::HashMap;

use crate::models::{Food, MealPlanItem};
use crate::planner::calculations::{
    calculate_sp, calculate_taste_mult, calculate_variety_mult, count_variety_qualifying,
    get_sp_delta, sum_all_weighted_nutrients, SpConfig,
};
use crate::planner::constants::*;
use crate::state::FoodStateManager;

/// Candidate food with its computed scores.
#[derive(Debug)]
struct Candidate<'a> {
    food: &'a Food,
    rank_score: f64,
    soft_variety_bias: f64,
    proximity_bias: f64,
}

/// Snapshot of multipliers and SP at a point in time.
struct StateSnapshot {
    variety_mult: f64,
    taste_mult: f64,
    sp: f64,
}

/// Calculate current state snapshot from stomach.
fn calculate_state_snapshot(
    stomach: &HashMap<&Food, u32>,
    cravings: &[String],
    config: &SpConfig,
) -> StateSnapshot {
    let variety_count = count_variety_qualifying(stomach);
    StateSnapshot {
        variety_mult: calculate_variety_mult(variety_count),
        taste_mult: calculate_taste_mult(stomach),
        sp: calculate_sp(stomach, cravings, config),
    }
}

/// Check if a food name matches any craving (case-insensitive).
fn is_craving_match(food_name: &str, cravings: &[String]) -> bool {
    let food_lower = food_name.to_lowercase();
    cravings.iter().any(|c| c.to_lowercase() == food_lower)
}

/// Calculate low-calorie penalty.
///
/// Quadratic penalty for foods below CAL_FLOOR.
fn low_calorie_penalty(calories: f64) -> f64 {
    if calories >= CAL_FLOOR {
        return 0.0;
    }
    let x = 1.0 - (calories / CAL_FLOOR);
    -CAL_PENALTY_GAMMA * (x * x)
}

/// Calculate soft-variety bias.
///
/// Bias based on change in variety multiplier.
fn soft_variety_bias(stomach: &HashMap<&Food, u32>, food: &Food) -> f64 {
    let count_before = count_variety_qualifying(stomach);
    let mult_before = calculate_variety_mult(count_before);

    // Simulate adding the food
    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let count_after = count_variety_qualifying(&new_stomach);
    let mult_after = calculate_variety_mult(count_after);

    // Delta in multiplier terms (e.g., 1.2 -> 1.3 = +0.1)
    let delta_mult = mult_after - mult_before;

    // Get nutrient sum after adding food
    let (density, _) = sum_all_weighted_nutrients(&new_stomach);
    let ns_after = density.sum();

    SOFT_BIAS_GAMMA * ns_after * delta_mult
}

/// Calculate proximity bias.
///
/// Favor moving toward VARIETY_CAL_THRESHOLD for this specific food.
fn proximity_bias(stomach: &HashMap<&Food, u32>, food: &Food) -> f64 {
    let current_count = stomach.get(&food).copied().unwrap_or(0);

    let p_before = (food.calories * current_count as f64) / VARIETY_CAL_THRESHOLD;
    let p_after = (food.calories * (current_count + 1) as f64) / VARIETY_CAL_THRESHOLD;

    // Movement toward threshold (capped at 1.0)
    let grow = (p_after.min(1.0) - p_before.min(1.0)).max(0.0);

    // Overshoot beyond threshold
    let over = (p_after - 1.0).max(0.0);

    let overshoot_penalty = if TIE_ALPHA > 0.0 {
        over * (TIE_BETA / TIE_ALPHA)
    } else {
        0.0
    };

    TIE_ALPHA * (grow - overshoot_penalty)
}

/// Choose the next best bite from available foods.
///
/// Uses multi-stage ranking:
/// 1. Compute raw ΔSP + low-calorie penalty
/// 2. Filter near-equal candidates within TIE_EPSILON
/// 3. Apply soft-variety bias + proximity tie-break
pub fn choose_next_bite<'a>(
    manager: &'a FoodStateManager,
    cravings: &[String],
    config: &SpConfig,
) -> Option<&'a Food> {
    let available = manager.all_available();
    if available.is_empty() {
        return None;
    }

    let stomach = manager.stomach_food_map();

    // Stage 1: Compute scores for all candidates
    let candidates: Vec<Candidate> = available
        .into_iter()
        .map(|food| {
            let sp_delta = get_sp_delta(&stomach, food, cravings, config);
            let penalty = low_calorie_penalty(food.calories);
            let rank_score = sp_delta + penalty;
            let sv_bias = soft_variety_bias(&stomach, food);
            let prox_bias = proximity_bias(&stomach, food);

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

    // Find best rank score
    let best_rank = candidates
        .iter()
        .map(|c| c.rank_score)
        .fold(f64::NEG_INFINITY, f64::max);

    // Stage 2: Filter to near-equal candidates
    let threshold = best_rank - TIE_EPSILON;
    let mut finalists: Vec<&Candidate> = candidates
        .iter()
        .filter(|c| c.rank_score >= threshold)
        .collect();

    // Stage 3: Sort by primary rank (with soft-variety) then proximity
    finalists.sort_by(|a, b| {
        let primary_a = a.rank_score + a.soft_variety_bias;
        let primary_b = b.rank_score + b.soft_variety_bias;

        // Higher is better, so reverse the comparison
        match primary_b.partial_cmp(&primary_a) {
            Some(std::cmp::Ordering::Equal) | None => {
                // Tie-break by proximity
                b.proximity_bias
                    .partial_cmp(&a.proximity_bias)
                    .unwrap_or(std::cmp::Ordering::Equal)
            }
            Some(ord) => ord,
        }
    });

    finalists.first().map(|c| c.food)
}

/// Pick a feasible craving if one exists.
///
/// Returns the craving food with highest ΔSP among available cravings.
pub fn pick_feasible_craving<'a>(
    manager: &'a FoodStateManager,
    cravings: &[String],
    config: &SpConfig,
) -> Option<&'a Food> {
    if cravings.is_empty() {
        return None;
    }

    let stomach = manager.stomach_food_map();
    let craving_set: std::collections::HashSet<String> =
        cravings.iter().map(|c| c.to_lowercase()).collect();

    let available = manager.all_available();

    available
        .into_iter()
        .filter(|f| craving_set.contains(&f.name.to_lowercase()))
        .max_by(|a, b| {
            let delta_a = get_sp_delta(&stomach, a, cravings, config);
            let delta_b = get_sp_delta(&stomach, b, cravings, config);
            delta_a
                .partial_cmp(&delta_b)
                .unwrap_or(std::cmp::Ordering::Equal)
        })
}

/// Generate a meal plan.
///
/// Iteratively selects the best bite until calories are exhausted.
pub fn generate_plan(
    manager: &mut FoodStateManager,
    cravings: &[String],
    config: &SpConfig,
    remaining_calories: f64,
) -> Vec<MealPlanItem> {
    let mut plan = Vec::new();
    let mut remaining = remaining_calories;

    for _ in 0..MAX_ITERATIONS {
        if remaining <= 0.0 {
            break;
        }

        // Check if any food is available
        if manager.all_available().is_empty() {
            break;
        }

        // Calculate current state
        let stomach_before = manager.stomach_food_map();
        let state_before = calculate_state_snapshot(&stomach_before, cravings, config);

        // Try to pick a craving first, otherwise best bite
        let selected = pick_feasible_craving(manager, cravings, config)
            .or_else(|| choose_next_bite(manager, cravings, config));

        let food = match selected {
            Some(f) => f,
            None => break,
        };

        // Check if food fits in remaining calories (allow first bite even if over budget)
        let exceeds_budget = food.calories > remaining;
        let is_first_bite = plan.is_empty();
        if exceeds_budget && !is_first_bite {
            break;
        }

        let food_name = food.name.clone();
        let food_calories = food.calories;

        // Check if this satisfies a craving
        let is_craving = is_craving_match(&food_name, cravings);

        // Consume the food
        let _ = manager.consume_food(&food_name);

        // Calculate new state
        let stomach_after = manager.stomach_food_map();
        let state_after = calculate_state_snapshot(&stomach_after, cravings, config);

        // Calculate deltas (e.g., 1.2 -> 1.3 shows as +0.1)
        let sp_gain = state_after.sp - state_before.sp;
        let variety_delta = state_after.variety_mult - state_before.variety_mult;
        let taste_delta = state_after.taste_mult - state_before.taste_mult;

        plan.push(MealPlanItem::new(
            food_name,
            food_calories,
            sp_gain,
            state_after.sp,
            is_craving,
            variety_delta,
            taste_delta,
        ));

        remaining -= food_calories;
    }

    plan
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
    fn test_low_calorie_penalty() {
        // Above CAL_FLOOR = no penalty
        assert_eq!(low_calorie_penalty(500.0), 0.0);
        assert_eq!(low_calorie_penalty(CAL_FLOOR + 1.0), 0.0);
        // Below CAL_FLOOR = penalty
        assert!(low_calorie_penalty(100.0) < 0.0);
        assert!(low_calorie_penalty(CAL_FLOOR - 1.0) < 0.0);
    }

    #[test]
    fn test_choose_next_bite() {
        let manager = FoodStateManager::new(sample_foods());
        let config = SpConfig::default();
        let selected = choose_next_bite(&manager, &[], &config);
        assert!(selected.is_some());
    }

    #[test]
    fn test_pick_feasible_craving() {
        let manager = FoodStateManager::new(sample_foods());
        let cravings = vec!["Apple".to_string()];
        let config = SpConfig::default();

        let selected = pick_feasible_craving(&manager, &cravings, &config);
        assert!(selected.is_some());
        assert_eq!(selected.unwrap().name.to_lowercase(), "apple");
    }

    #[test]
    fn test_generate_plan() {
        let mut manager = FoodStateManager::new(sample_foods());
        let config = SpConfig::default();
        let plan = generate_plan(&mut manager, &[], &config, 1000.0);

        assert!(!plan.is_empty());
        let total_cal: f64 = plan.iter().map(|p| p.calories).sum();
        assert!(total_cal <= 1000.0 || plan.len() == 1);
    }
}
