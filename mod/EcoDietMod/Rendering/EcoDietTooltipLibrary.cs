using Eco.Gameplay.Players;
using Eco.Gameplay.Systems.NewTooltip;
using Eco.Gameplay.Systems.NewTooltip.TooltipLibraryFiles;
using Eco.Shared.Items;
using Eco.Shared.Localization;
using EcoDietMod.Config;
using EcoDietMod.Tracking;

namespace EcoDietMod.Rendering;

/// <summary>
/// Adds an "EcoDiet Plan" section to the Stomach tooltip panel.
/// Registered via Eco's <see cref="TooltipLibraryAttribute"/> — scanned at server startup.
/// Uses extension method pattern required by Eco's NewTooltip scanner.
/// </summary>
[TooltipLibrary]
public static class EcoDietTooltipLibrary
{
    /// <summary>
    /// Appends a meal plan countdown to the Stomach tooltip.
    /// CacheAs.Disabled — we manage our own cache via PlanTracker.
    /// Extension method on Stomach (required by Eco's tooltip registration).
    /// </summary>
    [NewTooltip(CacheAs.Disabled, overrideType: typeof(Stomach))]
    public static LocString MealPlanTooltip(this Stomach stomach)
    {
        try
        {
            var user = stomach.Owner;
            if (user == null)
                return LocString.Empty;

            var displayConfig = DisplayConfig.Load(user.Name);
            var remaining = PlanTracker.GetRemainingPlanContext(
                user, out var status, out var finalSp, out var discovery);
            var text = PlanRenderer.RenderRemainingPlan(
                remaining, status, finalSp, discovery,
                showSources: displayConfig.Sources,
                showTags: displayConfig.Tags,
                compact: displayConfig.Compact);

            return new TooltipSection(
                Localizer.DoStr("EcoDiet"),
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
}
