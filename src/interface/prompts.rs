use dialoguer::{Confirm, Input, Select};
use strsim::jaro_winkler;

use crate::error::{EcoError, Result};
use crate::models::Food;
use crate::planner::constants::tastiness_name;

/// Prompt for current calories already consumed.
pub fn prompt_current_calories() -> Result<f64> {
    let input: String = Input::new()
        .with_prompt("How many calories have you already consumed today?")
        .default("0".to_string())
        .interact_text()?;

    input
        .parse()
        .map_err(|_| EcoError::InvalidInput("Invalid number".to_string()))
}

/// Prompt for maximum calorie limit.
pub fn prompt_max_calories(current: f64) -> Result<f64> {
    let input: String = Input::new()
        .with_prompt("What is your maximum calorie limit for today?")
        .default("2500".to_string())
        .interact_text()?;

    let max: f64 = input
        .parse()
        .map_err(|_| EcoError::InvalidInput("Invalid number".to_string()))?;

    if max < current {
        return Err(EcoError::InvalidInput(
            "Max calories must be >= current calories".to_string(),
        ));
    }

    Ok(max)
}

/// Prompt for number of cravings already satisfied today.
pub fn prompt_cravings_satisfied() -> Result<u32> {
    let input: String = Input::new()
        .with_prompt("How many cravings have you satisfied today?")
        .default("0".to_string())
        .interact_text()?;

    input
        .parse()
        .map_err(|_| EcoError::InvalidInput("Invalid number".to_string()))
}

/// Prompt for current cravings with fuzzy matching.
pub fn prompt_cravings(available_foods: &[&Food]) -> Result<Vec<String>> {
    let mut cravings = Vec::new();

    loop {
        let input: String = Input::new()
            .with_prompt("Enter a craving (or press Enter to finish)")
            .allow_empty(true)
            .interact_text()?;

        let input = input.trim();
        if input.is_empty() {
            break;
        }

        // Try exact match first (case-insensitive)
        let exact_match = available_foods
            .iter()
            .find(|f| f.name.to_lowercase() == input.to_lowercase());

        if let Some(food) = exact_match {
            cravings.push(food.name.clone());
            println!("Added: {}", food.name);
            continue;
        }

        // Try fuzzy matching
        let mut candidates: Vec<(&Food, f64)> = available_foods
            .iter()
            .map(|f| (*f, jaro_winkler(&f.name.to_lowercase(), &input.to_lowercase())))
            .filter(|(_, score)| *score > 0.7)
            .collect();

        candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        if candidates.is_empty() {
            println!("No matching food found for '{}'", input);
            continue;
        }

        if candidates.len() == 1 {
            let food = candidates[0].0;
            let confirm = Confirm::new()
                .with_prompt(format!("Did you mean '{}'?", food.name))
                .default(true)
                .interact()?;

            if confirm {
                cravings.push(food.name.clone());
                println!("Added: {}", food.name);
            }
        } else {
            // Multiple matches - let user select
            let options: Vec<String> = candidates
                .iter()
                .take(5)
                .map(|(f, _)| f.name.clone())
                .collect();

            let mut selection_options = options.clone();
            selection_options.push("None of these".to_string());

            let selection = Select::new()
                .with_prompt("Which did you mean?")
                .items(&selection_options)
                .default(0)
                .interact()?;

            if selection < options.len() {
                cravings.push(options[selection].clone());
                println!("Added: {}", options[selection]);
            }
        }
    }

    Ok(cravings)
}

/// Prompt for tastiness rating.
pub fn prompt_tastiness(food_name: &str) -> Result<i8> {
    let options = vec![
        format!("-3 ({})", tastiness_name(-3)),
        format!("-2 ({})", tastiness_name(-2)),
        format!("-1 ({})", tastiness_name(-1)),
        format!(" 0 ({})", tastiness_name(0)),
        format!(" 1 ({})", tastiness_name(1)),
        format!(" 2 ({})", tastiness_name(2)),
        format!(" 3 ({})", tastiness_name(3)),
        format!("99 ({})", tastiness_name(99)),
    ];

    let selection = Select::new()
        .with_prompt(format!("Rate the tastiness of '{}'", food_name))
        .items(&options)
        .default(3) // neutral (0)
        .interact()?;

    Ok(match selection {
        0 => -3,
        1 => -2,
        2 => -1,
        3 => 0,
        4 => 1,
        5 => 2,
        6 => 3,
        7 => 99,
        _ => 0,
    })
}

/// Prompt for yes/no confirmation.
pub fn prompt_yes_no(prompt: &str, default: bool) -> Result<bool> {
    Ok(Confirm::new()
        .with_prompt(prompt)
        .default(default)
        .interact()?)
}

/// Collect all user constraints for meal planning.
pub fn collect_user_constraints(
    available_foods: &[&Food],
) -> Result<(Vec<String>, u32, f64)> {
    let current_cal = prompt_current_calories()?;
    let max_cal = prompt_max_calories(current_cal)?;
    let cravings_satisfied = prompt_cravings_satisfied()?;
    let cravings = prompt_cravings(available_foods)?;

    let remaining = max_cal - current_cal;

    Ok((cravings, cravings_satisfied, remaining))
}
