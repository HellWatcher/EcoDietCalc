use std::collections::HashMap;

use crate::error::{EcoError, Result};
use crate::models::Food;
use crate::planner::calculations;

/// Manages the state of foods, stomach contents, and availability.
pub struct FoodStateManager {
    /// All foods keyed by lowercase name.
    foods: HashMap<String, Food>,
}

impl FoodStateManager {
    /// Create a new state manager from a list of foods.
    pub fn new(foods: Vec<Food>) -> Self {
        let mut map = HashMap::new();
        for food in foods {
            map.insert(food.key(), food);
        }
        Self { foods: map }
    }

    /// Get a food by name (case-insensitive).
    pub fn get_food(&self, name: &str) -> Option<&Food> {
        self.foods.get(&name.to_lowercase())
    }

    /// Get a mutable reference to a food by name (case-insensitive).
    pub fn get_food_mut(&mut self, name: &str) -> Option<&mut Food> {
        self.foods.get_mut(&name.to_lowercase())
    }

    /// Check if a food can be consumed (has available stock).
    pub fn can_consume(&self, name: &str) -> bool {
        self.get_food(name)
            .map(|f| f.available > 0)
            .unwrap_or(false)
    }

    /// Consume one unit of food: increment stomach, decrement available.
    pub fn consume_food(&mut self, name: &str) -> Result<()> {
        let food = self
            .get_food_mut(name)
            .ok_or_else(|| EcoError::FoodNotFound(name.to_string()))?;

        if food.available == 0 {
            return Err(EcoError::InvalidInput(format!(
                "{} has no available units",
                name
            )));
        }

        food.stomach += 1;
        food.available -= 1;
        Ok(())
    }

    /// Get all foods with positive stomach count.
    pub fn stomach_contents(&self) -> HashMap<String, u32> {
        self.foods
            .iter()
            .filter(|(_, f)| f.stomach > 0)
            .map(|(k, f)| (k.clone(), f.stomach))
            .collect()
    }

    /// Get the current stomach as a map of Food references to quantity.
    pub fn stomach_food_map(&self) -> HashMap<&Food, u32> {
        self.foods
            .values()
            .filter(|f| f.stomach > 0)
            .map(|f| (f, f.stomach))
            .collect()
    }

    /// Get foods that qualify for the variety bonus.
    pub fn unique_variety_foods(&self) -> Vec<&Food> {
        self.foods
            .values()
            .filter(|f| calculations::is_variety_qualifying(f.calories, f.stomach))
            .collect()
    }

    /// Get all foods with available units.
    pub fn all_available(&self) -> Vec<&Food> {
        self.foods.values().filter(|f| f.available > 0).collect()
    }

    /// Get all foods.
    pub fn all_foods(&self) -> Vec<&Food> {
        self.foods.values().collect()
    }

    /// Get all foods mutably.
    pub fn all_foods_mut(&mut self) -> impl Iterator<Item = &mut Food> {
        self.foods.values_mut()
    }

    /// Reset stomach counts for all foods.
    pub fn reset_stomach(&mut self) {
        for food in self.foods.values_mut() {
            food.stomach = 0;
        }
    }

    /// Reset availability for all foods to a fixed value.
    pub fn reset_availability(&mut self, new_available: u32) {
        for food in self.foods.values_mut() {
            food.available = new_available;
        }
    }

    /// Reset tastiness for all foods.
    ///
    /// If `to_unknown` is true, sets to 99 (unknown); otherwise sets to 0 (neutral).
    pub fn reset_tastiness(&mut self, to_unknown: bool) {
        let value = if to_unknown { 99 } else { 0 };
        for food in self.foods.values_mut() {
            food.tastiness = value;
        }
    }

    /// Compute current SP given cravings state.
    pub fn get_current_sp(&self, cravings: &[String], cravings_satisfied: u32) -> f64 {
        let stomach_map = self.stomach_food_map();
        calculations::calculate_sp(&stomach_map, cravings, cravings_satisfied)
    }

    /// Convert state to a list of foods for JSON serialization.
    pub fn to_foods(&self) -> Vec<Food> {
        self.foods.values().cloned().collect()
    }

    /// Total calories in stomach.
    pub fn total_stomach_calories(&self) -> f64 {
        self.foods
            .values()
            .map(|f| f.calories * f.stomach as f64)
            .sum()
    }

    /// Count of foods in the manager.
    pub fn len(&self) -> usize {
        self.foods.len()
    }

    /// Check if manager has no foods.
    pub fn is_empty(&self) -> bool {
        self.foods.is_empty()
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
                available: 5,
            },
            Food {
                name: "Bread".to_string(),
                calories: 200.0,
                carbs: 40.0,
                protein: 8.0,
                fats: 2.0,
                vitamins: 1.0,
                tastiness: 1,
                stomach: 2,
                available: 10,
            },
        ]
    }

    #[test]
    fn test_get_food_case_insensitive() {
        let manager = FoodStateManager::new(sample_foods());
        assert!(manager.get_food("apple").is_some());
        assert!(manager.get_food("APPLE").is_some());
        assert!(manager.get_food("Apple").is_some());
        assert!(manager.get_food("banana").is_none());
    }

    #[test]
    fn test_consume_food() {
        let mut manager = FoodStateManager::new(sample_foods());

        assert!(manager.can_consume("apple"));
        manager.consume_food("apple").unwrap();

        let apple = manager.get_food("apple").unwrap();
        assert_eq!(apple.stomach, 1);
        assert_eq!(apple.available, 4);
    }

    #[test]
    fn test_reset_stomach() {
        let mut manager = FoodStateManager::new(sample_foods());
        assert_eq!(manager.get_food("bread").unwrap().stomach, 2);

        manager.reset_stomach();
        assert_eq!(manager.get_food("bread").unwrap().stomach, 0);
    }

    #[test]
    fn test_all_available() {
        let manager = FoodStateManager::new(sample_foods());
        let available = manager.all_available();
        assert_eq!(available.len(), 2);
    }
}
