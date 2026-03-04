using System;
using System.Linq;
using Eco.Gameplay.Players;
using Eco.Gameplay.Systems.Messaging.Chat.Commands;
using Eco.Shared.Localization;
using EcoDietMod.Config;

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
            "EcoDiet commands: /ediet config [key value]");
    }

    [ChatSubCommand("EcoDiet", "Show or change display settings")]
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
                "Usage: /ediet config <key> <value>\n" +
                "  Boolean keys: fullplan, compact, sources, tags (true|false)\n" +
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
            case "fullplan":
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
                    case "fullplan": config.FullPlan = boolValue;  break;
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
                    "Valid: fullplan, compact, sources, tags, currencies, maxcost, maxdistance");
                return;
        }
    }
}
