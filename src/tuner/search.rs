use std::path::PathBuf;

use rand::rngs::StdRng;
use rand::SeedableRng;

use crate::models::Food;
use crate::tuner::evaluation::{evaluate_knobs, EvaluationResult};
use crate::tuner::knobs::{KnobRanges, TunerKnobs};

/// Configuration for the tuner.
pub struct TunerConfig {
    pub iterations: usize,
    pub seed: u64,
    pub budgets: Vec<f64>,
    pub ranges: KnobRanges,
    pub foods_path: PathBuf,
    pub topk: usize,
}

impl Default for TunerConfig {
    fn default() -> Self {
        Self {
            iterations: 300,
            seed: 123,
            // Realistic budgets: players consume 10s of thousands of calories
            budgets: vec![5000.0, 10000.0, 20000.0, 40000.0],
            ranges: KnobRanges::default(),
            topk: 10,
            foods_path: PathBuf::from("food_state.json"),
        }
    }
}

/// Results from a tuning run.
pub struct TunerResults {
    /// All evaluation results, sorted best to worst.
    pub results: Vec<EvaluationResult>,
    /// The baseline result using default constants.
    pub baseline: EvaluationResult,
}

/// Run random-search tuning.
pub fn run_tuner(config: TunerConfig, foods: &[Food]) -> TunerResults {
    let mut rng = StdRng::seed_from_u64(config.seed);
    let mut results = Vec::with_capacity(config.iterations);

    // Evaluate baseline (default constants)
    let baseline_knobs = TunerKnobs::default();
    let baseline = evaluate_knobs(&baseline_knobs, foods, &config.budgets);

    println!("Baseline: SP={:.2} delta/100kcal={:.3} variety={:.1}",
        baseline.avg_final_sp,
        baseline.avg_delta_sp_per_100kcal,
        baseline.avg_variety_count
    );
    println!("    {}\n", baseline_knobs.display());

    // Run random search
    println!("Running {} iterations...", config.iterations);

    let mut best_sp = baseline.avg_final_sp;

    for i in 0..config.iterations {
        let knobs = TunerKnobs::random(&mut rng, &config.ranges);
        let result = evaluate_knobs(&knobs, foods, &config.budgets);

        if result.avg_final_sp > best_sp {
            best_sp = result.avg_final_sp;
            println!(
                "[{}/{}] New best: SP={:.2} delta/100kcal={:.3} variety={:.1}",
                i + 1,
                config.iterations,
                result.avg_final_sp,
                result.avg_delta_sp_per_100kcal,
                result.avg_variety_count
            );
        }

        results.push(result);

        // Progress indicator every 10%
        if (i + 1) % (config.iterations / 10).max(1) == 0 {
            let pct = ((i + 1) as f64 / config.iterations as f64) * 100.0;
            eprint!("\r{:.0}% complete", pct);
        }
    }
    eprintln!();

    // Sort results by score (best first)
    results.sort_by(|a, b| b.cmp_score(a));

    TunerResults { results, baseline }
}
