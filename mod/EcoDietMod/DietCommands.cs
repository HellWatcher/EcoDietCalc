using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;
using Eco.Gameplay.Systems.Messaging.Chat.Commands;
using Eco.Shared.Localization;
using EcoDietMod.Algorithm;
using EcoDietMod.Config;
using EcoDietMod.Discovery;
using EcoDietMod.Models;
using EcoDietMod.Rendering;

namespace EcoDietMod;

/// <summary>
/// Chat commands that expose food/diet game data for the calling player.
/// Read-only inspection commands plus the in-game meal planner.
/// </summary>
[ChatCommandHandler]
public static class DietCommands
{
    [ChatCommand("EcoDiet commands — view your stomach, nutrients, cravings, plan meals, and export state", "ecodiet")]
    public static void EcoDietRoot(User user)
    {
        user.MsgLocStr(
            "EcoDiet commands: /ecodiet stomach, /ecodiet nutrients, /ecodiet cravings, " +
            "/ecodiet taste, /ecodiet multipliers, /ecodiet plan, /ecodiet fullplan, /ecodiet export");
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

    [ChatSubCommand("EcoDietRoot", "Plan optimal meal for remaining calorie budget (from backpack)", "plan")]
    public static void Plan(User user, int calories = 0)
    {
        try
        {
            var config = new PlannerConfig();
            var stomachState = StomachSnapshot.CaptureStomach(user);
            var (available, sources) = FoodDiscovery.DiscoverAll(user);

            if (available.Count == 0)
            {
                user.MsgLocStr("No food found in your backpack to plan with.");
                return;
            }

            var remainingCal = calories > 0
                ? calories
                : StomachSnapshot.GetRemainingCalories(user);

            if (remainingCal <= 0)
            {
                user.MsgLocStr("No calorie budget remaining. Stomach is full.");
                return;
            }

            var cravings = BuildCravingsList(user);
            var cravingsSatisfied = StomachSnapshot.GetCravingsSatisfied(user);
            var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);

            var result = MealPlanner.PlanMeal(
                stomachState, available, cravings, cravingsSatisfied,
                remainingCal, config, dinnerPartyMult: dinnerPartyMult);

            var output = PlanRenderer.RenderPlan(result, sources);
            user.MsgLocStr(output);
        }
        catch (Exception ex)
        {
            user.MsgLocStr($"Plan error: {ex.Message}");
        }
    }

    [ChatSubCommand("EcoDietRoot", "Plan optimal meal for full stomach capacity (ignoring current fill)", "fullplan")]
    public static void FullPlan(User user)
    {
        try
        {
            var config = new PlannerConfig();

            // For full plan: start with empty stomach, plan for max calories
            var stomachState = new Dictionary<FoodCandidate, int>();
            var (available, sources) = FoodDiscovery.DiscoverAll(user);

            if (available.Count == 0)
            {
                user.MsgLocStr("No food found in your backpack to plan with.");
                return;
            }

            var maxCalories = StomachSnapshot.GetMaxCalories(user);

            // No cravings context for full plan (starting fresh)
            var cravings = BuildCravingsList(user);
            var cravingsSatisfied = 0;
            var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);

            var result = MealPlanner.PlanMeal(
                stomachState, available, cravings, cravingsSatisfied,
                maxCalories, config, dinnerPartyMult: dinnerPartyMult);

            var output = PlanRenderer.RenderPlan(result, sources);
            user.MsgLocStr(output);
        }
        catch (Exception ex)
        {
            user.MsgLocStr($"Full plan error: {ex.Message}");
        }
    }

    [ChatSubCommand("EcoDietRoot", "Export game state to JSON for the Python planner", "export")]
    public static void Export(User user, string note = "")
    {
        var timestamp = DateTime.UtcNow.ToString("yyyy-MM-dd_HHmmss");
        var filename = $"game_state_{timestamp}.json";
        var dir = Path.Combine(
            AppDomain.CurrentDomain.BaseDirectory, "Mods", "EcoDietMod", "exports");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, filename);
        GameStateExporter.ExportGameState(user, path, note);
        user.MsgLocStr($"Game state exported to {path}");
    }

    /// <summary>
    /// Build a cravings list from the current craving (if any).
    /// </summary>
    private static List<string> BuildCravingsList(User user)
    {
        var cravings = new List<string>();
        var currentCraving = StomachSnapshot.GetCurrentCraving(user);
        if (currentCraving != null)
            cravings.Add(currentCraving);
        return cravings;
    }
}
