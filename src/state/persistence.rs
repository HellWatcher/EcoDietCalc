use std::collections::HashMap;
use std::fs;
use std::path::Path;

use crate::error::Result;
use crate::models::Food;

/// Load foods from a JSON file.
///
/// Deduplicates by lowercase name (last occurrence wins).
pub fn load_foods<P: AsRef<Path>>(path: P) -> Result<Vec<Food>> {
    let content = fs::read_to_string(path)?;
    let foods: Vec<Food> = serde_json::from_str(&content)?;

    // Deduplicate by lowercase name, keeping last occurrence
    let mut seen: HashMap<String, Food> = HashMap::new();
    for food in foods {
        seen.insert(food.key(), food);
    }

    Ok(seen.into_values().collect())
}

/// Save foods to a JSON file.
///
/// Deduplicates by lowercase name before saving.
pub fn save_foods<P: AsRef<Path>>(path: P, foods: &[Food]) -> Result<()> {
    // Deduplicate by lowercase name
    let mut seen: HashMap<String, &Food> = HashMap::new();
    for food in foods {
        seen.insert(food.key(), food);
    }

    let deduped: Vec<&Food> = seen.into_values().collect();
    let json = serde_json::to_string_pretty(&deduped)?;
    fs::write(path, json)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_load_and_save_roundtrip() {
        let json = r#"[
            {"Name": "Apple", "Calories": 100, "Carbs": 20, "Protein": 1, "Fats": 0, "Vitamins": 5, "Tastiness": 2, "Stomach": 0, "Available": 5}
        ]"#;

        let mut file = NamedTempFile::new().unwrap();
        file.write_all(json.as_bytes()).unwrap();

        let foods = load_foods(file.path()).unwrap();
        assert_eq!(foods.len(), 1);
        assert_eq!(foods[0].name, "Apple");

        // Save and reload
        let out_file = NamedTempFile::new().unwrap();
        save_foods(out_file.path(), &foods).unwrap();

        let reloaded = load_foods(out_file.path()).unwrap();
        assert_eq!(reloaded.len(), 1);
        assert_eq!(reloaded[0].name, "Apple");
    }

    #[test]
    fn test_deduplication() {
        let json = r#"[
            {"Name": "Apple", "Calories": 100, "Carbs": 20, "Protein": 1, "Fats": 0, "Vitamins": 5, "Tastiness": 1, "Stomach": 0, "Available": 5},
            {"Name": "apple", "Calories": 100, "Carbs": 20, "Protein": 1, "Fats": 0, "Vitamins": 5, "Tastiness": 3, "Stomach": 0, "Available": 10}
        ]"#;

        let mut file = NamedTempFile::new().unwrap();
        file.write_all(json.as_bytes()).unwrap();

        let foods = load_foods(file.path()).unwrap();
        assert_eq!(foods.len(), 1);
        // Last occurrence wins
        assert_eq!(foods[0].tastiness, 3);
        assert_eq!(foods[0].available, 10);
    }
}
