use clap::Parser;
use std::path::Path;

use eco_diet_maker_rs::cli::{Cli, Command};
use eco_diet_maker_rs::error::Result;
use eco_diet_maker_rs::interface::{
    collect_user_constraints, display_meal_plan, prompt_tastiness, prompt_yes_no,
};
use eco_diet_maker_rs::planner::generate_plan;
use eco_diet_maker_rs::state::{load_foods, save_foods, FoodStateManager};

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let cli = Cli::parse();
    let command = cli.command.unwrap_or_default();

    match command {
        Command::Plan => cmd_plan(&cli.file),
        Command::RateUnknowns => cmd_rate_unknowns(&cli.file),
        Command::Reset {
            stomach,
            availability,
            tastiness,
        } => cmd_reset(&cli.file, stomach, availability, tastiness),
    }
}

/// Generate a meal plan based on user constraints.
fn cmd_plan(file_path: &str) -> Result<()> {
    let path = Path::new(file_path);

    if !path.exists() {
        eprintln!("Food state file not found: {}", file_path);
        eprintln!("Please ensure food_state.json exists in the current directory.");
        return Ok(());
    }

    // Load foods
    let foods = load_foods(path)?;
    let mut manager = FoodStateManager::new(foods);

    println!("Loaded {} foods", manager.len());

    // Check for available foods
    let available = manager.all_available();
    if available.is_empty() {
        println!("No foods available. Use 'reset --availability' to set availability.");
        return Ok(());
    }

    println!("{} foods available", available.len());
    println!();

    // Collect user constraints
    let (cravings, cravings_satisfied, remaining_cal) = collect_user_constraints(&available)?;

    if remaining_cal <= 0.0 {
        println!("No remaining calories to plan for.");
        return Ok(());
    }

    println!();
    println!("Planning for {:.0} remaining calories...", remaining_cal);
    if !cravings.is_empty() {
        println!("Cravings: {}", cravings.join(", "));
    }
    println!();

    // Generate plan
    let plan = generate_plan(&mut manager, &cravings, cravings_satisfied, remaining_cal);

    // Display results
    display_meal_plan(&plan);

    // Save updated state
    if !plan.is_empty() {
        let save = prompt_yes_no("Save updated food state?", true)?;
        if save {
            save_foods(path, &manager.to_foods())?;
            println!("Food state saved.");
        }
    }

    Ok(())
}

/// Rate foods with unknown tastiness.
fn cmd_rate_unknowns(file_path: &str) -> Result<()> {
    let path = Path::new(file_path);

    if !path.exists() {
        eprintln!("Food state file not found: {}", file_path);
        return Ok(());
    }

    // Load foods
    let foods = load_foods(path)?;
    let mut manager = FoodStateManager::new(foods);

    // Find available foods with unknown tastiness
    let unknowns: Vec<String> = manager
        .all_available()
        .into_iter()
        .filter(|f| f.tastiness == 99)
        .map(|f| f.name.clone())
        .collect();

    if unknowns.is_empty() {
        println!("No available foods with unknown tastiness.");
        return Ok(());
    }

    println!("Found {} foods with unknown tastiness.", unknowns.len());
    println!();

    let mut rated_count = 0;

    for name in &unknowns {
        let rating = prompt_tastiness(name)?;

        if let Some(food) = manager.get_food_mut(name) {
            food.tastiness = rating;
            rated_count += 1;
        }

        // Allow early exit
        if rated_count < unknowns.len() {
            let continue_rating = prompt_yes_no("Continue rating?", true)?;
            if !continue_rating {
                break;
            }
        }
    }

    if rated_count > 0 {
        save_foods(path, &manager.to_foods())?;
        println!("Rated {} foods. State saved.", rated_count);
    }

    Ok(())
}

/// Reset various state values.
fn cmd_reset(file_path: &str, stomach: bool, availability: bool, tastiness: bool) -> Result<()> {
    if !stomach && !availability && !tastiness {
        println!("Please specify at least one reset option:");
        println!("  --stomach      Reset stomach counts to 0");
        println!("  --availability Reset all availability to 0");
        println!("  --tastiness    Set all tastiness to unknown (99)");
        return Ok(());
    }

    let path = Path::new(file_path);

    if !path.exists() {
        eprintln!("Food state file not found: {}", file_path);
        return Ok(());
    }

    // Load foods
    let foods = load_foods(path)?;
    let mut manager = FoodStateManager::new(foods);

    if stomach {
        manager.reset_stomach();
        println!("Reset all stomach counts to 0.");
    }

    if availability {
        manager.reset_availability(0);
        println!("Reset all availability to 0.");
    }

    if tastiness {
        manager.reset_tastiness(true);
        println!("Reset all tastiness to unknown (99).");
    }

    // Save updated state
    save_foods(path, &manager.to_foods())?;
    println!("Food state saved.");

    Ok(())
}
