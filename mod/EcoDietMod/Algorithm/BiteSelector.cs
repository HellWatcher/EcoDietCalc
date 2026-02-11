using System;
using System.Collections.Generic;
using EcoDietMod.Config;
using EcoDietMod.Models;

namespace EcoDietMod.Algorithm;

/// <summary>
/// Ranking pipeline for selecting the next bite.
/// Ported from planner.py bias/penalty helpers and _choose_next_bite.
/// All methods are static and side-effect free.
/// </summary>
public static class BiteSelector
{
    /// <summary>
    /// Quadratic penalty for foods below the calorie floor.
    /// Returns non-positive value (0 if at/above threshold).
    /// </summary>
    public static float LowCaloriePenalty(FoodCandidate food, PlannerConfig config)
    {
        if (food.Calories >= config.LowCalorieThreshold)
            return 0f;
        var deficitRatio = 1f - (food.Calories / (float)config.LowCalorieThreshold);
        return -config.LowCaloriePenaltyStrength * deficitRatio * deficitRatio;
    }

    /// <summary>
    /// Bias based on change in soft-variety bonus if one unit is added.
    /// Soft-variety delta (pp) scaled by post-bite nutrient density.
    /// </summary>
    public static float SoftVarietyBias(
        Dictionary<FoodCandidate, int> stomach,
        FoodCandidate food,
        PlannerConfig config)
    {
        var softBefore = SpCalculator.SoftVarietyCount(stomach, config);
        var afterStomach = SpCalculator.SimulateStomachWithAddedFood(stomach, food);
        var softAfter = SpCalculator.SoftVarietyCount(afterStomach, config);

        // Use fractional variety counts for continuous bonus, matching Python logic
        var varietyDeltaPp = GetVarietyBonus(softAfter, config)
                           - GetVarietyBonus(softBefore, config);

        var nutrientSumAfter = SpCalculator.NutrientSum(afterStomach);
        return config.SoftVarietyBiasStrength * nutrientSumAfter * (varietyDeltaPp / 100f);
    }

    /// <summary>
    /// Tie-break bias for moving toward (or overshooting) the per-food variety target.
    /// Positive when the bite moves closer; small negative if it overshoots.
    /// </summary>
    public static float ProximityBias(
        Dictionary<FoodCandidate, int> stomach,
        FoodCandidate food,
        PlannerConfig config)
    {
        stomach.TryGetValue(food, out var countBefore);
        var progressBefore = (food.Calories * countBefore) / (float)config.VarietyCalThreshold;
        var progressAfter = (food.Calories * (countBefore + 1)) / (float)config.VarietyCalThreshold;

        var growthTowardThreshold = MathF.Max(0f,
            MathF.Min(1f, progressAfter) - MathF.Min(1f, progressBefore));
        var overshootAmount = MathF.Max(0f, progressAfter - 1f);

        var overshootRatio = config.ProximityApproachWeight > 0f
            ? config.ProximityOvershootPenalty / config.ProximityApproachWeight
            : 0f;

        var proximityScore = growthTowardThreshold - overshootAmount * overshootRatio;
        return config.ProximityApproachWeight * proximityScore;
    }

    /// <summary>
    /// Select the next best bite by ranking.
    /// Filters by feasibility, scores by SP delta + penalties/biases,
    /// then applies soft-variety primary rank and proximity tie-break.
    /// Returns (bestFood, rawSpDelta) or (null, 0) if nothing fits.
    /// </summary>
    public static (FoodCandidate? Food, float RawDelta) ChooseNextBite(
        Dictionary<FoodCandidate, int> stomach,
        IEnumerable<FoodCandidate> availableFoods,
        float remainingCalories,
        int cravingsSatisfied,
        PlannerConfig config,
        float serverMult = 1f,
        float dinnerPartyMult = 1f)
    {
        var candidates = new List<(FoodCandidate Food, float RawDelta, float RankScore)>();
        FoodCandidate? bestFood = null;
        var bestRankScore = float.NegativeInfinity;
        var bestRawDelta = 0f;

        // Pass 1: raw SP delta + low-calorie penalty
        foreach (var food in availableFoods)
        {
            // Skip zero-calorie items (seeds, spores) — no nutritional value
            if (food.Calories <= 0f)
                continue;
            if (food.Calories > remainingCalories)
                continue;

            var rawDelta = SpCalculator.GetSpDelta(food, stomach, cravingsSatisfied,
                config, serverMult, dinnerPartyMult);
            var rankScore = rawDelta + LowCaloriePenalty(food, config);
            candidates.Add((food, rawDelta, rankScore));

            if (rankScore > bestRankScore)
            {
                bestRankScore = rankScore;
                bestFood = food;
                bestRawDelta = rawDelta;
            }
        }

        if (candidates.Count == 0)
            return (null, 0f);

        // Pass 2: keep near-equals within tiebreak window
        var nearCandidates = new List<(FoodCandidate Food, float RawDelta, float RankScore)>();
        foreach (var c in candidates)
        {
            if ((bestRankScore - c.RankScore) <= config.TiebreakScoreWindowSp)
                nearCandidates.Add(c);
        }

        // Pass 3: soft-variety as primary rank, proximity as tie-break
        var scored = new List<(FoodCandidate Food, float RawDelta, float PrimaryRank, float ProximityScore)>();
        foreach (var (food, rawDelta, rankScore) in nearCandidates)
        {
            var softBias = SoftVarietyBias(stomach, food, config);
            var proxBias = ProximityBias(stomach, food, config);
            var primaryRank = rawDelta + LowCaloriePenalty(food, config) + softBias;
            scored.Add((food, rawDelta, primaryRank, proxBias));
        }

        if (scored.Count == 0)
            return (bestFood, bestRawDelta);

        // Sort by (primaryRank, proximityBias) ascending; pick last (highest)
        scored.Sort((a, b) =>
        {
            var cmp = a.PrimaryRank.CompareTo(b.PrimaryRank);
            return cmp != 0 ? cmp : a.ProximityScore.CompareTo(b.ProximityScore);
        });

        var winner = scored[^1];
        return (winner.Food, winner.RawDelta);
    }

    /// <summary>
    /// Return the best craving food that can be eaten now (highest SP delta).
    /// Returns null if no craving food is feasible.
    /// </summary>
    public static FoodCandidate? PickFeasibleCraving(
        Dictionary<FoodCandidate, int> stomach,
        Dictionary<FoodCandidate, int> available,
        List<string> cravings,
        float remainingCalories,
        int cravingsSatisfied,
        PlannerConfig config,
        float serverMult = 1f,
        float dinnerPartyMult = 1f)
    {
        var cravingsSet = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var name in cravings)
            cravingsSet.Add(name.Trim());

        FoodCandidate? best = null;
        var bestDelta = float.NegativeInfinity;

        foreach (var (food, qty) in available)
        {
            if (qty <= 0 || food.Calories <= 0f || food.Calories > remainingCalories)
                continue;
            if (!cravingsSet.Contains(food.Name))
                continue;

            var delta = SpCalculator.GetSpDelta(food, stomach, cravingsSatisfied,
                config, serverMult, dinnerPartyMult);
            if (delta > bestDelta)
            {
                bestDelta = delta;
                best = food;
            }
        }

        return best;
    }

    /// <summary>
    /// Overload of GetVarietyBonus that accepts a float count for soft variety.
    /// </summary>
    private static float GetVarietyBonus(float softCount, PlannerConfig config)
    {
        return config.VarietyBonusCapPp * (1f - MathF.Pow(0.5f, softCount / 20f));
    }
}
