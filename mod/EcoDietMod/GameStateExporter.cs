using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;

namespace EcoDietMod;

/// <summary>
/// Exports the player's food/diet game state to a JSON file
/// that the Python planner can consume via <c>--import</c>.
/// </summary>
public static class GameStateExporter
{
    /// <summary>
    /// Build a snapshot of the player's diet state and write it to
    /// <paramref name="path"/> as pretty-printed JSON.
    /// </summary>
    public static void ExportGameState(User user, string path, string note)
    {
        var stomach = user.Stomach;
        var tasteBuds = stomach.TasteBuds;

        // Count stomach bites per food type name
        var stomachCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        if (stomach.Contents != null)
        {
            foreach (var entry in stomach.Contents)
            {
                var name = entry.Food?.GetType().Name.Replace("Item", "") ?? "Unknown";
                stomachCounts.TryGetValue(name, out var count);
                stomachCounts[name] = count + 1;
            }
        }

        // Build foods array from TasteBuds.FoodToTaste (all known foods)
        var foods = new List<Dictionary<string, object>>();
        if (tasteBuds.FoodToTaste != null)
        {
            foreach (var kvp in tasteBuds.FoodToTaste)
            {
                var foodType = kvp.Key;
                var taste = kvp.Value;
                var foodName = foodType.Name.Replace("Item", "");

                // Get a FoodItem instance for nutritional data
                var foodItem = Item.Get(foodType) as FoodItem;
                var calories = foodItem?.Calories ?? 0f;
                var nutrition = foodItem?.Nutrition;

                stomachCounts.TryGetValue(foodName, out var stomachCount);

                var entry = new Dictionary<string, object>
                {
                    ["Name"] = foodName,
                    ["Calories"] = (int)calories,
                    ["Carbs"] = (int)(nutrition?.Carbs ?? 0),
                    ["Protein"] = (int)(nutrition?.Protein ?? 0),
                    ["Fat"] = (int)(nutrition?.Fat ?? 0),
                    ["Vitamins"] = (int)(nutrition?.Vitamins ?? 0),
                    ["Tastiness"] = MapTastePreference(taste),
                    ["Stomach"] = stomachCount
                };
                foods.Add(entry);
            }
        }

        // Assemble the full export object
        var export = new Dictionary<string, object>
        {
            ["ExportedAt"] = DateTime.UtcNow.ToString("o"),
            ["PlayerName"] = user.Name,
            ["Note"] = note,
            ["Calories"] = new Dictionary<string, object>
            {
                ["Current"] = Math.Round(stomach.Calories, 1),
                ["Max"] = Math.Round(stomach.MaxCalories, 1)
            },
            ["Cravings"] = new Dictionary<string, object>
            {
                ["Current"] = stomach.Craving?.Name ?? "None",
                ["Multiplier"] = Math.Round(stomach.CravingMult, 2),
                ["Description"] = stomach.CravingMultDesc ?? ""
            },
            ["Multipliers"] = new Dictionary<string, object>
            {
                ["BalancedDiet"] = Math.Round(stomach.BalancedDietMult, 2),
                ["Variety"] = Math.Round(stomach.VarietyMult, 2),
                ["Tastiness"] = Math.Round(stomach.TastinessMult, 2),
                ["Craving"] = Math.Round(stomach.CravingMult, 2),
                ["DinnerParty"] = Math.Round(stomach.DinnerPartyMult, 2),
                ["Calorie"] = Math.Round(stomach.CalorieMult, 2),
                ["NutrientSkillRate"] = Math.Round(stomach.NutrientSkillRate(), 2)
            },
            ["Foods"] = foods
        };

        var options = new JsonSerializerOptions
        {
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.Never
        };
        var json = JsonSerializer.Serialize(export, options);
        File.WriteAllText(path, json);
    }

    /// <summary>
    /// Map the Eco <see cref="ItemTaste"/> to a -3..+3 integer.
    /// Undiscovered foods return 99 (the Python planner's "unknown" sentinel).
    /// </summary>
    public static int MapTastePreference(ItemTaste taste)
    {
        if (!taste.Discovered)
            return 99;

        return taste.Preference switch
        {
            ItemTaste.TastePreference.Worst     => -3,
            ItemTaste.TastePreference.Horrible  => -2,
            ItemTaste.TastePreference.Bad       => -1,
            ItemTaste.TastePreference.Ok        =>  0,
            ItemTaste.TastePreference.Good      =>  1,
            ItemTaste.TastePreference.Delicious =>  2,
            ItemTaste.TastePreference.Favorite  =>  3,
            _                        =>  0
        };
    }
}
