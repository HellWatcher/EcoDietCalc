use std::collections::HashMap;

use eco_diet_maker_rs::models::Food;
use eco_diet_maker_rs::planner::{
    calculate_sp, calculate_variety_mult, is_variety_qualifying, SpConfig, BASE_SKILL_POINTS,
    VARIETY_CAL_THRESHOLD, VARIETY_MULT_MAX,
};

fn make_food(name: &str, cal: f64, c: f64, p: f64, f: f64, v: f64, taste: i8) -> Food {
    Food {
        name: name.to_string(),
        calories: cal,
        carbs: c,
        protein: p,
        fats: f,
        vitamins: v,
        tastiness: taste,
        stomach: 0,
        available: 100,
    }
}

#[test]
fn test_variety_qualification_threshold() {
    // Exactly at threshold
    assert!(is_variety_qualifying(VARIETY_CAL_THRESHOLD, 1));
    assert!(is_variety_qualifying(1000.0, 2));

    // Below threshold
    assert!(!is_variety_qualifying(1999.0, 1));
    assert!(!is_variety_qualifying(500.0, 3));

    // Above threshold
    assert!(is_variety_qualifying(2001.0, 1));
    assert!(is_variety_qualifying(1000.0, 3));
}

#[test]
fn test_variety_mult_scaling() {
    // 0 foods = 1.0 (no bonus)
    assert!((calculate_variety_mult(0) - 1.0).abs() < 0.01);

    // Exponential growth toward cap
    let mult_10 = calculate_variety_mult(10);
    let mult_20 = calculate_variety_mult(20);
    let mult_40 = calculate_variety_mult(40);

    // Each doubling of count should halve the remaining gap
    assert!(mult_10 > 1.0);
    assert!(mult_20 > mult_10);
    assert!(mult_40 > mult_20);

    // Never exceeds max
    assert!(calculate_variety_mult(1000) < VARIETY_MULT_MAX);
}

#[test]
fn test_sp_calculation_empty_stomach() {
    let stomach: HashMap<&Food, u32> = HashMap::new();
    let config = SpConfig::default();
    let sp = calculate_sp(&stomach, &[], &config);

    // With empty stomach, SP should equal BASE_SKILL_POINTS
    assert!((sp - BASE_SKILL_POINTS).abs() < 0.01);
}

#[test]
fn test_sp_increases_with_food() {
    let food = make_food("Balanced", 500.0, 10.0, 10.0, 10.0, 10.0, 2);
    let config = SpConfig::default();

    let empty_stomach: HashMap<&Food, u32> = HashMap::new();
    let sp_empty = calculate_sp(&empty_stomach, &[], &config);

    let mut with_food: HashMap<&Food, u32> = HashMap::new();
    with_food.insert(&food, 1);
    let sp_with_food = calculate_sp(&with_food, &[], &config);

    // Adding nutritious food should increase SP
    assert!(sp_with_food > sp_empty);
}

#[test]
fn test_craving_mult_effect() {
    let food = make_food("Craved", 500.0, 10.0, 10.0, 10.0, 10.0, 2);
    let config = SpConfig::default();

    let mut stomach: HashMap<&Food, u32> = HashMap::new();
    stomach.insert(&food, 1);

    let sp_no_craving = calculate_sp(&stomach, &[], &config);
    let sp_with_craving = calculate_sp(&stomach, &["Craved".to_string()], &config);

    // Having the craved food in stomach should give multiplier bonus
    assert!(sp_with_craving > sp_no_craving);
}

#[test]
fn test_server_mult_effect() {
    let food = make_food("Food", 500.0, 10.0, 10.0, 10.0, 10.0, 2);

    let mut stomach: HashMap<&Food, u32> = HashMap::new();
    stomach.insert(&food, 1);

    let config_1x = SpConfig::default();
    let config_2x = SpConfig {
        server_mult: 2.0,
        ..Default::default()
    };

    let sp_1x = calculate_sp(&stomach, &[], &config_1x);
    let sp_2x = calculate_sp(&stomach, &[], &config_2x);

    // 2x server multiplier should double SP
    assert!((sp_2x / sp_1x - 2.0).abs() < 0.01);
}
