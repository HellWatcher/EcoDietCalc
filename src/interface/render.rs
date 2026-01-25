use crate::models::MealPlanItem;
use crate::planner::constants::{
    CRAVING_MULT_PER_MATCH, TASTE_DELTA_THRESHOLD, VARIETY_DELTA_THRESHOLD,
};

/// Display a meal plan in a formatted table.
pub fn display_meal_plan(plan: &[MealPlanItem]) {
    if plan.is_empty() {
        println!("No meal plan generated (no available foods or zero calorie budget).");
        return;
    }

    println!();
    println!("=== Meal Plan ===");
    println!();

    // Find max food name length for alignment
    let max_name_len = plan.iter().map(|p| p.food_name.len()).max().unwrap_or(10);

    let total_calories: f64 = plan.iter().map(|p| p.calories).sum();
    let total_sp_gain: f64 = plan.iter().map(|p| p.sp_gain).sum();
    let final_sp = plan.last().map(|p| p.new_total_sp).unwrap_or(0.0);

    for (i, item) in plan.iter().enumerate() {
        let mut tags = Vec::new();

        // Craving tag
        if item.is_craving {
            tags.push(format!("[Craving +{:.0}%]", CRAVING_MULT_PER_MATCH * 100.0));
        }

        // Variety delta tag
        if item.variety_delta.abs() > VARIETY_DELTA_THRESHOLD {
            let sign = if item.variety_delta > 0.0 { "+" } else { "" };
            tags.push(format!("Variety {} {:.2} pp", sign, item.variety_delta));
        }

        // Taste delta tag
        if item.taste_delta.abs() > TASTE_DELTA_THRESHOLD {
            let sign = if item.taste_delta > 0.0 { "+" } else { "" };
            tags.push(format!("Taste {} {:.2} pp", sign, item.taste_delta));
        }

        let tags_str = if tags.is_empty() {
            String::new()
        } else {
            format!("  {}", tags.join(", "))
        };

        let sp_sign = if item.sp_gain >= 0.0 { "+" } else { "" };

        println!(
            "{:>3}. {:<width$} - {:>4.0} cal | SP {}{:.2} => {:.2}{}",
            i + 1,
            item.food_name,
            item.calories,
            sp_sign,
            item.sp_gain,
            item.new_total_sp,
            tags_str,
            width = max_name_len
        );
    }

    println!();
    println!("--- Summary ---");
    println!("Total items: {}", plan.len());
    println!("Total calories: {:.0}", total_calories);
    println!("Total SP gain: {:.2}", total_sp_gain);
    println!("Final SP: {:.2}", final_sp);
    println!();
}

/// Display a simple list of foods with their details.
pub fn display_food_list(foods: &[&crate::models::Food], title: &str) {
    if foods.is_empty() {
        println!("{}: (none)", title);
        return;
    }

    println!();
    println!("=== {} ({} items) ===", title, foods.len());
    println!();

    for food in foods {
        println!(
            "  {} - {} cal, C:{} P:{} F:{} V:{}, taste:{}",
            food.name,
            food.calories,
            food.carbs,
            food.protein,
            food.fats,
            food.vitamins,
            food.tastiness
        );
    }

    println!();
}
