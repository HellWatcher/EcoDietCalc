use std::fs;
use std::path::PathBuf;

use clap::Parser;

use eco_diet_maker_rs::models::Food;
use eco_diet_maker_rs::tuner::{
    print_pareto_frontier, print_topk, run_tuner, write_best_json, write_csv, HillClimbConfig,
    KnobRanges, TunerConfig,
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

    /// Disable hill climbing refinement
    #[arg(long)]
    no_hill_climb: bool,
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
    let hill_climb = if args.no_hill_climb {
        None
    } else {
        Some(HillClimbConfig::default())
    };

    let config = TunerConfig {
        iterations: args.iters,
        seed: args.seed,
        budgets,
        ranges: KnobRanges::default(),
        foods_path: args.foods.clone(),
        topk: args.topk,
        hill_climb,
    };

    // Run tuning
    let tuner_results = run_tuner(config, &foods);

    // Print Pareto frontier (primary output)
    print_pareto_frontier(
        &tuner_results.results,
        &tuner_results.pareto_indices,
        tuner_results.balanced_idx,
    );

    // Also print top-k by SP for reference
    print_topk(&tuner_results.results, args.topk);

    // Get the balanced result (or fall back to top SP)
    let best_idx = tuner_results.balanced_idx.unwrap_or(0);
    let best = &tuner_results.results[best_idx];
    let baseline = &tuner_results.baseline;

    // Compare balanced result to baseline
    let sp_improvement = best.avg_final_sp - baseline.avg_final_sp;
    let sp_pct = (sp_improvement / baseline.avg_final_sp) * 100.0;
    let variety_improvement = best.avg_variety_count - baseline.avg_variety_count;
    let balance_improvement = best.avg_balance_ratio - baseline.avg_balance_ratio;

    println!("=== Comparison: Balanced vs Baseline ===");
    println!(
        "Baseline: SP={:.2} variety={:.1} balance={:.3}",
        baseline.avg_final_sp, baseline.avg_variety_count, baseline.avg_balance_ratio
    );
    println!(
        "Balanced: SP={:.2} variety={:.1} balance={:.3}",
        best.avg_final_sp, best.avg_variety_count, best.avg_balance_ratio
    );
    println!(
        "Change:   SP {:+.2} ({:+.2}%)  variety {:+.1}  balance {:+.3}",
        sp_improvement, sp_pct, variety_improvement, balance_improvement
    );
    println!();

    // Write outputs
    if let Err(e) = write_csv(&tuner_results.results, &args.csv) {
        eprintln!("Error writing CSV: {}", e);
    } else {
        println!("Wrote all results to {:?}", args.csv);
    }

    // Save balanced result to JSON
    if let Err(e) = write_best_json(best, &args.json) {
        eprintln!("Error writing JSON: {}", e);
    } else {
        println!("Wrote balanced result to {:?}", args.json);
    }
}
