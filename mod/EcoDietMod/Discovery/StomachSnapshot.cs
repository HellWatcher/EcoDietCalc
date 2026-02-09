using System;
using System.Collections.Generic;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;
using EcoDietMod.Models;

namespace EcoDietMod.Discovery;

/// <summary>
/// Reads the player's current Stomach state into planner-compatible dictionaries.
/// Follows the same Eco API patterns as GameStateExporter.cs.
/// </summary>
public static class StomachSnapshot
{
    /// <summary>
    /// Capture the current stomach contents as a FoodCandidate -> count dictionary.
    /// </summary>
    public static Dictionary<FoodCandidate, int> CaptureStomach(User user)
    {
        var stomach = user.Stomach;
        var result = new Dictionary<FoodCandidate, int>();

        if (stomach.Contents == null)
            return result;

        foreach (var entry in stomach.Contents)
        {
            var foodItem = entry.Food;
            if (foodItem == null) continue;

            var candidate = FoodItemToCandidate(foodItem, stomach.TasteBuds);
            if (candidate == null) continue;

            result.TryGetValue(candidate, out var count);
            result[candidate] = count + 1;
        }

        return result;
    }

    /// <summary>
    /// Get remaining calorie budget (max - current).
    /// </summary>
    public static int GetRemainingCalories(User user)
    {
        var stomach = user.Stomach;
        return (int)Math.Max(0, stomach.MaxCalories - stomach.Calories);
    }

    /// <summary>
    /// Get max calories for the player's stomach.
    /// </summary>
    public static int GetMaxCalories(User user)
    {
        return (int)user.Stomach.MaxCalories;
    }

    /// <summary>
    /// Get current calorie fill.
    /// </summary>
    public static int GetCurrentCalories(User user)
    {
        return (int)user.Stomach.Calories;
    }

    /// <summary>
    /// Get the current craving food name, or null if none.
    /// </summary>
    public static string? GetCurrentCraving(User user)
    {
        var craving = user.Stomach.Craving;
        return craving?.Name?.Replace("Item", "");
    }

    /// <summary>
    /// Get the number of cravings satisfied (parsed from CravingMultDesc).
    /// Returns 0 if unable to parse.
    /// </summary>
    public static int GetCravingsSatisfied(User user)
    {
        // CravingMult is (1 + satisfied_count * 0.10), so:
        // satisfied_count = (CravingMult - 1) / 0.10
        var mult = user.Stomach.CravingMult;
        if (mult <= 1f) return 0;
        return (int)Math.Round((mult - 1f) / 0.10f);
    }

    /// <summary>
    /// Get the dinner party multiplier.
    /// </summary>
    public static float GetDinnerPartyMult(User user)
    {
        return user.Stomach.DinnerPartyMult;
    }

    /// <summary>
    /// Convert an Eco FoodItem to a FoodCandidate using TasteBuds for tastiness.
    /// </summary>
    public static FoodCandidate? FoodItemToCandidate(FoodItem foodItem, TasteBuds tasteBuds)
    {
        var name = foodItem.GetType().Name.Replace("Item", "");
        var calories = (int)foodItem.Calories;
        var nutrition = foodItem.Nutrition;
        var carbs = (int)nutrition.Carbs;
        var protein = (int)nutrition.Protein;
        var fat = (int)nutrition.Fat;
        var vitamins = (int)nutrition.Vitamins;

        // Map tastiness via TasteBuds
        var tastiness = 99; // unknown default
        if (tasteBuds?.FoodToTaste != null)
        {
            var foodType = foodItem.GetType();
            if (tasteBuds.FoodToTaste.TryGetValue(foodType, out var taste))
            {
                tastiness = GameStateExporter.MapTastePreference(taste);
            }
        }

        return new FoodCandidate(name, calories, carbs, protein, fat, vitamins, tastiness);
    }
}
