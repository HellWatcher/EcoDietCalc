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
        var stomachFoodItems = new Dictionary<string, FoodItem>(StringComparer.OrdinalIgnoreCase);
        if (stomach.Contents != null)
        {
            foreach (var entry in stomach.Contents)
            {
                var food = entry.Food;
                if (food == null) continue;
                var name = food.GetType().Name.Replace("Item", "");
                stomachCounts.TryGetValue(name, out var count);
                stomachCounts[name] = count + 1;
                // Keep a reference for nutritional data (any instance will do)
                stomachFoodItems.TryAdd(name, food);
            }
        }

        // Build foods array from TasteBuds.FoodToTaste (all known foods)
        var foods = new List<Dictionary<string, object>>();
        var exportedNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

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
                exportedNames.Add(foodName);
            }
        }

        // Add any stomach foods not already covered by FoodToTaste
        // (fixes gap where eaten foods aren't in TasteBuds yet)
        foreach (var kvp in stomachCounts)
        {
            if (exportedNames.Contains(kvp.Key))
                continue;

            var stomachCount = kvp.Value;
            float calories = 0f;
            int carbs = 0, protein = 0, fat = 0, vitamins = 0;

            if (stomachFoodItems.TryGetValue(kvp.Key, out var foodItem))
            {
                calories = foodItem.Calories;
                var nutrition = foodItem.Nutrition;
                carbs = (int)nutrition.Carbs;
                protein = (int)nutrition.Protein;
                fat = (int)nutrition.Fat;
                vitamins = (int)nutrition.Vitamins;
            }

            var entry = new Dictionary<string, object>
            {
                ["Name"] = kvp.Key,
                ["Calories"] = (int)calories,
                ["Carbs"] = carbs,
                ["Protein"] = protein,
                ["Fat"] = fat,
                ["Vitamins"] = vitamins,
                ["Tastiness"] = 99, // unknown — not in TasteBuds
                ["Stomach"] = stomachCount
            };
            foods.Add(entry);
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
