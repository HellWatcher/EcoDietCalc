use std::collections::HashMap;

use crate::models::{Food, MealPlanItem};
use crate::planner::calculations::{
    calculate_sp, calculate_taste_bonus, calculate_variety_bonus, count_variety_qualifying,
    get_sp_delta, sum_all_weighted_nutrients,
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
/// Bias based on change in soft-variety bonus.
fn soft_variety_bias(stomach: &HashMap<&Food, u32>, food: &Food) -> f64 {
    let count_before = count_variety_qualifying(stomach);
    let bonus_before = calculate_variety_bonus(count_before);

    // Simulate adding the food
    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let count_after = count_variety_qualifying(&new_stomach);
    let bonus_after = calculate_variety_bonus(count_after);

    let delta_pp = bonus_after - bonus_before;

    // Get nutrient sum after adding food
    let (density, _) = sum_all_weighted_nutrients(&new_stomach);
    let ns_after = density.sum();

    SOFT_BIAS_GAMMA * ns_after * (delta_pp / 100.0)
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
    cravings_satisfied: u32,
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
            let sp_delta = get_sp_delta(&stomach, food, cravings, cravings_satisfied);
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
    cravings_satisfied: u32,
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
            let delta_a = get_sp_delta(&stomach, a, cravings, cravings_satisfied);
            let delta_b = get_sp_delta(&stomach, b, cravings, cravings_satisfied);
            delta_a.partial_cmp(&delta_b).unwrap_or(std::cmp::Ordering::Equal)
        })
}

/// Generate a meal plan.
///
/// Iteratively selects the best bite until calories are exhausted.
pub fn generate_plan(
    manager: &mut FoodStateManager,
    cravings: &[String],
    mut cravings_satisfied: u32,
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
        let variety_before = calculate_variety_bonus(count_variety_qualifying(&stomach_before));
        let taste_before = calculate_taste_bonus(&stomach_before);
        let sp_before = calculate_sp(&stomach_before, cravings, cravings_satisfied);

        // Try to pick a craving first, otherwise best bite
        let selected = pick_feasible_craving(manager, cravings, cravings_satisfied)
            .or_else(|| choose_next_bite(manager, cravings, cravings_satisfied));

        let food = match selected {
            Some(f) => f,
            None => break,
        };

        // Check if food fits in remaining calories
        if food.calories > remaining && plan.is_empty() {
            // Allow first bite even if over budget
        } else if food.calories > remaining {
            break;
        }

        let food_name = food.name.clone();
        let food_calories = food.calories;

        // Check if this satisfies a craving
        let is_craving = cravings
            .iter()
            .any(|c| c.to_lowercase() == food_name.to_lowercase());

        // Consume the food
        let _ = manager.consume_food(&food_name);

        // Update craving satisfaction
        if is_craving {
            cravings_satisfied += 1;
        }

        // Calculate new state
        let stomach_after = manager.stomach_food_map();
        let variety_after = calculate_variety_bonus(count_variety_qualifying(&stomach_after));
        let taste_after = calculate_taste_bonus(&stomach_after);
        let sp_after = calculate_sp(&stomach_after, cravings, cravings_satisfied);

        let sp_gain = sp_after - sp_before;
        let variety_delta = variety_after - variety_before;
        let taste_delta = taste_after - taste_before;

        plan.push(MealPlanItem::new(
            food_name,
            food_calories,
            sp_gain,
            sp_after,
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
        assert_eq!(low_calorie_penalty(500.0), 0.0);
        assert_eq!(low_calorie_penalty(420.0), 0.0);
        assert!(low_calorie_penalty(100.0) < 0.0);
    }

    #[test]
    fn test_choose_next_bite() {
        let manager = FoodStateManager::new(sample_foods());
        let selected = choose_next_bite(&manager, &[], 0);
        assert!(selected.is_some());
    }

    #[test]
    fn test_pick_feasible_craving() {
        let manager = FoodStateManager::new(sample_foods());
        let cravings = vec!["Apple".to_string()];

        let selected = pick_feasible_craving(&manager, &cravings, 0);
        assert!(selected.is_some());
        assert_eq!(selected.unwrap().name.to_lowercase(), "apple");
    }

    #[test]
    fn test_generate_plan() {
        let mut manager = FoodStateManager::new(sample_foods());
        let plan = generate_plan(&mut manager, &[], 0, 1000.0);

        assert!(!plan.is_empty());
        let total_cal: f64 = plan.iter().map(|p| p.calories).sum();
        assert!(total_cal <= 1000.0 || plan.len() == 1);
    }
}
