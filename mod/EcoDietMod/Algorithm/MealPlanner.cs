using System;
using System.Collections.Generic;
using System.Linq;
using EcoDietMod.Config;
using EcoDietMod.Models;

namespace EcoDietMod.Algorithm;

/// <summary>
/// Main meal planning loop. Ported from planner.py plan_meal / _apply_bite.
/// Takes stomach and available food as dictionaries (no FoodStateManager).
/// </summary>
public static class MealPlanner
{
    /// <summary>
    /// Plan a sequence of bites under the current constraints.
    /// </summary>
    /// <param name="stomach">Current stomach contents (food -> count). Will be mutated.</param>
    /// <param name="available">Available food (food -> count). Will be mutated as foods are consumed.</param>
    /// <param name="cravings">Active cravings (case-insensitive names). Will be mutated as cravings are satisfied.</param>
    /// <param name="cravingsSatisfied">Number of cravings already satisfied today.</param>
    /// <param name="remainingCalories">Calorie budget for this plan.</param>
    /// <param name="config">Planner configuration.</param>
    /// <param name="serverMult">Server skill gain multiplier.</param>
    /// <param name="dinnerPartyMult">Dinner party multiplier.</param>
    public static MealPlanResult PlanMeal(
        Dictionary<FoodCandidate, int> stomach,
        Dictionary<FoodCandidate, int> available,
        List<string> cravings,
        int cravingsSatisfied,
        float remainingCalories,
        PlannerConfig config,
        float serverMult = 1f,
        float dinnerPartyMult = 1f)
    {
        // Normalize cravings (lowercase + trim), matching Python's plan_meal
        for (var c = 0; c < cravings.Count; c++)
            cravings[c] = cravings[c].Trim().ToLowerInvariant();

        var startingSp = SpCalculator.GetSp(stomach, cravingsSatisfied,
            SpCalculator.UniqueVarietyNames(stomach, config), config, serverMult, dinnerPartyMult);
        var currentSp = startingSp;
        var varietyCountNow = SpCalculator.VarietyCount(stomach, config);
        var items = new List<MealPlanItem>();
        var startCalories = remainingCalories;

        for (var i = 0; i < config.MaxIterations; i++)
        {
            if (remainingCalories <= 0)
                break;

            // Build list of foods that have availability
            var availableFoods = GetAvailableFoods(available);

            // Craving-first if feasible, else ranked best
            var food = BiteSelector.PickFeasibleCraving(
                stomach, available, cravings, remainingCalories,
                cravingsSatisfied, config, serverMult, dinnerPartyMult);

            if (food is null)
            {
                (food, _) = BiteSelector.ChooseNextBite(
                    stomach, availableFoods, remainingCalories,
                    cravingsSatisfied, config, serverMult, dinnerPartyMult);

                if (food is null)
                    break;
            }

            // Apply the bite
            (currentSp, remainingCalories, cravingsSatisfied, varietyCountNow) = ApplyBite(
                stomach, available, food, cravings, items,
                currentSp, remainingCalories, cravingsSatisfied, varietyCountNow,
                config, serverMult, dinnerPartyMult);
        }

        return new MealPlanResult
        {
            Items = items,
            StartingSp = startingSp,
            FinalSp = currentSp,
            TotalCalories = startCalories - remainingCalories,
            RemainingCalories = remainingCalories,
            VarietyCount = varietyCountNow,
            CravingsSatisfied = cravingsSatisfied
        };
    }

    /// <summary>
    /// Consume one unit of food, recompute SP/bonuses, append to plan items.
    /// Returns updated (currentSp, remainingCalories, cravingsSatisfied, varietyCount).
    /// </summary>
    private static (float CurrentSp, float RemainingCalories, int CravingsSatisfied, int VarietyCount)
        ApplyBite(
            Dictionary<FoodCandidate, int> stomach,
            Dictionary<FoodCandidate, int> available,
            FoodCandidate food,
            List<string> cravings,
            List<MealPlanItem> items,
            float currentSp,
            float remainingCalories,
            int cravingsSatisfied,
            int varietyCountNow,
            PlannerConfig config,
            float serverMult,
            float dinnerPartyMult)
    {
        var beforeSp = currentSp;
        var tastinessDelta = SpCalculator.TastinessDeltaForAddedUnit(stomach, food, config);

        // Consume: add to stomach, remove from available
        stomach.TryGetValue(food, out var stomachCount);
        stomach[food] = stomachCount + 1;

        available.TryGetValue(food, out var availCount);
        if (availCount > 1)
            available[food] = availCount - 1;
        else
            available.Remove(food);

        remainingCalories -= food.Calories;

        // Check craving satisfaction (cravings are already normalized in PlanMeal)
        var satisfied = false;
        var foodName = food.Name.ToLowerInvariant();
        for (var j = 0; j < cravings.Count; j++)
        {
            if (string.Equals(cravings[j], foodName, StringComparison.OrdinalIgnoreCase))
            {
                cravings.RemoveAt(j);
                cravingsSatisfied++;
                satisfied = true;
                break;
            }
        }

        // Recompute SP
        var uniqueVariety = SpCalculator.UniqueVarietyNames(stomach, config);
        currentSp = SpCalculator.GetSp(stomach, cravingsSatisfied,
            uniqueVariety, config, serverMult, dinnerPartyMult);

        var newVarietyCount = SpCalculator.VarietyCount(stomach, config);
        var varietyDelta = SpCalculator.GetVarietyBonus(newVarietyCount, config)
                         - SpCalculator.GetVarietyBonus(varietyCountNow, config);

        items.Add(new MealPlanItem
        {
            Name = food.Name,
            Calories = food.Calories,
            SpGain = currentSp - beforeSp,
            NewSp = currentSp,
            Craving = satisfied,
            VarietyDeltaPp = varietyDelta,
            TastinessDeltaPp = tastinessDelta
        });

        return (currentSp, remainingCalories, cravingsSatisfied, newVarietyCount);
    }

    /// <summary>
    /// Get all foods with positive availability.
    /// </summary>
    private static List<FoodCandidate> GetAvailableFoods(Dictionary<FoodCandidate, int> available)
    {
        var foods = new List<FoodCandidate>();
        foreach (var (food, qty) in available)
        {
            if (qty > 0) foods.Add(food);
        }
        return foods;
    }
}
