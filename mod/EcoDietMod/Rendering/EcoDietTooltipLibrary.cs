using System;
using System.Collections.Generic;
using System.Linq;
using Eco.Gameplay.Items;
using Eco.Gameplay.Players;
using Eco.Gameplay.Systems.NewTooltip;
using Eco.Gameplay.Systems.NewTooltip.TooltipLibraryFiles;
using Eco.Shared.Items;
using Eco.Shared.Localization;
using EcoDietMod.Algorithm;
using EcoDietMod.Config;
using EcoDietMod.Discovery;
using EcoDietMod.Models;

namespace EcoDietMod.Rendering;

/// <summary>
/// Adds an "EcoDiet Plan" section to the Stomach tooltip panel.
/// Registered via Eco's <see cref="TooltipLibraryAttribute"/> — scanned at server startup.
/// </summary>
[TooltipLibrary]
public static class EcoDietTooltipLibrary
{
    /// <summary>
    /// Appends a meal plan summary to the Stomach tooltip.
    /// Cached per-user (plan depends on player inventory and stomach state).
    /// Priority 200 places it below the built-in stomach sections (100-110).
    /// </summary>
    [NewTooltip(CacheAs.User, priority: 200, flags: TTFlags.ClearCacheForAllUsers,
        overrideType: typeof(Stomach))]
    public static LocString MealPlanTooltip(Stomach stomach, User user)
    {
        try
        {
            var (available, sources) = FoodDiscovery.DiscoverAll(user);
            if (available.Count == 0)
                return LocString.Empty;

            var remainingCal = StomachSnapshot.GetRemainingCalories(user);
            if (remainingCal <= 0)
                return LocString.Empty;

            var stomachState = StomachSnapshot.CaptureStomach(user);
            var cravings = BuildCravingsList(user);
            var cravingsSatisfied = StomachSnapshot.GetCravingsSatisfied(user);
            var dinnerPartyMult = StomachSnapshot.GetDinnerPartyMult(user);
            var config = new PlannerConfig();

            var result = MealPlanner.PlanMeal(
                stomachState, available, cravings, cravingsSatisfied,
                remainingCal, config, dinnerPartyMult: dinnerPartyMult);

            if (result.Items.Count == 0)
                return LocString.Empty;

            var displayConfig = DisplayConfig.Load(user.Name);
            var text = PlanRenderer.RenderPlan(
                result, sources,
                showSources: displayConfig.Sources,
                showTags: displayConfig.Tags,
                compact: true); // tooltips always use compact format

            return new TooltipSection(
                Localizer.DoStr("EcoDiet Plan"),
                Localizer.DoStr(text),
                allowLineWrapping: true,
                isFoldable: true);
        }
        catch
        {
            // Tooltip errors must not crash the UI
            return LocString.Empty;
        }
    }

    private static List<string> BuildCravingsList(User user)
    {
        var cravings = new List<string>();
        var currentCraving = StomachSnapshot.GetCurrentCraving(user);
        if (currentCraving != null)
            cravings.Add(currentCraving);
        return cravings;
    }
}
