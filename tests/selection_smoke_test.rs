use eco_diet_maker_rs::models::Food;
use eco_diet_maker_rs::planner::{generate_plan, SpConfig};
use eco_diet_maker_rs::state::FoodStateManager;

fn sample_foods() -> Vec<Food> {
    vec![
        Food {
            name: "High Protein".to_string(),
            calories: 400.0,
            carbs: 5.0,
            protein: 30.0,
            fats: 10.0,
            vitamins: 2.0,
            tastiness: 2,
            stomach: 0,
            available: 20,
        },
        Food {
            name: "High Carb".to_string(),
            calories: 500.0,
            carbs: 50.0,
            protein: 5.0,
            fats: 5.0,
            vitamins: 3.0,
            tastiness: 1,
            stomach: 0,
            available: 20,
        },
        Food {
            name: "Balanced".to_string(),
            calories: 450.0,
            carbs: 15.0,
            protein: 15.0,
            fats: 15.0,
            vitamins: 10.0,
            tastiness: 3,
            stomach: 0,
            available: 20,
        },
        Food {
            name: "Low Cal Snack".to_string(),
            calories: 100.0,
            carbs: 10.0,
            protein: 2.0,
            fats: 1.0,
            vitamins: 5.0,
            tastiness: 2,
            stomach: 0,
            available: 50,
        },
    ]
}

#[test]
fn test_generate_plan_respects_calorie_budget() {
    let mut manager = FoodStateManager::new(sample_foods());
    let config = SpConfig::default();
    let plan = generate_plan(&mut manager, &[], &config, 1000.0);

    let total_cal: f64 = plan.iter().map(|p| p.calories).sum();

    // Total calories should be at or under budget (with allowance for first bite)
    assert!(
        total_cal <= 1000.0 || plan.len() == 1,
        "Plan exceeded budget: {} calories",
        total_cal
    );
}

#[test]
fn test_generate_plan_nonempty_for_available_foods() {
    let mut manager = FoodStateManager::new(sample_foods());
    let config = SpConfig::default();
    let plan = generate_plan(&mut manager, &[], &config, 2000.0);

    assert!(
        !plan.is_empty(),
        "Plan should not be empty when foods are available"
    );
}

#[test]
fn test_generate_plan_prioritizes_cravings() {
    let mut manager = FoodStateManager::new(sample_foods());
    let config = SpConfig::default();
    let cravings = vec!["Balanced".to_string()];
    let plan = generate_plan(&mut manager, &cravings, &config, 500.0);

    // First item should be the craving if available
    assert!(!plan.is_empty());
    assert_eq!(
        plan[0].food_name.to_lowercase(),
        "balanced",
        "Expected craving to be selected first"
    );
    assert!(plan[0].is_craving);
}

#[test]
fn test_generate_plan_sp_increases_monotonically() {
    let mut manager = FoodStateManager::new(sample_foods());
    let config = SpConfig::default();
    let plan = generate_plan(&mut manager, &[], &config, 3000.0);

    assert!(!plan.is_empty());

    // Each item's new_total_sp should be >= the previous
    for window in plan.windows(2) {
        assert!(
            window[1].new_total_sp >= window[0].new_total_sp,
            "SP should not decrease: {} -> {}",
            window[0].new_total_sp,
            window[1].new_total_sp
        );
    }
}

#[test]
fn test_generate_plan_updates_state() {
    let mut manager = FoodStateManager::new(sample_foods());
    let config = SpConfig::default();

    let before_available: u32 = manager.all_available().iter().map(|f| f.available).sum();

    let plan = generate_plan(&mut manager, &[], &config, 1500.0);

    let after_available: u32 = manager.all_available().iter().map(|f| f.available).sum();
    let total_stomach: u32 = manager.all_foods().iter().map(|f| f.stomach).sum();

    // Available should decrease by number of items consumed
    let items_consumed = plan.len() as u32;
    assert_eq!(
        before_available - after_available,
        items_consumed,
        "Available count mismatch"
    );
    assert_eq!(total_stomach, items_consumed, "Stomach count mismatch");
}

#[test]
fn test_generate_plan_empty_when_no_available() {
    let foods: Vec<Food> = sample_foods()
        .into_iter()
        .map(|mut f| {
            f.available = 0;
            f
        })
        .collect();

    let mut manager = FoodStateManager::new(foods);
    let config = SpConfig::default();
    let plan = generate_plan(&mut manager, &[], &config, 2000.0);

    assert!(
        plan.is_empty(),
        "Plan should be empty when no foods are available"
    );
}

#[test]
fn test_generate_plan_zero_budget() {
    let mut manager = FoodStateManager::new(sample_foods());
    let config = SpConfig::default();
    let plan = generate_plan(&mut manager, &[], &config, 0.0);

    assert!(
        plan.is_empty(),
        "Plan should be empty with zero calorie budget"
    );
}
