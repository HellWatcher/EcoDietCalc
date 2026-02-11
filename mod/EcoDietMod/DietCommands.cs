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
/// Chat commands for the EcoDiet in-game meal planner.
/// </summary>
[ChatCommandHandler]
public static class DietCommands
{
    [ChatCommand("EcoDiet — plan optimal meals", "ed")]
    public static void EcoDiet(User user)
    {
        user.MsgLocStr(
            "EcoDiet commands: /ed plan [full|calories], /ed config [key value], /ed export [note]");
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
            var (available, sources) = FoodDiscovery.DiscoverAll(user);

            if (available.Count == 0)
            {
                user.MsgLocStr("No food found in your backpack to plan with.");
                return;
            }

            Dictionary<FoodCandidate, int> stomachState;
            int calorieBudget;
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

            if (calorieBudget <= 0)
            {
                user.MsgLocStr("No calorie budget remaining. Stomach is full.");
                return;
            }

            var cravings = BuildCravingsList(user);
            var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);

            var displayConfig = DisplayConfig.Load(user.Name);

            var result = MealPlanner.PlanMeal(
                stomachState, available, cravings, cravingsSatisfied,
                calorieBudget, config, dinnerPartyMult: dinnerPartyMult);

            var output = PlanRenderer.RenderPlan(
                result, sources,
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
                // Show current config
                var cfg = DisplayConfig.Load(user.Name);
                var sb = new StringBuilder();
                sb.AppendLine("--- EcoDiet Display Settings ---");
                sb.AppendLine($"  compact  = {cfg.Compact}    (compact vs full plan format)");
                sb.AppendLine($"  sources  = {cfg.Sources}    (show food source tags)");
                sb.AppendLine($"  tags     = {cfg.Tags}    (show variety/taste/craving tags)");
                sb.AppendLine($"  autoplan = {cfg.AutoPlan}    (reserved for future auto-plan)");
                sb.AppendLine();
                sb.AppendLine("Usage: /ed config <key> <true|false>");
                user.MsgLocStr(sb.ToString());
                return;
            }

            if (parts.Length < 2)
            {
                user.MsgLocStr("Usage: /ed config <key> <true|false>");
                return;
            }

            var key = parts[0].ToLowerInvariant();
            if (!bool.TryParse(parts[1], out var value))
            {
                user.MsgLocStr($"Invalid value '{parts[1]}'. Use true or false.");
                return;
            }

            var config = DisplayConfig.Load(user.Name);
            switch (key)
            {
                case "compact":  config.Compact = value;  break;
                case "sources":  config.Sources = value;  break;
                case "tags":     config.Tags = value;     break;
                case "autoplan": config.AutoPlan = value;  break;
                default:
                    user.MsgLocStr($"Unknown setting '{key}'. Valid: compact, sources, tags, autoplan");
                    return;
            }

            config.Save(user.Name);
            user.MsgLocStr($"Set {key} = {value}");
        }
        catch (Exception ex)
        {
            user.MsgLocStr($"Config error: {ex.Message}");
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
