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

/// Calculate balance multiplier.
///
/// Range: 0.5 (worst balance) to 2.0 (perfect 1:1:1:1 ratio).
pub fn calculate_balance_mult(density: &NutrientDensity) -> f64 {
    let max_val = density.max();
    if max_val == 0.0 {
        return 1.0; // No food = neutral
    }

    let min_val = density.min_nonzero();
    if min_val == f64::MAX {
        return BALANCE_MULT_MIN; // Missing nutrients = worst
    }

    let balance_ratio = min_val / max_val; // 0.0 to 1.0
                                           // Map ratio to multiplier range: 0 -> 0.5, 1 -> 2.0
    BALANCE_MULT_MIN + balance_ratio * (BALANCE_MULT_MAX - BALANCE_MULT_MIN)
}

/// Calculate variety multiplier.
///
/// Uses exponential approach: each +20 qualifying foods halves remaining gap.
/// Range: 1.0 (no variety) to VARIETY_MULT_MAX (1.55).
pub fn calculate_variety_mult(variety_count: usize) -> f64 {
    // variety_mult(count) = 1.0 + (VARIETY_MULT_MAX - 1.0) * (1 - 0.5^(count/20))
    let bonus_range = VARIETY_MULT_MAX - 1.0;
    1.0 + bonus_range * (1.0 - 0.5_f64.powf(variety_count as f64 / 20.0))
}

/// Calculate taste multiplier.
///
/// Calorie-weighted average of individual food taste multipliers.
/// Range: 0.7 (all hated) to 1.3 (all favorite).
pub fn calculate_taste_mult(stomach: &HashMap<&Food, u32>) -> f64 {
    let total_cal: f64 = stomach
        .iter()
        .map(|(f, qty)| f.calories * (*qty) as f64)
        .sum();

    if total_cal == 0.0 {
        return 1.0; // No food = neutral
    }

    let weighted_taste: f64 = stomach
        .iter()
        .map(|(food, qty)| {
            let cal = food.calories * (*qty) as f64;
            let mult = tastiness_multiplier(food.tastiness);
            cal * mult
        })
        .sum();

    weighted_taste / total_cal
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

/// Calculate craving multiplier.
///
/// Returns 1.0 + (CRAVING_MULT_PER_MATCH * matches) for foods matching cravings.
pub fn calculate_craving_mult(stomach: &HashMap<&Food, u32>, cravings: &[String]) -> f64 {
    let craving_set: std::collections::HashSet<String> =
        cravings.iter().map(|c| c.to_lowercase()).collect();

    let matches = stomach
        .keys()
        .filter(|f| craving_set.contains(&f.name.to_lowercase()))
        .count();

    1.0 + matches as f64 * CRAVING_MULT_PER_MATCH
}

/// Configurable multipliers for SP calculation.
#[derive(Debug, Clone)]
pub struct SpConfig {
    pub server_mult: f64,
    pub dinner_party_mult: f64,
}

impl Default for SpConfig {
    fn default() -> Self {
        Self {
            server_mult: DEFAULT_SERVER_MULT,
            dinner_party_mult: DEFAULT_DINNER_PARTY_MULT,
        }
    }
}

/// Calculate total SP from stomach contents and craving state.
///
/// Formula: (nutrient_total * balance * variety * taste * craving * dinner_party + base) * server
pub fn calculate_sp(stomach: &HashMap<&Food, u32>, cravings: &[String], config: &SpConfig) -> f64 {
    let (density, _total_cal) = sum_all_weighted_nutrients(stomach);
    let density_sum = density.sum();

    let balance_mult = calculate_balance_mult(&density);
    let variety_count = count_variety_qualifying(stomach);
    let variety_mult = calculate_variety_mult(variety_count);
    let taste_mult = calculate_taste_mult(stomach);
    let craving_mult = calculate_craving_mult(stomach, cravings);

    // Chain multipliers
    let nutrition_sp = density_sum
        * balance_mult
        * variety_mult
        * taste_mult
        * craving_mult
        * config.dinner_party_mult;

    (nutrition_sp + BASE_SKILL_POINTS) * config.server_mult
}

/// Calculate the SP delta from adding one unit of a food.
pub fn get_sp_delta(
    stomach: &HashMap<&Food, u32>,
    food: &Food,
    cravings: &[String],
    config: &SpConfig,
) -> f64 {
    let sp_before = calculate_sp(stomach, cravings, config);

    // Create new stomach with food added
    let mut new_stomach = stomach.clone();
    let current = new_stomach.get(&food).copied().unwrap_or(0);
    new_stomach.insert(food, current + 1);

    let sp_after = calculate_sp(&new_stomach, cravings, config);

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
    fn test_balance_mult_perfect() {
        // Perfect balance: all nutrients equal -> 2.0x
        let density = NutrientDensity {
            carbs: 10.0,
            protein: 10.0,
            fats: 10.0,
            vitamins: 10.0,
        };
        let mult = calculate_balance_mult(&density);
        assert!((mult - BALANCE_MULT_MAX).abs() < 0.01);
    }

    #[test]
    fn test_balance_mult_imbalanced() {
        // Very imbalanced: ratio = 0.1 -> 0.5 + 0.1 * 1.5 = 0.65
        let density = NutrientDensity {
            carbs: 100.0,
            protein: 10.0,
            fats: 10.0,
            vitamins: 10.0,
        };
        let mult = calculate_balance_mult(&density);
        let expected = BALANCE_MULT_MIN + 0.1 * (BALANCE_MULT_MAX - BALANCE_MULT_MIN);
        assert!((mult - expected).abs() < 0.01);
    }

    #[test]
    fn test_variety_mult() {
        assert!((calculate_variety_mult(0) - 1.0).abs() < 0.01); // No variety = 1.0x
                                                                 // 20 foods = halfway to max
        let half_bonus = 1.0 + (VARIETY_MULT_MAX - 1.0) * 0.5;
        assert!((calculate_variety_mult(20) - half_bonus).abs() < 0.01);
        assert!(calculate_variety_mult(100) < VARIETY_MULT_MAX); // Approaches but never exceeds
    }

    #[test]
    fn test_taste_mult() {
        let food1 = sample_food("Good", 100.0, 10.0, 10.0, 10.0, 10.0, 3); // favorite
        let food2 = sample_food("Bad", 100.0, 10.0, 10.0, 10.0, 10.0, -3); // hated

        let mut stomach: HashMap<&Food, u32> = HashMap::new();
        stomach.insert(&food1, 1);
        let mult = calculate_taste_mult(&stomach);
        assert!((mult - 1.3).abs() < 0.01); // +3 taste = 1.3x

        let mut stomach2: HashMap<&Food, u32> = HashMap::new();
        stomach2.insert(&food2, 1);
        let mult2 = calculate_taste_mult(&stomach2);
        assert!((mult2 - 0.7).abs() < 0.01); // -3 taste = 0.7x
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
        let config = SpConfig::default();
        let sp = calculate_sp(&stomach, &[], &config);
        assert!((sp - BASE_SKILL_POINTS).abs() < 0.01);
    }

    #[test]
    fn test_sp_delta() {
        let food = sample_food("Balanced", 500.0, 10.0, 10.0, 10.0, 10.0, 2);
        let stomach: HashMap<&Food, u32> = HashMap::new();
        let config = SpConfig::default();

        let delta = get_sp_delta(&stomach, &food, &[], &config);
        assert!(delta > 0.0); // Adding food should increase SP
    }

    #[test]
    fn test_craving_mult() {
        let food = sample_food("Pizza", 500.0, 10.0, 10.0, 10.0, 10.0, 2);
        let mut stomach: HashMap<&Food, u32> = HashMap::new();
        stomach.insert(&food, 1);

        // No craving = 1.0x
        let mult_none = calculate_craving_mult(&stomach, &[]);
        assert!((mult_none - 1.0).abs() < 0.01);

        // Matching craving = 1.0 + CRAVING_MULT_PER_MATCH
        let mult_match = calculate_craving_mult(&stomach, &["Pizza".to_string()]);
        assert!((mult_match - (1.0 + CRAVING_MULT_PER_MATCH)).abs() < 0.01);
    }

    #[test]
    fn test_server_mult_affects_sp() {
        let food = sample_food("Test", 500.0, 10.0, 10.0, 10.0, 10.0, 0);
        let mut stomach: HashMap<&Food, u32> = HashMap::new();
        stomach.insert(&food, 1);

        let config_1x = SpConfig::default();
        let config_2x = SpConfig {
            server_mult: 2.0,
            ..Default::default()
        };

        let sp_1x = calculate_sp(&stomach, &[], &config_1x);
        let sp_2x = calculate_sp(&stomach, &[], &config_2x);

        assert!((sp_2x / sp_1x - 2.0).abs() < 0.01);
    }
}
