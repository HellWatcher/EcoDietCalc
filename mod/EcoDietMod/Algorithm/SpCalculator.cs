using System;
using System.Collections.Generic;
using System.Linq;
using EcoDietMod.Config;
using EcoDietMod.Models;

namespace EcoDietMod.Algorithm;

/// <summary>
/// Pure SP calculation functions ported from calculations.py.
/// All methods are static and side-effect free.
/// </summary>
public static class SpCalculator
{
    // --- Nutrient aggregation ---

    /// <summary>
    /// Calorie-weighted nutrient densities and total calories for a stomach.
    /// Returns (densityDict, totalCalories) where densityDict has keys: carbs, protein, fat, vitamins.
    /// </summary>
    public static (NutrientDensity Density, float TotalCalories) SumAllWeightedNutrients(
        Dictionary<FoodCandidate, int> stomach)
    {
        var totalCal = TotalCalories(stomach);
        var density = new NutrientDensity();
        if (totalCal <= 0f) return (density, 0f);

        foreach (var (food, quantity) in stomach)
        {
            var calorieWeight = (food.Calories * quantity) / totalCal;
            density.Carbs += food.Carbs * calorieWeight;
            density.Protein += food.Protein * calorieWeight;
            density.Fat += food.Fat * calorieWeight;
            density.Vitamins += food.Vitamins * calorieWeight;
        }

        return (density, totalCal);
    }

    /// <summary>Total calories in the stomach.</summary>
    public static float TotalCalories(Dictionary<FoodCandidate, int> stomach)
    {
        float total = 0f;
        foreach (var (food, quantity) in stomach)
            total += food.Calories * quantity;
        return total;
    }

    // --- Balanced diet ---

    /// <summary>
    /// Balance ratio: min_nonzero / max among the four nutrient values.
    /// Returns value in [0, 1]; higher means more balanced.
    /// </summary>
    public static float CalculateBalancedDietRatio(float[] nutrients)
    {
        var max = nutrients.Max();
        if (max <= 0f) return 0f;
        var minPositive = float.MaxValue;
        foreach (var n in nutrients)
        {
            if (n > 0f && n < minPositive) minPositive = n;
        }
        return minPositive == float.MaxValue ? 0f : minPositive / max;
    }

    /// <summary>
    /// Balanced diet bonus in percentage points: (ratio * 100) - 50.
    /// Range: [-50, +50].
    /// </summary>
    public static float CalculateBalancedDietBonus(float[] nutrients)
    {
        return (CalculateBalancedDietRatio(nutrients) * 100f) - 50f;
    }

    // --- Tastiness ---

    /// <summary>
    /// Tastiness bonus in percentage points for the current stomach.
    /// Calorie-weighted average of tastiness multipliers, scaled by config weight.
    /// </summary>
    public static float GetTastinessBonus(
        Dictionary<FoodCandidate, int> stomach,
        PlannerConfig config)
    {
        var totalCal = TotalCalories(stomach);
        if (totalCal <= 0f) return 0f;

        float tasteScore = 0f;
        foreach (var (food, quantity) in stomach)
        {
            PlannerConfig.TastinessMultipliers.TryGetValue(food.Tastiness, out var mult);
            tasteScore += mult * food.Calories * quantity;
        }

        return (tasteScore / totalCal) * 100f * config.TastinessWeight;
    }

    /// <summary>
    /// Change in tastiness bonus from adding one unit of a food.
    /// </summary>
    public static float TastinessDeltaForAddedUnit(
        Dictionary<FoodCandidate, int> stomach,
        FoodCandidate food,
        PlannerConfig config)
    {
        var before = GetTastinessBonus(stomach, config);
        var after = GetTastinessBonus(SimulateStomachWithAddedFood(stomach, food), config);
        return after - before;
    }

    // --- Variety ---

    /// <summary>
    /// Variety bonus from the number of qualifying foods.
    /// Exponential cap: each +20 qualifying foods halves the remaining gap.
    /// </summary>
    public static float GetVarietyBonus(int uniqueFoodCount, PlannerConfig config)
    {
        return config.VarietyBonusCapPp * (1f - MathF.Pow(0.5f, uniqueFoodCount / 20f));
    }

    /// <summary>Whether this food meets the variety calorie threshold at the given quantity.</summary>
    public static bool IsVarietyQualifying(FoodCandidate food, int quantity, PlannerConfig config)
    {
        return (food.Calories * quantity) >= config.VarietyCalThreshold;
    }

    /// <summary>Fractional variety contribution in [0, 1].</summary>
    public static float VarietyFractionFor(FoodCandidate food, int quantity, PlannerConfig config)
    {
        if (quantity <= 0) return 0f;
        return MathF.Min(1f, (food.Calories * quantity) / (float)config.VarietyCalThreshold);
    }

    /// <summary>Count of foods that individually meet the variety threshold.</summary>
    public static int VarietyCount(Dictionary<FoodCandidate, int> stomach, PlannerConfig config)
    {
        int count = 0;
        foreach (var (food, quantity) in stomach)
        {
            if (IsVarietyQualifying(food, quantity, config))
                count++;
        }
        return count;
    }

    /// <summary>Sum of fractional variety contributions (can be non-integer).</summary>
    public static float SoftVarietyCount(Dictionary<FoodCandidate, int> stomach, PlannerConfig config)
    {
        float sum = 0f;
        foreach (var (food, quantity) in stomach)
            sum += VarietyFractionFor(food, quantity, config);
        return sum;
    }

    /// <summary>Set of lowercased food names that meet the variety threshold.</summary>
    public static HashSet<string> UniqueVarietyNames(
        Dictionary<FoodCandidate, int> stomach,
        PlannerConfig config)
    {
        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var (food, quantity) in stomach)
        {
            if (IsVarietyQualifying(food, quantity, config))
                names.Add(food.Name);
        }
        return names;
    }

    // --- SP calculation ---

    /// <summary>
    /// Total nutrition multiplier (percentage points).
    /// Includes balanced diet, variety, and tastiness bonuses.
    /// </summary>
    public static float CalculateNutritionMultiplier(
        Dictionary<FoodCandidate, int> stomach,
        HashSet<string> uniqueFoods24h,
        PlannerConfig config)
    {
        var (density, _) = SumAllWeightedNutrients(stomach);
        var nutrients = new[] { density.Carbs, density.Protein, density.Fat, density.Vitamins };

        var balancedDietPp = CalculateBalancedDietBonus(nutrients);
        var varietyPp = GetVarietyBonus(uniqueFoods24h.Count, config);
        var tastinessPp = GetTastinessBonus(stomach, config);

        return balancedDietPp + varietyPp + tastinessPp;
    }

    /// <summary>
    /// Compute SP from stomach and bonuses.
    /// Formula: ((nutrient_sp * bonuses * dinner_party) + BASE_SP) * server_mult
    /// </summary>
    public static float GetSp(
        Dictionary<FoodCandidate, int> stomach,
        int cravingsSatisfied,
        HashSet<string> uniqueFoods24h,
        PlannerConfig config,
        float serverMult = 1f,
        float dinnerPartyMult = 1f)
    {
        var (density, _) = SumAllWeightedNutrients(stomach);
        var densitySum = density.Carbs + density.Protein + density.Fat + density.Vitamins;

        var bonus = CalculateNutritionMultiplier(stomach, uniqueFoods24h, config) / 100f;
        bonus += cravingsSatisfied * config.CravingSatisfiedFrac;

        var nutritionSp = densitySum * (1f + bonus) * dinnerPartyMult;
        return (nutritionSp + config.BaseSkillPoints) * serverMult;
    }

    // --- Simulation helpers ---

    /// <summary>
    /// Clone the stomach and add one unit of the given food.
    /// </summary>
    public static Dictionary<FoodCandidate, int> SimulateStomachWithAddedFood(
        Dictionary<FoodCandidate, int> stomach,
        FoodCandidate food)
    {
        var clone = new Dictionary<FoodCandidate, int>(stomach);
        clone.TryGetValue(food, out var current);
        clone[food] = current + 1;
        return clone;
    }

    /// <summary>
    /// Estimate nutrition multiplier after hypothetically adding a food.
    /// </summary>
    public static float EvaluateBonusWithAddition(
        Dictionary<FoodCandidate, int> stomach,
        FoodCandidate food,
        HashSet<string> varietyReference,
        PlannerConfig config)
    {
        var testStomach = SimulateStomachWithAddedFood(stomach, food);
        var newTotal = food.Calories * testStomach[food];

        HashSet<string> updatedVariety;
        if (newTotal >= config.VarietyCalThreshold
            && !varietyReference.Contains(food.Name))
        {
            updatedVariety = new HashSet<string>(varietyReference, StringComparer.OrdinalIgnoreCase)
            {
                food.Name
            };
        }
        else
        {
            updatedVariety = varietyReference;
        }

        return CalculateNutritionMultiplier(testStomach, updatedVariety, config);
    }

    /// <summary>
    /// Change in SP from adding one unit of a specific food.
    /// </summary>
    public static float GetSpDelta(
        FoodCandidate food,
        Dictionary<FoodCandidate, int> stomach,
        int cravingsSatisfied,
        PlannerConfig config,
        float serverMult = 1f,
        float dinnerPartyMult = 1f)
    {
        var after = SimulateStomachWithAddedFood(stomach, food);
        var spAfter = GetSp(after, cravingsSatisfied,
            UniqueVarietyNames(after, config), config, serverMult, dinnerPartyMult);
        var spBefore = GetSp(stomach, cravingsSatisfied,
            UniqueVarietyNames(stomach, config), config, serverMult, dinnerPartyMult);
        return spAfter - spBefore;
    }

    /// <summary>
    /// Balance ratio for the current stomach.
    /// </summary>
    public static float GetBalancedDietRatio(Dictionary<FoodCandidate, int> stomach)
    {
        var (density, _) = SumAllWeightedNutrients(stomach);
        var nutrients = new[] { density.Carbs, density.Protein, density.Fat, density.Vitamins };
        return CalculateBalancedDietRatio(nutrients);
    }

    /// <summary>
    /// Sum of weighted nutrients (nutrient density sum).
    /// </summary>
    public static float NutrientSum(Dictionary<FoodCandidate, int> stomach)
    {
        var (density, _) = SumAllWeightedNutrients(stomach);
        return density.Carbs + density.Protein + density.Fat + density.Vitamins;
    }
}

/// <summary>
/// Mutable struct for accumulating weighted nutrient densities.
/// </summary>
public struct NutrientDensity
{
    public float Carbs;
    public float Protein;
    public float Fat;
    public float Vitamins;
}
