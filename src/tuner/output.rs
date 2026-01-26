use std::fs::File;
use std::io::Write;
use std::path::Path;

use crate::error::Result;
use crate::tuner::evaluation::EvaluationResult;

/// Truncate a float to n decimal places.
fn truncate(value: f64, decimals: u32) -> f64 {
    let factor = 10_f64.powi(decimals as i32);
    (value * factor).round() / factor
}

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
        "balance_bias_gamma",
        "repetition_penalty_gamma",
        "avg_final_sp",
        "avg_delta_sp_per_100kcal",
        "avg_variety_count",
    ])?;

    // Write data rows (truncated to 3 decimal places for knobs)
    for (i, result) in results.iter().enumerate() {
        wtr.write_record([
            (i + 1).to_string(),
            format!("{:.3}", result.knobs.soft_bias_gamma),
            format!("{:.3}", result.knobs.tie_alpha),
            format!("{:.3}", result.knobs.tie_beta),
            format!("{:.3}", result.knobs.tie_epsilon),
            format!("{:.1}", result.knobs.cal_floor),
            format!("{:.3}", result.knobs.cal_penalty_gamma),
            format!("{:.3}", result.knobs.balance_bias_gamma),
            format!("{:.3}", result.knobs.repetition_penalty_gamma),
            format!("{:.2}", result.avg_final_sp),
            format!("{:.3}", result.avg_delta_sp_per_100kcal),
            format!("{:.1}", result.avg_variety_count),
        ])?;
    }

    wtr.flush()?;
    Ok(())
}

/// Write the best result to a JSON file with truncated floats.
pub fn write_best_json(best: &EvaluationResult, path: &Path) -> Result<()> {
    let json = serde_json::json!({
        "knobs": {
            "soft_bias_gamma": truncate(best.knobs.soft_bias_gamma, 3),
            "tie_alpha": truncate(best.knobs.tie_alpha, 3),
            "tie_beta": truncate(best.knobs.tie_beta, 3),
            "tie_epsilon": truncate(best.knobs.tie_epsilon, 3),
            "cal_floor": truncate(best.knobs.cal_floor, 1),
            "cal_penalty_gamma": truncate(best.knobs.cal_penalty_gamma, 3),
            "balance_bias_gamma": truncate(best.knobs.balance_bias_gamma, 3),
            "repetition_penalty_gamma": truncate(best.knobs.repetition_penalty_gamma, 3),
        },
        "metrics": {
            "avg_final_sp": truncate(best.avg_final_sp, 2),
            "avg_delta_sp_per_100kcal": truncate(best.avg_delta_sp_per_100kcal, 3),
            "avg_variety_count": truncate(best.avg_variety_count, 1),
            "avg_balance_ratio": truncate(best.avg_balance_ratio, 3),
        },
        "per_budget": best.per_budget.iter().map(|r| {
            serde_json::json!({
                "budget": r.budget,
                "final_sp": truncate(r.final_sp, 2),
                "total_calories": r.total_calories,
                "variety_count": r.variety_count,
                "bites": r.bites,
                "delta_sp_per_100kcal": truncate(r.delta_sp_per_100kcal(), 3),
                "balance_ratio": truncate(r.balance_ratio, 3),
            })
        }).collect::<Vec<_>>(),
    });

    let mut file = File::create(path)?;
    file.write_all(serde_json::to_string_pretty(&json)?.as_bytes())?;
    Ok(())
}

/// Print top-k results to stdout.
pub fn print_topk(results: &[EvaluationResult], k: usize) {
    println!("\n=== Top {} Results (by SP) ===\n", k.min(results.len()));

    for (i, result) in results.iter().take(k).enumerate() {
        println!(
            "#{}: SP={:.2} delta/100kcal={:.3} variety={:.1} balance={:.3}",
            i + 1,
            result.avg_final_sp,
            result.avg_delta_sp_per_100kcal,
            result.avg_variety_count,
            result.avg_balance_ratio
        );
        println!("    {}", result.knobs.display());
        println!();
    }
}

/// Print Pareto frontier with the balanced pick highlighted.
pub fn print_pareto_frontier(
    results: &[EvaluationResult],
    pareto_indices: &[usize],
    balanced_idx: Option<usize>,
) {
    println!(
        "\n=== Pareto Frontier ({} non-dominated solutions) ===\n",
        pareto_indices.len()
    );

    // Sort frontier by SP for display (highest first)
    let mut sorted_indices: Vec<usize> = pareto_indices.to_vec();
    sorted_indices.sort_by(|&a, &b| {
        results[b]
            .avg_final_sp
            .partial_cmp(&results[a].avg_final_sp)
            .unwrap_or(std::cmp::Ordering::Equal)
    });

    for (display_rank, &idx) in sorted_indices.iter().enumerate() {
        let result = &results[idx];
        let is_balanced = balanced_idx == Some(idx);

        let label = if is_balanced {
            " ★ BALANCED (recommended)"
        } else {
            ""
        };

        println!(
            "#{}: SP={:.2} variety={:.1} balance={:.3} eff={:.3}{}",
            display_rank + 1,
            result.avg_final_sp,
            result.avg_variety_count,
            result.avg_balance_ratio,
            result.avg_delta_sp_per_100kcal,
            label
        );
        println!("    {}", result.knobs.display());
        println!();
    }

    if let Some(idx) = balanced_idx {
        println!("─────────────────────────────────────────────────────────────");
        println!("★ Balanced pick minimizes sacrifice across all metrics.");
        println!("  Use this unless you specifically want max SP or max variety.");
        println!(
            "  Knobs saved to JSON will use the balanced configuration (#{}).",
            sorted_indices.iter().position(|&i| i == idx).unwrap_or(0) + 1
        );
    }
}
