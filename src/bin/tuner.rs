use std::fs;
use std::path::PathBuf;

use clap::Parser;

use eco_diet_maker_rs::models::Food;
use eco_diet_maker_rs::tuner::{
    print_topk, run_tuner, write_best_json, write_csv, KnobRanges, TunerConfig,
};

#[derive(Parser, Debug)]
#[command(name = "tuner")]
#[command(about = "Hyperparameter tuner for the eco diet planner")]
struct Args {
    /// Number of random search iterations
    #[arg(long, default_value = "300")]
    iters: usize,

    /// Random seed for reproducibility
    #[arg(long, default_value = "123")]
    seed: u64,

    /// Calorie budgets to evaluate (comma-separated)
    #[arg(long, default_value = "5000,10000,20000,40000")]
    budgets: String,

    /// Path to food_state.json
    #[arg(long, default_value = "food_state.json")]
    foods: PathBuf,

    /// Output CSV file for all results
    #[arg(long, default_value = "tuner_results.csv")]
    csv: PathBuf,

    /// Output JSON file for best result
    #[arg(long, default_value = "tuner_best.json")]
    json: PathBuf,

    /// Number of top results to display
    #[arg(long, default_value = "10")]
    topk: usize,
}

fn parse_budgets(s: &str) -> Vec<f64> {
    s.split(',')
        .filter_map(|part| part.trim().parse().ok())
        .collect()
}

fn main() {
    let args = Args::parse();

    // Load foods
    let foods_json = match fs::read_to_string(&args.foods) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("Error reading foods file {:?}: {}", args.foods, e);
            std::process::exit(1);
        }
    };

    let foods: Vec<Food> = match serde_json::from_str(&foods_json) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("Error parsing foods JSON: {}", e);
            std::process::exit(1);
        }
    };

    println!("Loaded {} foods from {:?}", foods.len(), args.foods);

    // Parse budgets
    let budgets = parse_budgets(&args.budgets);
    if budgets.is_empty() {
        eprintln!("Error: no valid budgets provided");
        std::process::exit(1);
    }
    println!("Testing budgets: {:?}", budgets);

    // Configure tuner
    let config = TunerConfig {
        iterations: args.iters,
        seed: args.seed,
        budgets,
        ranges: KnobRanges::default(),
        foods_path: args.foods.clone(),
        topk: args.topk,
    };

    // Run tuning
    let tuner_results = run_tuner(config, &foods);

    // Print top-k
    print_topk(&tuner_results.results, args.topk);

    // Compare best to baseline
    if let Some(best) = tuner_results.results.first() {
        let baseline = &tuner_results.baseline;
        let sp_improvement = best.avg_final_sp - baseline.avg_final_sp;
        let sp_pct = (sp_improvement / baseline.avg_final_sp) * 100.0;

        println!("=== Comparison to Baseline ===");
        println!(
            "Baseline: SP={:.2} delta/100kcal={:.3} variety={:.1}",
            baseline.avg_final_sp, baseline.avg_delta_sp_per_100kcal, baseline.avg_variety_count
        );
        println!(
            "Best:     SP={:.2} delta/100kcal={:.3} variety={:.1}",
            best.avg_final_sp, best.avg_delta_sp_per_100kcal, best.avg_variety_count
        );
        println!(
            "Change:   SP {:+.2} ({:+.2}%)",
            sp_improvement, sp_pct
        );
        println!();
    }

    // Write outputs
    if let Err(e) = write_csv(&tuner_results.results, &args.csv) {
        eprintln!("Error writing CSV: {}", e);
    } else {
        println!("Wrote results to {:?}", args.csv);
    }

    if let Some(best) = tuner_results.results.first() {
        if let Err(e) = write_best_json(best, &args.json) {
            eprintln!("Error writing JSON: {}", e);
        } else {
            println!("Wrote best result to {:?}", args.json);
        }
    }
}
