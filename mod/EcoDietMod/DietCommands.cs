using System;
using System.Linq;
using System.Text;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;
using Eco.Gameplay.Systems.Messaging.Chat.Commands;
using Eco.Shared.Localization;

namespace EcoDietMod;

/// <summary>
/// Chat commands that expose food/diet game data for the calling player.
/// All commands are read-only — they inspect state without modifying it.
/// </summary>
[ChatCommandHandler]
public static class DietCommands
{
    [ChatCommand("EcoDiet commands — view your stomach, nutrients, and cravings", "ecodiet")]
    public static void EcoDietRoot(User user)
    {
        user.MsgLocStr("EcoDiet commands: /ecodiet stomach, /ecodiet nutrients, /ecodiet cravings, /ecodiet taste, /ecodiet multipliers");
    }

    [ChatSubCommand("EcoDietRoot", "Show current stomach contents", "stomach")]
    public static void Stomach(User user)
    {
        var stomach = user.Stomach;
        var sb = new StringBuilder();

        sb.AppendLine($"--- Stomach ({stomach.Calories:F0}/{stomach.MaxCalories:F0} cal) ---");

        if (stomach.Contents == null || stomach.Contents.Count == 0)
        {
            sb.AppendLine("Empty.");
        }
        else
        {
            foreach (var entry in stomach.Contents)
            {
                var food = entry.Food;
                var name = food?.GetType().Name.Replace("Item", "") ?? "Unknown";
                var cal = food?.Calories ?? 0;
                sb.AppendLine($"  {name}: {cal:F0} cal (eaten at {entry.TimeEaten:F1})");
            }
        }

        user.MsgLocStr(sb.ToString());
    }

    [ChatSubCommand("EcoDietRoot", "Show current nutrient levels (carbs/protein/fat/vitamins)", "nutrients")]
    public static void Nutrients(User user)
    {
        var stomach = user.Stomach;
        var nutrients = stomach.Nutrients;
        var sb = new StringBuilder();

        sb.AppendLine("--- Nutrients ---");
        sb.AppendLine($"  Carbs:    {nutrients.Carbs:F1}");
        sb.AppendLine($"  Protein:  {nutrients.Protein:F1}");
        sb.AppendLine($"  Fat:      {nutrients.Fat:F1}");
        sb.AppendLine($"  Vitamins: {nutrients.Vitamins:F1}");
        sb.AppendLine($"  Total:    {nutrients.NutrientTotal():F1}");
        sb.AppendLine($"  Average:  {nutrients.NutrientAverage():F1}");

        user.MsgLocStr(sb.ToString());
    }

    [ChatSubCommand("EcoDietRoot", "Show current craving and craving multiplier", "cravings")]
    public static void Cravings(User user)
    {
        var stomach = user.Stomach;
        var sb = new StringBuilder();

        sb.AppendLine("--- Cravings ---");
        sb.AppendLine($"  Current craving: {stomach.Craving?.Name ?? "None"}");
        sb.AppendLine($"  Craving mult:    {stomach.CravingMult:F2}x");
        sb.AppendLine($"  Description:     {stomach.CravingMultDesc}");

        user.MsgLocStr(sb.ToString());
    }

    [ChatSubCommand("EcoDietRoot", "Show taste preferences for foods in your stomach", "taste")]
    public static void Taste(User user)
    {
        var stomach = user.Stomach;
        var tasteBuds = stomach.TasteBuds;
        var sb = new StringBuilder();

        sb.AppendLine("--- Taste Preferences ---");

        if (tasteBuds.Favorite != null)
            sb.AppendLine($"  Favorite: {tasteBuds.Favorite.GetType().Name.Replace("Item", "")}");

        if (tasteBuds.Worst != null)
            sb.AppendLine($"  Worst:    {tasteBuds.Worst.GetType().Name.Replace("Item", "")}");

        if (tasteBuds.FoodToTaste != null)
        {
            sb.AppendLine("  Known tastes:");
            foreach (var kvp in tasteBuds.FoodToTaste)
            {
                if (kvp.Value.Discovered)
                {
                    var foodName = kvp.Key.Name.Replace("Item", "");
                    sb.AppendLine($"    {foodName}: {kvp.Value.Preference} ({kvp.Value.TastinessMult:F2}x)");
                }
            }
        }

        user.MsgLocStr(sb.ToString());
    }

    [ChatSubCommand("EcoDietRoot", "Show all SP multipliers (variety, balanced diet, taste, craving, dinner party)", "multipliers")]
    public static void Multipliers(User user)
    {
        var stomach = user.Stomach;
        var sb = new StringBuilder();

        sb.AppendLine("--- SP Multipliers ---");
        sb.AppendLine($"  Nutrient SP rate:   {stomach.NutrientSkillRate():F2}");
        sb.AppendLine($"  Balanced diet:      {stomach.BalancedDietMult:F2}x");
        sb.AppendLine($"  Variety:            {stomach.VarietyMult:F2}x");
        sb.AppendLine($"  Tastiness:          {stomach.TastinessMult:F2}x");
        sb.AppendLine($"  Craving:            {stomach.CravingMult:F2}x");
        sb.AppendLine($"  Dinner party:       {stomach.DinnerPartyMult:F2}x");
        sb.AppendLine($"  Calorie mult:       {stomach.CalorieMult:F2}x");

        user.MsgLocStr(sb.ToString());
    }
}
