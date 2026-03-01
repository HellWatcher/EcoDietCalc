using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
/// Chat commands for the EcoDiet in-game meal planner.
/// </summary>
[ChatCommandHandler]
public static class DietCommands
{
    [ChatCommand("EcoDiet — plan optimal meals", "ediet")]
    public static void EcoDiet(User user)
    {
        user.MsgLocStr(
            "EcoDiet commands: /ediet plan [full|calories], /ediet config [key value], /ediet export [note]");
    }

    /// <summary>
    /// Plan an optimal meal.
    ///   /ed plan       — remaining calorie budget
    ///   /ed plan full  — full stomach capacity (empty stomach sim)
    ///   /ed plan 1500  — custom calorie budget
    /// </summary>
    [ChatSubCommand("EcoDiet", "Plan optimal meal (plan / plan full / plan <calories>)", "plan")]
    public static void Plan(User user, string arg = "")
    {
        try
        {
            var trimmed = arg.Trim();
            var isFullPlan = string.Equals(trimmed, "full", StringComparison.OrdinalIgnoreCase)
                          || string.Equals(trimmed, "max", StringComparison.OrdinalIgnoreCase);

            var config = new PlannerConfig();
            var displayConfig = DisplayConfig.Load(user.Name);
            var discovery = FoodDiscovery.DiscoverAll(user, displayConfig);

            if (discovery.Available.Count == 0)
            {
                user.MsgLocStr("No food found in backpack, nearby storage, or shops.");
                return;
            }

            Dictionary<FoodCandidate, int> stomachState;
            float calorieBudget;
            int cravingsSatisfied;

            if (isFullPlan)
            {
                // Full plan: empty stomach, plan for max calories
                stomachState = new Dictionary<FoodCandidate, int>();
                calorieBudget = StomachSnapshot.GetMaxCalories(user);
                cravingsSatisfied = 0;
            }
            else if (int.TryParse(trimmed, out var customCal) && customCal > 0)
            {
                // Custom calorie budget with current stomach
                stomachState = StomachSnapshot.CaptureStomach(user);
                calorieBudget = customCal;
                cravingsSatisfied = StomachSnapshot.GetCravingsSatisfied(user);
            }
            else
            {
                // Default: remaining calories
                stomachState = StomachSnapshot.CaptureStomach(user);
                calorieBudget = StomachSnapshot.GetRemainingCalories(user);
                cravingsSatisfied = StomachSnapshot.GetCravingsSatisfied(user);
            }

            if (calorieBudget <= 0f)
            {
                user.MsgLocStr("No calorie budget remaining. Stomach is full.");
                return;
            }

            var cravings = BuildCravingsList(user);
            var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);

            var result = MealPlanner.PlanMeal(
                stomachState, discovery.Available, cravings, cravingsSatisfied,
                calorieBudget, config, dinnerPartyMult: dinnerPartyMult);

            var output = PlanRenderer.RenderPlan(
                result, discovery,
                showSources: displayConfig.Sources,
                showTags: displayConfig.Tags,
                compact: displayConfig.Compact);
            user.MsgLocStr(output);
        }
        catch (Exception ex)
        {
            user.MsgLocStr($"Plan error: {ex.Message}");
        }
    }

    [ChatSubCommand("EcoDiet", "Show or change display settings", "config")]
    public static void Config(User user, string args = "")
    {
        try
        {
            var parts = args.Trim().Split(' ', 2, StringSplitOptions.RemoveEmptyEntries);

            if (parts.Length == 0)
            {
                ConfigEditor.EditInteractive(user);
                return;
            }

            ApplyConfigChange(user, parts);
        }
        catch (Exception ex)
        {
            user.MsgLocStr($"Config error: {ex.Message}");
        }
    }

    /// <summary>
    /// Apply a CLI config change: /ed config &lt;key&gt; &lt;value&gt;.
    /// </summary>
    private static void ApplyConfigChange(User user, string[] parts)
    {
        if (parts.Length < 2)
        {
            user.MsgLocStr(
                "Usage: /ed config <key> <value>\n" +
                "  Boolean keys: compact, sources, tags (true|false)\n" +
                "  currencies <name,name,...> or 'clear'\n" +
                "  maxcost <number> (0 = no limit)\n" +
                "  maxdistance <meters> (discovery radius)");
            return;
        }

        var key = parts[0].ToLowerInvariant();
        var rawValue = parts[1].Trim();
        var config = DisplayConfig.Load(user.Name);

        switch (key)
        {
            // Boolean settings
            case "compact":
            case "sources":
            case "tags":
                if (!bool.TryParse(rawValue, out var boolValue))
                {
                    user.MsgLocStr($"Invalid value '{rawValue}'. Use true or false.");
                    return;
                }
                switch (key)
                {
                    case "compact":  config.Compact = boolValue;  break;
                    case "sources":  config.Sources = boolValue;  break;
                    case "tags":     config.Tags = boolValue;     break;
                }
                config.Save(user.Name);
                user.MsgLocStr($"Set {key} = {boolValue}");
                break;

            // Currency whitelist
            case "currencies":
                if (string.Equals(rawValue, "clear", StringComparison.OrdinalIgnoreCase))
                {
                    config.ShopCurrencyFilter.Clear();
                    config.Save(user.Name);
                    user.MsgLocStr("Cleared shop currency filter (all currencies accepted).");
                }
                else
                {
                    var currencies = rawValue
                        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                        .ToList();
                    config.ShopCurrencyFilter = currencies;
                    config.Save(user.Name);
                    user.MsgLocStr($"Set currencies = {string.Join(", ", currencies)}");
                }
                break;

            // Max cost per 1000 cal
            case "maxcost":
                if (!float.TryParse(rawValue, out var costValue) || costValue < 0)
                {
                    user.MsgLocStr($"Invalid value '{rawValue}'. Use a number >= 0 (0 = no limit).");
                    return;
                }
                config.MaxCostPer1000Cal = costValue;
                config.Save(user.Name);
                var costLabel = costValue > 0 ? $"{costValue:F1}" : "no limit";
                user.MsgLocStr($"Set maxcost = {costLabel}");
                break;

            // Discovery radius
            case "maxdistance":
                if (!float.TryParse(rawValue, out var distValue) || distValue <= 0)
                {
                    user.MsgLocStr($"Invalid value '{rawValue}'. Use a number > 0.");
                    return;
                }
                config.MaxDiscoveryRadius = distValue;
                config.Save(user.Name);
                user.MsgLocStr($"Set maxdistance = {distValue:F0}m");
                break;

            default:
                user.MsgLocStr(
                    $"Unknown setting '{key}'.\n" +
                    "Valid: compact, sources, tags, currencies, maxcost, maxdistance");
                return;
        }
    }

    [ChatSubCommand("EcoDiet", "Export game state to JSON for the Python planner", "export")]
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
