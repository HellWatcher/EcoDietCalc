using System.Collections.Generic;

namespace EcoDietMod.Config;

/// <summary>
/// Algorithm constants for the meal planner. Defaults match config.default.yml exactly.
/// Passed explicitly to all algorithm functions (no static globals).
/// </summary>
public sealed class PlannerConfig
{
    // --- Algorithm parameters ---

    /// <summary>Strength of the soft-variety ranking bias.</summary>
    public float SoftVarietyBiasStrength { get; init; } = 3.61f;

    /// <summary>Tie-break window (in SP) for near-equal candidates.</summary>
    public float TiebreakScoreWindowSp { get; init; } = 0.449f;

    /// <summary>Proximity weight toward the variety calorie threshold.</summary>
    public float ProximityApproachWeight { get; init; } = 0.977f;

    /// <summary>Small penalty when already past 1.0 progress toward variety threshold.</summary>
    public float ProximityOvershootPenalty { get; init; } = 0.076f;

    /// <summary>Calories below this threshold incur quadratic penalty.</summary>
    public int LowCalorieThreshold { get; init; } = 395;

    /// <summary>Strength of the low-calorie penalty (>= 1; higher = harsher).</summary>
    public float LowCaloriePenaltyStrength { get; init; } = 2.48f;

    /// <summary>Strength of the balance-improvement bias for filling nutrient gaps.</summary>
    public float BalancedDietImprovementStrength { get; init; } = 1.91f;

    /// <summary>Asymptotic cap for variety bonus (percentage points).</summary>
    public float VarietyBonusCapPp { get; init; } = 55.0f;

    /// <summary>Weight applied to tastiness bonus.</summary>
    public float TastinessWeight { get; init; } = 1.0f;

    // --- Game rules ---

    /// <summary>Calories required per food for variety bonus eligibility.</summary>
    public int VarietyCalThreshold { get; init; } = 2000;

    /// <summary>SP multiplier fraction per satisfied craving.</summary>
    public float CravingSatisfiedFrac { get; init; } = 0.10f;

    // --- Safety ---

    /// <summary>Maximum food additions in a single planning loop.</summary>
    public int MaxIterations { get; init; } = 100;

    /// <summary>Default base SP points.</summary>
    public float BaseSkillPoints { get; init; } = 12f;

    // --- Tastiness multipliers (fraction, e.g. +0.20 = +20pp before weighting) ---

    public static readonly IReadOnlyDictionary<int, float> TastinessMultipliers =
        new Dictionary<int, float>
        {
            [-3] = -0.30f,
            [-2] = -0.20f,
            [-1] = -0.10f,
            [0] = 0.00f,
            [1] = 0.10f,
            [2] = 0.20f,
            [3] = 0.30f,
            [99] = 0.00f  // unknown
        };

    public static readonly IReadOnlyDictionary<int, string> TastinessNames =
        new Dictionary<int, string>
        {
            [-3] = "worst",
            [-2] = "horrible",
            [-1] = "bad",
            [0] = "ok",
            [1] = "good",
            [2] = "delicious",
            [3] = "favorite",
            [99] = "unknown"
        };
}
