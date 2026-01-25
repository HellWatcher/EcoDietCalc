use std::fs::File;
use std::io::Write;
use std::path::Path;

use crate::error::Result;
use crate::tuner::evaluation::EvaluationResult;

/// Write all results to a CSV file.
pub fn write_csv(results: &[EvaluationResult], path: &Path) -> Result<()> {
    let mut wtr = csv::Writer::from_path(path)?;

    // Write header
    wtr.write_record([
        "rank",
        "soft_bias_gamma",
        "tie_alpha",
        "tie_beta",
        "tie_epsilon",
        "cal_floor",
        "cal_penalty_gamma",
        "avg_final_sp",
        "avg_delta_sp_per_100kcal",
        "avg_variety_count",
    ])?;

    // Write data rows
    for (i, result) in results.iter().enumerate() {
        wtr.write_record([
            (i + 1).to_string(),
            format!("{:.6}", result.knobs.soft_bias_gamma),
            format!("{:.6}", result.knobs.tie_alpha),
            format!("{:.6}", result.knobs.tie_beta),
            format!("{:.6}", result.knobs.tie_epsilon),
            format!("{:.2}", result.knobs.cal_floor),
            format!("{:.6}", result.knobs.cal_penalty_gamma),
            format!("{:.4}", result.avg_final_sp),
            format!("{:.4}", result.avg_delta_sp_per_100kcal),
            format!("{:.2}", result.avg_variety_count),
        ])?;
    }

    wtr.flush()?;
    Ok(())
}

/// Write the best result to a JSON file.
pub fn write_best_json(best: &EvaluationResult, path: &Path) -> Result<()> {
    let json = serde_json::json!({
        "knobs": {
            "soft_bias_gamma": best.knobs.soft_bias_gamma,
            "tie_alpha": best.knobs.tie_alpha,
            "tie_beta": best.knobs.tie_beta,
            "tie_epsilon": best.knobs.tie_epsilon,
            "cal_floor": best.knobs.cal_floor,
            "cal_penalty_gamma": best.knobs.cal_penalty_gamma,
        },
        "metrics": {
            "avg_final_sp": best.avg_final_sp,
            "avg_delta_sp_per_100kcal": best.avg_delta_sp_per_100kcal,
            "avg_variety_count": best.avg_variety_count,
        },
        "per_budget": best.per_budget.iter().map(|r| {
            serde_json::json!({
                "budget": r.budget,
                "final_sp": r.final_sp,
                "total_calories": r.total_calories,
                "variety_count": r.variety_count,
                "bites": r.bites,
                "delta_sp_per_100kcal": r.delta_sp_per_100kcal(),
            })
        }).collect::<Vec<_>>(),
    });

    let mut file = File::create(path)?;
    file.write_all(serde_json::to_string_pretty(&json)?.as_bytes())?;
    Ok(())
}

/// Print top-k results to stdout.
pub fn print_topk(results: &[EvaluationResult], k: usize) {
    println!("\n=== Top {} Results ===\n", k.min(results.len()));

    for (i, result) in results.iter().take(k).enumerate() {
        println!(
            "#{}: SP={:.2} delta/100kcal={:.3} variety={:.1}",
            i + 1,
            result.avg_final_sp,
            result.avg_delta_sp_per_100kcal,
            result.avg_variety_count
        );
        println!("    {}", result.knobs.display());
        println!();
    }
}
