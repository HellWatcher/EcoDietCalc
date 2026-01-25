use serde::{Deserialize, Serialize};

/// A food item with nutritional data and state.
///
/// Tastiness uses a scale of -3 to +3, with 99 as the "unknown" sentinel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Food {
    #[serde(rename = "Name")]
    pub name: String,

    #[serde(rename = "Calories")]
    pub calories: f64,

    #[serde(rename = "Carbs")]
    pub carbs: f64,

    #[serde(rename = "Protein")]
    pub protein: f64,

    #[serde(rename = "Fats")]
    pub fats: f64,

    #[serde(rename = "Vitamins")]
    pub vitamins: f64,

    #[serde(rename = "Tastiness")]
    pub tastiness: i8,

    #[serde(rename = "Stomach", default)]
    pub stomach: u32,

    #[serde(rename = "Available", default)]
    pub available: u32,
}

impl Food {
    /// Sum of all nutrients (carbs + protein + fats + vitamins).
    #[inline]
    pub fn sum_nutrients(&self) -> f64 {
        self.carbs + self.protein + self.fats + self.vitamins
    }

    /// Nutrient density: nutrients per calorie.
    #[inline]
    pub fn density(&self) -> f64 {
        if self.calories > 0.0 {
            self.sum_nutrients() / self.calories
        } else {
            0.0
        }
    }

    /// Calories per unit of total nutrients.
    #[inline]
    pub fn calories_per_nutrient(&self) -> f64 {
        let nutrients = self.sum_nutrients();
        if nutrients > 0.0 {
            self.calories / nutrients
        } else {
            0.0
        }
    }

    /// Basic validation: non-negative values and valid tastiness.
    pub fn is_valid(&self) -> bool {
        self.calories >= 0.0
            && self.carbs >= 0.0
            && self.protein >= 0.0
            && self.fats >= 0.0
            && self.vitamins >= 0.0
            && ((-3..=3).contains(&self.tastiness) || self.tastiness == 99)
    }

    /// Debug string for logging.
    pub fn debug_string(&self) -> String {
        format!(
            "{}: {} cal, C:{} P:{} F:{} V:{}, taste:{}",
            self.name,
            self.calories,
            self.carbs,
            self.protein,
            self.fats,
            self.vitamins,
            self.tastiness
        )
    }

    /// Canonical key for lookups (lowercase name).
    pub fn key(&self) -> String {
        self.name.to_lowercase()
    }
}

impl PartialEq for Food {
    fn eq(&self, other: &Self) -> bool {
        self.name.to_lowercase() == other.name.to_lowercase()
    }
}

impl Eq for Food {}

impl std::hash::Hash for Food {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.name.to_lowercase().hash(state);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_food() -> Food {
        Food {
            name: "Apple".to_string(),
            calories: 100.0,
            carbs: 20.0,
            protein: 1.0,
            fats: 0.5,
            vitamins: 5.0,
            tastiness: 2,
            stomach: 0,
            available: 5,
        }
    }

    #[test]
    fn test_sum_nutrients() {
        let food = sample_food();
        assert!((food.sum_nutrients() - 26.5).abs() < 0.001);
    }

    #[test]
    fn test_density() {
        let food = sample_food();
        assert!((food.density() - 0.265).abs() < 0.001);
    }

    #[test]
    fn test_is_valid() {
        let food = sample_food();
        assert!(food.is_valid());

        let mut invalid = sample_food();
        invalid.tastiness = 5;
        assert!(!invalid.is_valid());
    }

    #[test]
    fn test_equality_case_insensitive() {
        let food1 = sample_food();
        let mut food2 = sample_food();
        food2.name = "APPLE".to_string();
        assert_eq!(food1, food2);
    }
}
