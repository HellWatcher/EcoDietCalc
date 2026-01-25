use std::collections::HashMap;

use crate::models::Food;
use crate::planner::constants::*;

/// Nutrient density breakdown.
#[derive(Debug, Clone, Default)]
pub struct NutrientDensity {
    pub carbs: f64,
    pub protein: f64,
    pub fats: f64,
    pub vitamins: f64,
}

impl NutrientDensity {
    /// Sum of all nutrient densities.
    pub fn sum(&self) -> f64 {
        self.carbs + self.protein + self.fats + self.vitamins
    }

    /// Minimum non-zero nutrient value.
    pub fn min_nonzero(&self) -> f64 {
        [self.carbs, self.protein, self.fats, self.vitamins]
            .into_iter()
            .filter(|&v| v > 0.0)
            .fold(f64::MAX, f64::min)
    }

    /// Maximum nutrient value.
    pub fn max(&self) -> f64 {
        [self.carbs, self.protein, self.fats, self.vitamins]
            .into_iter()
            .fold(0.0, f64::max)
    }
}

/// Calculate calorie-weighted nutrient density from stomach contents.
///
/// Returns (density, total_calories).
pub fn sum_all_weighted_nutrients(stomach: &HashMap<&Food, u32>) -> (NutrientDensity, f64) {
    let total_cal: f64 = stomach
        .iter()
        .map(|(f, qty)| f.calories * (*qty) as f64)
        .sum();

    if total_cal == 0.0 {
        return (NutrientDensity::default(), 0.0);
    }

    let mut density = NutrientDensity::default();
    for (food, qty) in stomach {
        let weight = (food.calories * (*qty) as f64) / total_cal;
        density.carbs += food.carbs * weight;
        density.protein += food.protein * weight;
        density.fats += food.fats * weight;
        density.vitamins += food.vitamins * weight;
    }

    (density, total_cal)
}

/// Calculate balance bonus (percentage points).
///
/// Range: -50 to +50 pp.
/// Penalizes imbalanced nutrition; peaks at perfect 1:1:1:1 ratio.
pub fn calculate_balance_bonus(density: &NutrientDensity) -> f64 {
    let max_val = density.max();
    if max_val == 0.0 {
        return 0.0;
    }

    let min_val = density.min_nonzero();
    if min_val == f64::MAX {
        return 0.0;
    }

    let balance_ratio = min_val / max_val;
    (balance_ratio * 100.0) - 50.0
}

/// Calculate variety bonus (percentage points).
///
/// Uses exponential cap: each +20 qualifying foods halves remaining gap.
/// Max: VARIETY_BONUS_CAP_PP (55 pp).
pub fn calculate_variety_bonus(variety_count: usize) -> f64 {
    // variety_bonus(count) = VARIETY_BONUS_CAP_PP * (1 - 0.5^(count/20))
    VARIETY_BONUS_CAP_PP * (1.0 - 0.5_f64.powf(variety_count as f64 / 20.0))
}

/// Calculate taste bonus (percentage points).
///
/// Range: approximately -30 to +30 pp.
pub fn calculate_taste_bonus(stomach: &HashMap<&Food, u32>) -> f64 {
    let total_cal: f64 = stomach
        .iter()
        .map(|(f, qty)| f.calories * (*qty) as f64)
        .sum();

    if total_cal == 0.0 {
        return 0.0;
    }

    let weighted_taste: f64 = stomach
        .iter()
        .map(|(food, qty)| {
            let cal = food.calories * (*qty) as f64;
            let mult = tastiness_multiplier(food.tastiness);
            cal * mult
        })
        .sum();

    (weighted_taste / total_cal) * 100.0 * TASTE_WEIGHT
}

/// Count foods that qualify for variety bonus.
pub fn count_variety_qualifying(stomach: &HashMap<&Food, u32>) -> usize {
    stomach
        .iter()
        .filter(|(food, qty)| is_variety_qualifying(food.calories, **qty))
        .count()
}

/// Check if a food qualifies for variety bonus.
pub fn is_variety_qualifying(calories_per_unit: f64, quantity: u32) -> bool {
    (calories_per_unit * quantity as f64) >= VARIETY_CAL_THRESHOLD
}

/// Calculate craving bonus in percentage points.
///
/// Returns CRAVING_BONUS_PP for each food in stomach that matches a craving.
pub fn calculate_craving_bonus(stomach: &HashMap<&Food, u32>, cravings: &[String]) -> f64 {
    let craving_set: std::collections::HashSet<String> =
        cravings.iter().map(|c| c.to_lowercase()).collect();

    let matches = stomach
        .keys()
        .filter(|f| craving_set.contains(&f.name.to_lowercase()))
        .count();

    matches as f64 * CRAVING_BONUS_PP
}

/// Calculate total SP from stomach contents and craving state.
///
/// SP = density_sum * (1.0 + bonus/100) + BASE_SKILL_POINTS + (cravings_satisfied * CRAVING_SATISFIED_FRAC)
pub fn calculate_sp(
    stomach: &HashMap<&Food, u32>,
    cravings: &[String],
    cravings_satisfied: u32,
) -> f64 {
    let (density, _total_cal) = sum_all_weighted_nutrients(stomach);
    let density_sum = density.sum();

    let balance_bonus = calculate_balance_bonus(&density);
    let variety_count = count_variety_qualifying(stomach);
    let variety_bonus = calculate_variety_bonus(variety_count);
    let taste_bonus = calculate_taste_bonus(stomach);
    let craving_bonus = calculate_craving_bonus(stomach, cravings);

    let total_bonus = balance_bonus + variety_bonus + taste_bonus + craving_bonus;

    density_sum * (1.0 + total_bonus / 100.0)
        + BASE_SKILL_POINTS
        + (cravings_satisfied as f64 * CRAVING_SATISFIED_FRAC)
}

/// Calculate the SP delta from adding one unit of a food.
pub fn get_sp_delta(
    stomach: &HashMap<&Food, u32>,
    food: &Food,
    cravings: &[String],
    cravings_satisfied: u32,
) -> f64 {
    let sp_before = calculate_sp(stomach, cravings, cravings_satisfied);

    // Create new stomach with food added
    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let sp_after = calculate_sp(&new_stomach, cravings, cravings_satisfied);

    sp_after - sp_before
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_food(name: &str, cal: f64, c: f64, p: f64, f: f64, v: f64, taste: i8) -> Food {
        Food {
            name: name.to_string(),
            calories: cal,
            carbs: c,
            protein: p,
            fats: f,
            vitamins: v,
            tastiness: taste,
            stomach: 0,
            available: 10,
        }
    }

    #[test]
    fn test_balance_bonus_perfect() {
        // Perfect balance: all nutrients equal
        let density = NutrientDensity {
            carbs: 10.0,
            protein: 10.0,
            fats: 10.0,
            vitamins: 10.0,
        };
        let bonus = calculate_balance_bonus(&density);
        assert!((bonus - 50.0).abs() < 0.01); // 100% balance -> +50 pp
    }

    #[test]
    fn test_balance_bonus_imbalanced() {
        // Very imbalanced: one nutrient dominates
        let density = NutrientDensity {
            carbs: 100.0,
            protein: 10.0,
            fats: 10.0,
            vitamins: 10.0,
        };
        let bonus = calculate_balance_bonus(&density);
        assert!((bonus - (-40.0)).abs() < 0.01); // 10/100 = 0.1 -> -40 pp
    }

    #[test]
    fn test_variety_bonus() {
        assert!((calculate_variety_bonus(0) - 0.0).abs() < 0.01);
        assert!((calculate_variety_bonus(20) - 27.5).abs() < 0.1); // Half of cap
        assert!(calculate_variety_bonus(100) < VARIETY_BONUS_CAP_PP); // Approaches but never exceeds cap
    }

    #[test]
    fn test_taste_bonus() {
        let food1 = sample_food("Good", 100.0, 10.0, 10.0, 10.0, 10.0, 3); // favorite
        let food2 = sample_food("Bad", 100.0, 10.0, 10.0, 10.0, 10.0, -3); // hated

        let mut stomach: HashMap<&Food, u32> = HashMap::new();
        stomach.insert(&food1, 1);
        let bonus = calculate_taste_bonus(&stomach);
        assert!((bonus - 30.0).abs() < 0.01); // +3 taste = +30%

        let mut stomach2: HashMap<&Food, u32> = HashMap::new();
        stomach2.insert(&food2, 1);
        let bonus2 = calculate_taste_bonus(&stomach2);
        assert!((bonus2 - (-30.0)).abs() < 0.01); // -3 taste = -30%
    }

    #[test]
    fn test_is_variety_qualifying() {
        assert!(is_variety_qualifying(500.0, 4)); // 2000 cal
        assert!(!is_variety_qualifying(500.0, 3)); // 1500 cal
        assert!(is_variety_qualifying(2000.0, 1)); // Exactly 2000
    }

    #[test]
    fn test_calculate_sp_empty_stomach() {
        let stomach: HashMap<&Food, u32> = HashMap::new();
        let sp = calculate_sp(&stomach, &[], 0);
        assert!((sp - BASE_SKILL_POINTS).abs() < 0.01);
    }

    #[test]
    fn test_sp_delta() {
        let food = sample_food("Balanced", 500.0, 10.0, 10.0, 10.0, 10.0, 2);
        let stomach: HashMap<&Food, u32> = HashMap::new();

        let delta = get_sp_delta(&stomach, &food, &[], 0);
        assert!(delta > 0.0); // Adding food should increase SP
    }
}
