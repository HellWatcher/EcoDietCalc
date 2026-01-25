use std::collections::HashMap;

use eco_diet_maker_rs::models::Food;
use eco_diet_maker_rs::planner::{
    calculate_sp, calculate_variety_bonus, is_variety_qualifying, BASE_SKILL_POINTS,
    VARIETY_CAL_THRESHOLD,
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
fn test_variety_bonus_scaling() {
    // 0 foods = 0 bonus
    assert_eq!(calculate_variety_bonus(0), 0.0);

    // Exponential growth toward cap
    let bonus_10 = calculate_variety_bonus(10);
    let bonus_20 = calculate_variety_bonus(20);
    let bonus_40 = calculate_variety_bonus(40);

    // Each doubling of count should halve the remaining gap
    assert!(bonus_10 > 0.0);
    assert!(bonus_20 > bonus_10);
    assert!(bonus_40 > bonus_20);

    // Never exceeds cap (55)
    assert!(calculate_variety_bonus(1000) < 55.0);
}

#[test]
fn test_sp_calculation_empty_stomach() {
    let stomach: HashMap<&Food, u32> = HashMap::new();
    let sp = calculate_sp(&stomach, &[], 0);

    // With empty stomach, SP should equal BASE_SKILL_POINTS
    assert!((sp - BASE_SKILL_POINTS).abs() < 0.01);
}

#[test]
fn test_sp_increases_with_food() {
    let food = make_food("Balanced", 500.0, 10.0, 10.0, 10.0, 10.0, 2);

    let empty_stomach: HashMap<&Food, u32> = HashMap::new();
    let sp_empty = calculate_sp(&empty_stomach, &[], 0);

    let mut with_food: HashMap<&Food, u32> = HashMap::new();
    with_food.insert(&food, 1);
    let sp_with_food = calculate_sp(&with_food, &[], 0);

    // Adding nutritious food should increase SP
    assert!(sp_with_food > sp_empty);
}

#[test]
fn test_craving_bonus_effect() {
    let food = make_food("Craved", 500.0, 10.0, 10.0, 10.0, 10.0, 2);

    let mut stomach: HashMap<&Food, u32> = HashMap::new();
    stomach.insert(&food, 1);

    let sp_no_craving = calculate_sp(&stomach, &[], 0);
    let sp_with_craving = calculate_sp(&stomach, &["Craved".to_string()], 0);

    // Having the craved food in stomach should give bonus
    assert!(sp_with_craving > sp_no_craving);
}

#[test]
fn test_cravings_satisfied_bonus() {
    let food = make_food("Food", 500.0, 10.0, 10.0, 10.0, 10.0, 2);

    let mut stomach: HashMap<&Food, u32> = HashMap::new();
    stomach.insert(&food, 1);

    let sp_0_satisfied = calculate_sp(&stomach, &[], 0);
    let sp_1_satisfied = calculate_sp(&stomach, &[], 1);
    let sp_2_satisfied = calculate_sp(&stomach, &[], 2);

    // Each satisfied craving should add bonus
    assert!(sp_1_satisfied > sp_0_satisfied);
    assert!(sp_2_satisfied > sp_1_satisfied);
}
